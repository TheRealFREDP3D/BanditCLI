"""SSH connection management module for BanditCLI.

This module provides thread-safe SSH connection management for the OverTheWire
Bandit wargame. It includes SSHConnection for individual connections and
SSHManager for managing multiple sessions.
"""

import logging
import os
import socket
import threading
import time
from collections import defaultdict
from typing import Callable, Optional

import paramiko

logging.getLogger("paramiko").setLevel(logging.WARNING)

MAX_ATTEMPTS_PER_MINUTE = 5
RATE_LIMIT_WINDOW = 60  # seconds

_connection_attempts: dict[str, list[float]] = defaultdict(list)
_rate_limit_lock = threading.Lock()


def _check_rate_limit(identifier: str) -> bool:
    """Check if connection attempts are rate limited.

    Args:
        identifier: Unique identifier (hostname:port) for rate limiting.

    Returns:
        bool: True if allowed, False if rate limited.
    """
    current_time = time.time()
    with _rate_limit_lock:
        _connection_attempts[identifier] = [
            t for t in _connection_attempts[identifier] if current_time - t < RATE_LIMIT_WINDOW
        ]
        if len(_connection_attempts[identifier]) >= MAX_ATTEMPTS_PER_MINUTE:
            return False
        _connection_attempts[identifier].append(current_time)
        return True


