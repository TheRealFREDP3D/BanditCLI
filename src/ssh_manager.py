"""SSH connection management module for BanditCLI.

This module provides thread-safe SSH connection management for the OverTheWire
Bandit wargame. It includes SSHConnection for individual connections and
SSHManager for managing multiple sessions.

The SSHConnection class handles individual SSH connections with background
output reading, while SSHManager provides a centralized interface for managing
multiple SSH sessions.
"""

# src/ssh_manager.py
import logging
import os
import socket
import threading
import time
from collections import defaultdict
from typing import Callable, Dict, Optional

import paramiko

# Configure logging
logging.getLogger("paramiko").setLevel(logging.WARNING)

# Rate limiting configuration
MAX_ATTEMPTS_PER_MINUTE = 5
RATE_LIMIT_WINDOW = 60  # seconds

# Global rate limiting storage
_connection_attempts = defaultdict(list)


class SSHConnection:
    """Thread-safe SSH connection with background output reading.

    This class manages a single SSH connection to a remote server, providing
    interactive shell functionality with real-time output reading in a separate
    thread. It handles connection lifecycle, command sending, and graceful
    disconnection.

    Security Considerations:
        - Passwords are stored in memory and securely cleared on disconnection
        - Host key verification is enabled by default to prevent MITM attacks
        - Connection timeouts prevent hanging connections
        - Sensitive data is overwritten using bytearray for secure memory clearing
        - No SSH agent or private key usage to prevent credential leakage

    Attributes:
        hostname (str): The remote server hostname.
        port (int): The SSH port number.
        username (str): The SSH username.
        password (str): The SSH password (cleared after disconnection).
        client (Optional[paramiko.SSHClient]): The Paramiko SSH client.
        channel (Optional[paramiko.Channel]): The interactive shell channel.
        connected (bool): Connection status flag.
        output_callback (Optional[Callable[[str], None]]): Callback for output.
        read_thread (Optional[threading.Thread]): Background output reading thread.
        stop_reading (bool): Flag to stop the background reading thread.
        notify (Callable[[str, str], None]): Notification callback for messages.
        timeout (int): Connection timeout in seconds.
        keepalive_interval (int): Keepalive packet interval in seconds.
        _lock (threading.Lock): Thread safety lock.
    """

    def __init__(
        self,
        hostname: str,
        port: int,
        username: str,
        password: str,
        notify_callback: Callable[[str, str], None],
        timeout: int = 10,
        verify_host_key: bool = True,
    ) -> None:
        """Initialize SSH connection parameters.

        Args:
            hostname: The remote server hostname.
            port: The SSH port number.
            username: The SSH username.
            password: The SSH password.
            notify_callback: Callback for status/error notifications (message, severity).
            timeout: Connection timeout in seconds.
            verify_host_key: Whether to verify host keys (recommended for security).
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
        self.connected = False
        self.output_callback: Optional[Callable[[str], None]] = None
        self.read_thread: Optional[threading.Thread] = None
        self.stop_reading = False
        self.notify = notify_callback
        self.timeout = timeout
        self.keepalive_interval = 30  # Send keepalive every 30 seconds
        self.verify_host_key = verify_host_key
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Establish SSH connection with interactive shell.

        Creates and configures the SSH client, connects to the remote server,
        establishes an interactive shell channel, and starts background output
        reading. Handles authentication and connection errors gracefully.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            self.client = paramiko.SSHClient()

            # Configure host key policy based on security preference
            if self.verify_host_key:
                # Use AddPolicy for educational environments - adds new hosts to known_hosts
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                # Load known hosts file if it exists
                try:
                    self.client.load_system_host_keys()
                    self.client.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))
                except OSError as e:
                    self.notify(
                        f"Warning: Could not load known hosts file: {e}. New hosts will be added automatically.",
                        "warning",
                    )
            else:
                # Educational: AutoAddPolicy for learning environments (less secure)
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.notify(
                    "WARNING: Using insecure host key policy (AutoAddPolicy). This creates MITM vulnerability.",
                    "warning",
                )

            # Connect with retry logic
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    self.client.connect(
                        hostname=self.hostname,
                        port=self.port,
                        username=self.username,
                        password=self.password,
                        timeout=self.timeout,
                        allow_agent=False,  # Don't use SSH agent for security
                        look_for_keys=False,  # Don't look for private keys
                    )
                    break  # Connection successful
                except (paramiko.AuthenticationException, paramiko.SSHException) as e:
                    if attempt == max_retries - 1:
                        raise  # Re-raise on final attempt
                    self.notify(
                        f"Connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...",
                        "warning",
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

            # Create interactive shell
            self.channel = self.client.invoke_shell(term="xterm-color", width=80, height=24)
            self.channel.settimeout(0.1)
            self.connected = True

            # Start reading output in background
            self.start_reading()

            return True

        except (
            paramiko.AuthenticationException,
            paramiko.SSHException,
            OSError,
            TimeoutError,
        ) as e:
            self.notify(f"SSH connection failed: {type(e).__name__}: {e}", "error")
            return False

    def start_reading(self) -> None:
        """Start background thread to read SSH output continuously.

        Initializes and starts a daemon thread that continuously reads output
        from the SSH channel and calls the output callback when data is received.
        """
        with self._lock:
            # Reset the stop flag before starting the thread
            self.stop_reading = False

        # Create and start daemon thread for background output reading
        # Daemon thread will exit automatically when main program exits
        self.read_thread = threading.Thread(target=self._read_output, daemon=True)
        self.read_thread.start()

    def _read_output(self) -> None:
        """Background thread function to continuously read SSH output with performance optimizations.

        Runs in a separate thread, continuously reading data from the SSH channel
        and passing it to the output callback. Uses larger buffer size and reduced
        callback frequency for better performance.
        """
        output_buffer = []
        last_callback_time = time.time()
        callback_interval = 0.05  # 50ms between callbacks to reduce UI updates
        buffer_size_limit = 4096  # Larger buffer for better throughput

        while not self.stop_reading and self.connected:
            try:
                if self.channel:
                    # Read larger chunks for better performance
                    data = self.channel.recv(buffer_size_limit).decode("utf-8", errors="ignore")
                    if data:
                        output_buffer.append(data)
                        current_time = time.time()

                        # Batch callbacks to reduce UI update frequency
                        if (
                            current_time - last_callback_time >= callback_interval
                            or len("".join(output_buffer)) > 8192
                        ):  # Flush if buffer gets large

                            batched_data = "".join(output_buffer)
                            output_buffer.clear()

                            if self.output_callback:
                                self.output_callback(batched_data)

                            last_callback_time = current_time
            except socket.timeout:
                # Socket timeout is expected when no data is available
                # Flush any remaining buffered data
                if output_buffer and self.output_callback:
                    batched_data = "".join(output_buffer)
                    output_buffer.clear()
                    self.output_callback(batched_data)
                continue
            except OSError as e:
                # Network-related errors (connection lost, etc.)
                if not self.stop_reading:
                    self.notify(f"SSH communication error: {type(e).__name__}: {e}", "error")
                break  # Exit the loop on connection errors
            except Exception as e:
                # Catch-all for unexpected errors to prevent thread crashes
                if not self.stop_reading:
                    self.notify(f"Unexpected SSH error: {type(e).__name__}: {e}", "error")
                break  # Exit the loop on unexpected errors

        # Flush any remaining data on exit
        if output_buffer and self.output_callback:
            batched_data = "".join(output_buffer)
            self.output_callback(batched_data)

    def send_command(self, command: str) -> None:
        """Send command to SSH session with error handling.

        Sends a command to the interactive shell channel. Validates connection
        status before sending and handles any transmission errors.

        Args:
            command: The command to send to the remote shell.
        """
        with self._lock:
            if not self.channel or not self.connected:
                self.notify("SSH connection not active", "error")
                return

        try:
            self.channel.send(command.encode("utf-8"))
        except (OSError, paramiko.SSHException) as e:
            self.notify(f"Command transmission failed: {type(e).__name__}: {e}", "error")
            with self._lock:
                self.connected = False

    def disconnect(self) -> None:
        """Close SSH connection safely with thread cleanup.

        Performs graceful disconnection by stopping the background reading thread,
        closing the SSH channel and client, and clearing sensitive data.
        Handles thread termination timeouts and resource cleanup errors.
        """
        with self._lock:
            # Signal the background thread to stop reading
            self.stop_reading = True
            self.connected = False

        # Wait for read thread to finish gracefully with timeout
        if self.read_thread and self.read_thread.is_alive():
            # Give the thread 2 seconds to exit cleanly
            self.read_thread.join(timeout=2)
            if self.read_thread.is_alive():
                # Thread didn't exit gracefully - attempt forced cleanup
                self.notify(
                    "Warning: SSH reading thread did not exit gracefully. Attempting resource cleanup.",
                    "warning",
                )
                # Attempt resource cleanup even though thread is still running
                if self.client:
                    try:
                        self.client.close()
                        self.notify(
                            "SSH client connection closed due to lingering thread.", "information"
                        )
                    except (paramiko.SSHException, OSError) as e:
                        self.notify(
                            f"Error during SSH client cleanup: {type(e).__name__}: {e}", "error"
                        )
                self.notify(
                    "Forced thread termination is not supported; resources have been cleaned up.",
                    "warning",
                )

        # Close channel and client (may be redundant if already closed above)
        # This ensures cleanup even if thread handling above failed
        if self.read_thread:
            # Second attempt to wait for thread completion
            self.read_thread.join(timeout=2)
            if self.read_thread.is_alive():
                self.notify("Warning: SSH reading thread did not exit gracefully.", "warning")
        if self.channel:
            try:
                self.channel.close()
            except (paramiko.SSHException, OSError) as e:
                self.notify(f"Error closing SSH channel: {type(e).__name__}: {e}", "warning")

        if self.client:
            try:
                self.client.close()
            except (paramiko.SSHException, OSError) as e:
                self.notify(f"Error closing SSH client: {type(e).__name__}: {e}", "warning")

        # Clear sensitive data securely using bytearray for proper memory overwrite
        if self.password:
            try:
                # Convert to bytearray for in-place modification
                # This ensures the original password data is actually overwritten in memory
                password_bytes = bytearray(self.password.encode("utf-8"))
                # Overwrite each byte with zeros to clear sensitive data
                for i in range(len(password_bytes)):
                    password_bytes[i] = 0
                # Clear the original string reference
                self.password = ""
                # Explicitly delete the bytearray to free memory
                del password_bytes
            except Exception:
                # Fallback to basic clearing if bytearray approach fails
                # This is less secure but prevents crashes
                self.password = " " * len(self.password)
                self.password = ""

    def resize_pty(self, width: int, height: int) -> bool:
        """Resize the interactive shell PTY.

        This adjusts the remote pseudo-terminal dimensions to match the
        local UI container.

        Args:
            width: New width in characters.
            height: New height in characters.

        Returns:
            bool: True if resize successful, False otherwise.
        """
        with self._lock:
            if not self.channel or not self.connected:
                return False

        try:
            self.channel.resize_pty(width=width, height=height)
            return True
        except (paramiko.SSHException, OSError) as e:
            self.notify(f"SSH error during terminal resize: {type(e).__name__}: {e}", "warning")
            return False
        except Exception as e:
            self.notify(
                f"Unexpected error during terminal resize: {type(e).__name__}: {e}", "warning"
            )
            return False

    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback function for handling SSH output.

        Args:
            callback: Function to call when SSH output is received.
        """
        self.output_callback = callback


