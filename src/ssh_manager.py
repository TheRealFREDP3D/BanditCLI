"""SSH connection management module for BanditCLI.

This module provides thread-safe SSH connection management for the OverTheWire
Bandit wargame. It includes SSHConnection for individual connections and
SSHManager for managing multiple sessions.

The SSHConnection class handles individual SSH connections with background
output reading, while SSHManager provides a centralized interface for managing
multiple SSH sessions.
"""
# src/ssh_manager.py
import paramiko
import threading
import time
import socket
import logging
from typing import Optional, Callable, Dict
from enum import Enum

# Configure logging
logging.getLogger("paramiko").setLevel(logging.WARNING)

class SSHConnection:
    """Thread-safe SSH connection with background output reading.
    
    This class manages a single SSH connection to a remote server, providing
    interactive shell functionality with real-time output reading in a separate
    thread. It handles connection lifecycle, command sending, and graceful
    disconnection.
    
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
    def __init__(self, hostname: str, port: int, username: str, password: str, 
                 notify_callback: Callable[[str, str], None], timeout: int = 10) -> None:
        """Initialize SSH connection parameters.
        
        Args:
            hostname: The remote server hostname.
            port: The SSH port number.
            username: The SSH username.
            password: The SSH password.
            notify_callback: Callback for status/error notifications.
            timeout: Connection timeout in seconds.
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
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.client.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout
            )
            
            # Create interactive shell
            self.channel = self.client.invoke_shell(term='xterm-color', width=80, height=24)
            self.channel.settimeout(0.1)
            self.connected = True
            
            # Start reading output in background
            self.start_reading()
            
            return True
            
        except (paramiko.AuthenticationException, paramiko.SSHException, TimeoutError) as e:
            self.notify(f"SSH connection failed: {e}", "error")
            return False

    def start_reading(self) -> None:
        """Start background thread to read SSH output continuously.
        
        Initializes and starts a daemon thread that continuously reads output
        from the SSH channel and calls the output callback when data is received.
        """
        with self._lock:
            self.stop_reading = False
        self.read_thread = threading.Thread(target=self._read_output, daemon=True)
        self.read_thread.start()

    def _read_output(self) -> None:
        """Background thread function to continuously read SSH output.
        
        Runs in a separate thread, continuously reading data from the SSH channel
        and passing it to the output callback. Handles socket timeouts and other
        errors gracefully. Stops when stop_reading flag is set or connection is lost.
        """
        while not self.stop_reading and self.connected:
            try:
                if self.channel:
                    data = self.channel.recv(1024).decode('utf-8', errors='ignore')
                    if data and self.output_callback:
                        self.output_callback(data)
            except (socket.timeout, Exception) as e:
                if not self.stop_reading:
                    self.notify(f"Error reading SSH output: {e}", "error")
                break

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
            self.channel.send(command.encode('utf-8'))
        except Exception as e:
            self.notify(f"Error sending command: {e}", "error")
            with self._lock:
                self.connected = False

    def disconnect(self) -> None:
        """Close SSH connection safely with thread cleanup.
        
        Performs graceful disconnection by stopping the background reading thread,
        closing the SSH channel and client, and clearing sensitive data.
        Handles thread termination timeouts and resource cleanup errors.
        """
        with self._lock:
            self.stop_reading = True
            self.connected = False
        
        # Wait for read thread to finish
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
            if self.read_thread.is_alive():
                self.notify("Warning: SSH reading thread did not exit gracefully. Attempting resource cleanup.", "warning")
                # Attempt resource cleanup
                if self.client:
                    try:
                        self.client.close()
                        self.notify("SSH client connection closed due to lingering thread.", "info")
                    except Exception as e:
                        self.notify(f"Error during SSH client cleanup: {e}", "error")
                self.notify("Forced thread termination is not supported; resources have been cleaned up.", "warning")
        
        # Close channel and client
        if self.read_thread:
            self.read_thread.join(timeout=2)
            if self.read_thread.is_alive():
                self.notify("Warning: SSH reading thread did not exit gracefully.", "warning")
        if self.channel:
            try:
                self.channel.close()
            except Exception as e:
                self.notify(f"Error closing SSH channel: {e}", "warning")
        
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                self.notify(f"Error closing SSH client: {e}", "warning")
        
        # Clear sensitive data
        self.password = ""
    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback function for handling SSH output.
        
        Args:
            callback: Function to call when SSH output is received.
        """
        self.output_callback = callback


class SSHManager:
    """Multi-session SSH connection manager.
    
    This class manages multiple SSH connections simultaneously, providing
    a centralized interface for creating, accessing, and disconnecting
    SSH sessions. Thread-safe implementation ensures safe concurrent access.
    
    Attributes:
        connections (Dict[str, SSHConnection]): Dictionary of active connections.
        notify (Callable[[str, str], None]): Notification callback for messages.
        _lock (threading.Lock): Thread safety lock for connection management.
    """
    def __init__(self, notify_callback: Callable[[str, str], None]) -> None:
        """Initialize SSH manager with notification callback.
        
        Args:
            notify_callback: Callback for status/error notifications.
        """
        self.connections: Dict[str, SSHConnection] = {}
        self.notify = notify_callback
        self._lock = threading.Lock()

    def create_connection(self, session_id: str, hostname: str, port: int,
                          username: str, password: str, timeout: int = 10) -> bool:
        """Create new SSH connection with validation and session management.
        
        Creates a new SSH connection and stores it in the connections dictionary.
        If a connection with the same session_id already exists, it will be
        disconnected and replaced with the new connection.
        
        Args:
            session_id: Unique identifier for the SSH session.
            hostname: The remote server hostname.
            port: The SSH port number.
            username: The SSH username.
            password: The SSH password.
            timeout: Connection timeout in seconds.
            
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        with self._lock:
            # Clean up existing connection
            if session_id in self.connections:
                self.disconnect_session(session_id)
            
            connection = SSHConnection(hostname, port, username, password, self.notify, timeout)
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
        """Disconnect all active SSH sessions.
        
        Iterates through all active connections and disconnects them.
        This method is thread-safe and handles concurrent access properly.
        """
        with self._lock:
            session_ids = list(self.connections.keys())
        
        for session_id in session_ids:
            self.disconnect_session(session_id)