class SSHConnection:
    """Thread-safe SSH connection with background output reading.

    The output_callback MUST be set before calling connect(), so the
    background reader thread can deliver data as soon as it arrives.

    Attributes:
        hostname (str): The remote server hostname.
        port (int): The SSH port number.
        username (str): The SSH username.
        connected (bool): Connection status flag.
        output_callback (Optional[Callable[[str], None]]): Called with output data.
        timeout (int): Connection timeout in seconds.
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
        output_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialise SSH connection parameters.

        Args:
            hostname: The remote server hostname.
            port: The SSH port number.
            username: The SSH username.
            password: The SSH password.
            notify_callback: Callback for status/error notifications.
            timeout: Connection timeout in seconds.
            verify_host_key: Whether to attempt loading system known_hosts.
            output_callback: Optional callback to receive output immediately.
                             Can also be set later via set_output_callback()
                             before connect() is called.
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
        self.connected = False
        self.output_callback: Optional[Callable[[str], None]] = output_callback
        self.read_thread: Optional[threading.Thread] = None
        self.stop_reading = False
        self.notify = notify_callback
        self.timeout = timeout
        self.keepalive_interval = 30
        self.verify_host_key = verify_host_key
        self._lock = threading.Lock()

    def _configure_host_key_policy(self) -> None:
        """Load trusted host keys and configure the selected trust policy."""
        if self.client is None:
            raise RuntimeError("SSH client has not been created")

        if self.verify_host_key:
            known_hosts = os.path.expanduser("~/.ssh/known_hosts")
            try:
                self.client.load_system_host_keys()
                if os.path.exists(known_hosts):
                    self.client.load_host_keys(known_hosts)
                else:
                    self.notify(
                        f"No known-hosts file found at {known_hosts}; "
                        "unknown SSH host keys will be rejected.",
                        "warning",
                    )
            except OSError as error:
                self.notify(
                    f"Warning: Could not load known hosts: {error}. "
                    "Unknown SSH host keys will still be rejected.",
                    "warning",
                )
            self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.notify(
                f"WARNING: SSH host-key verification is disabled for "
                f"{self.hostname}:{self.port}",
                "warning",
            )

    def connect(self) -> bool:
        """Establish SSH connection with interactive shell.

        Set output_callback before calling this if you want output from the
        very first bytes the server sends (e.g. the login banner).

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            self.client = paramiko.SSHClient()
            self._configure_host_key_policy()

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
                        allow_agent=False,
                        look_for_keys=False,
                    )
                    break
                except (paramiko.AuthenticationException, paramiko.SSHException) as e:
                    if attempt == max_retries - 1:
                        raise
                    self.notify(
                        f"Connection attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {retry_delay}s...",
                        "warning",
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2

            self.channel = self.client.invoke_shell(term="xterm-color", width=80, height=24)
            self.channel.settimeout(0.1)
            self.connected = True
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
        """Start the background thread that reads SSH output."""
        with self._lock:
            self.stop_reading = False

        self.read_thread = threading.Thread(target=self._read_output, daemon=True)
        self.read_thread.start()

    def _read_output(self) -> None:
        """Background thread: continuously read SSH output and fire the callback."""
        output_buffer: list[str] = []
        last_callback_time = time.time()
        callback_interval = 0.05  # flush at most every 50 ms
        buffer_size_limit = 4096

        while not self.stop_reading and self.connected:
            try:
                if self.channel:
                    data = self.channel.recv(buffer_size_limit).decode("utf-8", errors="ignore")
                    if data:
                        output_buffer.append(data)
                        current_time = time.time()

                        should_flush = (
                            current_time - last_callback_time >= callback_interval
                            or len("".join(output_buffer)) > 8192
                        )
                        if should_flush:
                            batched = "".join(output_buffer)
                            output_buffer.clear()
                            if self.output_callback:
                                self.output_callback(batched)
                            last_callback_time = current_time

            except socket.timeout:
                # Expected when no data is available — flush anything buffered
                if output_buffer and self.output_callback:
                    self.output_callback("".join(output_buffer))
                    output_buffer.clear()
                    last_callback_time = time.time()
                continue
            except OSError as e:
                if not self.stop_reading:
                    self.notify(f"SSH communication error: {type(e).__name__}: {e}", "error")
                break
            except Exception as e:
                if not self.stop_reading:
                    self.notify(f"Unexpected SSH error: {type(e).__name__}: {e}", "error")
                break

        # Final flush on exit
        if output_buffer and self.output_callback:
            self.output_callback("".join(output_buffer))

    def send_command(self, command: str) -> None:
        """Send a command to the SSH shell.

        Args:
            command: Raw bytes to send (include \\r\\n for Enter).
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
        """Close the SSH connection and clean up the reader thread."""
        with self._lock:
            self.stop_reading = True
            self.connected = False

        if self.read_thread and self.read_thread.is_alive():
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

        if self.password:
            try:
                password_bytes = bytearray(self.password.encode("utf-8"))
                for i in range(len(password_bytes)):
                    password_bytes[i] = 0
                self.password = ""
                del password_bytes
            except Exception:
                self.password = ""

    def resize_pty(self, width: int, height: int) -> bool:
        """Resize the remote pseudo-terminal.

        Args:
            width: New width in characters.
            height: New height in characters.

        Returns:
            bool: True if successful, False otherwise.
        """
        with self._lock:
            if not self.channel or not self.connected:
                return False

        try:
            self.channel.resize_pty(width=width, height=height)
            return True
        except Exception as e:
            self.notify(f"Terminal resize failed: {type(e).__name__}: {e}", "warning")
            return False

    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set (or replace) the output callback.

        Prefer passing the callback to __init__ or setting it before connect()
        so no early output is lost. This method is still useful for replacing
        the callback on an already-connected session.

        Args:
            callback: Function called with batched output strings.
        """
        self.output_callback = callback


class SSHConnectionPool:
    """Reuse SSH connections to reduce connection overhead."""

    def __init__(self, max_connections: int = 5) -> None:
        self.max_connections = max_connections
        self._pool: dict[str, SSHConnection] = {}
        self._connection_times: dict[str, float] = {}
        self._lock = threading.Lock()
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
        output_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[SSHConnection]:
        """Get or create a pooled connection.

        The output_callback is passed through to SSHConnection so it is set
        before connect() starts the reader thread.

        Args:
            connection_key: Cache key for this connection.
            hostname: SSH server hostname.
            port: SSH server port.
            username: SSH username.
            password: SSH password.
            notify_callback: Callback for status/error notifications.
            timeout: Connection timeout in seconds.
            verify_host_key: Whether to load system known_hosts.
            output_callback: Output handler — set before connect() runs.

        Returns:
            SSHConnection if available/created, None if pool is full.
        """
        with self._lock:
            current_time = time.time()

            if connection_key in self._pool:
                conn = self._pool[connection_key]
                if (
                    conn.connected
                    and (current_time - self._connection_times[connection_key])
                    < self._connection_timeout
                ):
                    # Update callback in case it changed (e.g. new session)
                    if output_callback is not None:
                        conn.output_callback = output_callback
                    self._connection_times[connection_key] = current_time
                    return conn
                else:
                    self._remove_connection_locked(connection_key)

            if len(self._pool) >= self.max_connections:
                self._cleanup_stale_connections_locked()
                if len(self._pool) >= self.max_connections:
                    return None

            # Pass output_callback to constructor so it's set BEFORE connect()
            conn = SSHConnection(
                hostname,
                port,
                username,
                password,
                notify_callback,
                timeout,
                verify_host_key,
                output_callback=output_callback,
            )
            if conn.connect():
                self._pool[connection_key] = conn
                self._connection_times[connection_key] = current_time
                return conn

            return None

    def _remove_connection_locked(self, connection_key: str) -> None:
        """Remove and disconnect a pooled connection (caller holds self._lock)."""
        if connection_key in self._pool:
            conn = self._pool.pop(connection_key)
            self._connection_times.pop(connection_key, None)
            try:
                conn.disconnect()
            except Exception:
                pass

    def _cleanup_stale_connections_locked(self) -> None:
        """Remove connections idle longer than _connection_timeout (caller holds lock)."""
        current_time = time.time()
        stale = [
            k
            for k, t in self._connection_times.items()
            if current_time - t > self._connection_timeout
        ]
        for k in stale:
            self._remove_connection_locked(k)

    def close_all(self) -> None:
        """Close every connection in the pool."""
        with self._lock:
            for key in list(self._pool.keys()):
                self._remove_connection_locked(key)


class SSHManager:
    """Multi-session SSH connection manager.

    Attributes:
        connections (Dict[str, SSHConnection]): Active connections by session ID.
        notify (Callable[[str, str], None]): Notification callback.
    """

    def __init__(self, notify_callback: Callable[[str, str], None]) -> None:
        self.connections: dict[str, SSHConnection] = {}
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
        output_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Create a new SSH connection, replacing any existing one for session_id.

        The output_callback is wired up BEFORE the connection is established so
        no output (including the login banner) is lost.

        Args:
            session_id: Unique identifier for this session.
            hostname: SSH server hostname.
            port: SSH port number.
            username: SSH username.
            password: SSH password.
            timeout: Connection timeout in seconds.
            verify_host_key: Whether to load system known_hosts.
            output_callback: Called on the reader thread with batched output.
                             The caller is responsible for thread-safe dispatch
                             (e.g. using app.call_from_thread in Textual).

        Returns:
            bool: True if connection succeeded, False otherwise.
        """
        connection_identifier = f"{hostname}:{port}"
        if not _check_rate_limit(connection_identifier):
            self.notify(
                f"Connection rate limit exceeded for {hostname}:{port}. "
                "Please wait before trying again.",
                "error",
            )
            return False

        # Pop and disconnect any existing connection outside the lock
        with self._lock:
            existing = self.connections.pop(session_id, None)
        if existing is not None:
            existing.disconnect()

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
            output_callback=output_callback,
        )

        if conn:
            with self._lock:
                self.connections[session_id] = conn
            return True

        # Fallback: direct connection if pool is full
        connection = SSHConnection(
            hostname,
            port,
            username,
            password,
            self.notify,
            timeout,
            verify_host_key,
            output_callback=output_callback,
        )
        if connection.connect():
            with self._lock:
                self.connections[session_id] = connection
            return True

        return False

    def get_connection(self, session_id: str) -> Optional[SSHConnection]:
        """Return the active SSHConnection for session_id, or None."""
        with self._lock:
            return self.connections.get(session_id)

    def disconnect_session(self, session_id: str) -> None:
        """Disconnect and remove the connection for session_id."""
        with self._lock:
            conn = self.connections.pop(session_id, None)
        if conn is not None:
            conn.disconnect()

    def disconnect_all(self) -> None:
        """Disconnect all active sessions and drain the pool."""
        with self._lock:
            session_ids = list(self.connections.keys())
        for sid in session_ids:
            self.disconnect_session(sid)
        self.connection_pool.close_all()