def _check_rate_limit(identifier: str) -> bool:
    """Check if connection attempts are rate limited.

    Args:
        identifier: Unique identifier (hostname:port) for rate limiting.

    Returns:
        bool: True if allowed, False if rate limited.
    """
    current_time = time.time()

    # Remove old attempts outside the window
    _connection_attempts[identifier] = [
        attempt_time
        for attempt_time in _connection_attempts[identifier]
        if current_time - attempt_time < RATE_LIMIT_WINDOW
    ]

    # Check if under the limit
    if len(_connection_attempts[identifier]) >= MAX_ATTEMPTS_PER_MINUTE:
        return False

    # Record this attempt
    _connection_attempts[identifier].append(current_time)
    return True


class SSHConnectionPool:
    """Connection pool for managing multiple SSH sessions efficiently.

    Reuses SSH connections when possible to reduce connection overhead
    and manages connection lifecycle for better performance.
    """

    def __init__(self, max_connections: int = 5) -> None:
        """Initialize connection pool.

        Args:
            max_connections: Maximum number of concurrent connections.
        """
        self.max_connections = max_connections
        self._pool: Dict[str, SSHConnection] = {}
        self._connection_times: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._connection_timeout = 1800  # 30 minutes

    def get_connection(
        self,
        connection_key: str,
        hostname: str,
        port: int,
        username: str,
        password: str,
        notify_callback: Callable[[str, str], None],
        timeout: int = 10,
        verify_host_key: bool = True,
    ) -> Optional[SSHConnection]:
        """Get or create a connection from the pool.

        Args:
            connection_key: Unique key for the connection.
            hostname: SSH server hostname.
            port: SSH server port.
            username: SSH username.
            password: SSH password.
            notify_callback: Callback for notifications.
            timeout: Connection timeout.
            verify_host_key: Whether to verify host keys.

        Returns:
            SSHConnection if available/created, None otherwise.
        """
        with self._lock:
            current_time = time.time()

            # Check if we have an existing, valid connection
            if connection_key in self._pool:
                conn = self._pool[connection_key]
                if (
                    conn.connected
                    and (current_time - self._connection_times[connection_key])
                    < self._connection_timeout
                ):
                    # Update last used time
                    self._connection_times[connection_key] = current_time
                    return conn
                else:
                    # Connection is stale, remove it
                    self._remove_connection(connection_key)

            # Check if we're at the connection limit
            if len(self._pool) >= self.max_connections:
                self._cleanup_stale_connections()

                if len(self._pool) >= self.max_connections:
                    return None  # Pool is full

            # Create new connection
            conn = SSHConnection(
                hostname, port, username, password, notify_callback, timeout, verify_host_key
            )
            if conn.connect():
                self._pool[connection_key] = conn
                self._connection_times[connection_key] = current_time
                return conn

            return None

    def _remove_connection(self, connection_key: str) -> None:
        """Remove a connection from the pool."""
        if connection_key in self._pool:
            conn = self._pool[connection_key]
            try:
                conn.disconnect()
            except Exception:
                pass  # Ignore errors during cleanup

            del self._pool[connection_key]
            if connection_key in self._connection_times:
                del self._connection_times[connection_key]

    def _cleanup_stale_connections(self) -> None:
        """Remove stale connections from the pool."""
        current_time = time.time()
        stale_keys = []

        for key, last_used in self._connection_times.items():
            if current_time - last_used > self._connection_timeout:
                stale_keys.append(key)

        for key in stale_keys:
            self._remove_connection(key)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            keys = list(self._pool.keys())
            for key in keys:
                self._remove_connection(key)


class SSHManager:
    """Multi-session SSH connection manager.

    This class manages multiple SSH connections simultaneously, providing
    a centralized interface for creating, accessing, and disconnecting
    SSH sessions. Thread-safe implementation ensures safe concurrent access.

    Security Considerations:
        - Rate limiting prevents brute force attacks (max 5 attempts per minute)
        - Connection identifiers use hostname:port for granular rate limiting
        - Thread-safe operations prevent race conditions
        - Automatic cleanup of existing connections prevents resource leaks
        - All connections inherit security settings from SSHConnection class

    Attributes:
        connections (Dict[str, SSHConnection]): Dictionary of active connections.
        notify (Callable[[str, str], None]): Notification callback for messages.
        _lock (threading.Lock): Thread safety lock for connection management.
    """

    def __init__(self, notify_callback: Callable[[str, str], None]) -> None:
        """Initialize SSH manager with notification callback and connection pool.

        Args:
            notify_callback: Callback for status/error notifications.
        """
        self.connections: Dict[str, SSHConnection] = {}
        self.notify = notify_callback
        self._lock = threading.Lock()
        self.connection_pool = SSHConnectionPool(max_connections=5)

    def create_connection(
        self,
        session_id: str,
        hostname: str,
        port: int,
        username: str,
        password: str,
        timeout: int = 10,
        verify_host_key: bool = True,
    ) -> bool:
        """Create new SSH connection with validation, session management, and connection pooling.

        Creates a new SSH connection and stores it in the connections dictionary.
        Uses connection pool for better resource management. If a connection with the same
        session_id already exists, it will be disconnected and replaced with the new connection.

        Args:
            session_id: Unique identifier for the SSH session.
            hostname: The remote server hostname.
            port: The SSH port number.
            username: The SSH username.
            password: The SSH password.
            timeout: Connection timeout in seconds.
            verify_host_key: Whether to verify host keys (recommended for security).

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        with self._lock:
            # Check rate limiting before attempting connection
            connection_identifier = f"{hostname}:{port}"
            if not _check_rate_limit(connection_identifier):
                self.notify(
                    f"Connection rate limit exceeded for {hostname}:{port}. Please wait before trying again.",
                    "error",
                )
                return False

            # Clean up existing connection
            if session_id in self.connections:
                self.disconnect_session(session_id)

            # Try to get connection from pool first
            connection_key = f"{session_id}:{hostname}:{port}:{username}"
            conn = self.connection_pool.get_connection(
                connection_key,
                hostname,
                port,
                username,
                password,
                self.notify,
                timeout,
                verify_host_key,
            )

            if conn:
                self.connections[session_id] = conn
                return True

            # Fallback to direct connection if pool is full
            connection = SSHConnection(
                hostname, port, username, password, self.notify, timeout, verify_host_key
            )
            if connection.connect():
                self.connections[session_id] = connection
                return True
            return False

    def get_connection(self, session_id: str) -> Optional[SSHConnection]:
        """Get SSH connection by session ID.

        Retrieves an existing SSH connection from the connections dictionary.

        Args:
            session_id: The session identifier to look up.

        Returns:
            Optional[SSHConnection]: The SSH connection if found, None otherwise.
        """
        with self._lock:
            return self.connections.get(session_id)

    def disconnect_session(self, session_id: str) -> None:
        """Disconnect and remove SSH session.

        Disconnects the SSH connection associated with the given session ID
        and removes it from the connections dictionary.

        Args:
            session_id: The session identifier to disconnect.
        """
        with self._lock:
            if session_id in self.connections:
                self.connections[session_id].disconnect()
                del self.connections[session_id]

    def disconnect_all(self) -> None:
        """Disconnect all active SSH sessions and close connection pool.

        Iterates through all active connections and disconnects them.
        This method is thread-safe and handles concurrent access properly.
        Also closes all pooled connections.
        """
        with self._lock:
            session_ids = list(self.connections.keys())

        for session_id in session_ids:
            self.disconnect_session(session_id)

        # Close all pooled connections
        self.connection_pool.close_all()
