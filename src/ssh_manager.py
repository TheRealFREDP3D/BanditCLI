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
    def __init__(self, hostname: str, port: int, username: str, password: str, notify_callback: Callable[[str, str], None], timeout: int = 10):
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
        """Establish SSH connection"""
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
    def _create_ssh_client(self) -> None:
        """Create and configure SSH client with connection parameters."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=10
        )

    def start_reading(self):
        """Start background thread to read SSH output"""
        with self._lock:
            self.stop_reading = False
        self.read_thread = threading.Thread(target=self._read_output, daemon=True)
        self.read_thread.start()

    def _read_output(self):
        """Background thread function to continuously read SSH output"""
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

    def send_command(self, command: str):
        """Send command to SSH session with error handling"""
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

    def disconnect(self):
        """Close SSH connection safely"""
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


class SSHManager:
    def __init__(self, notify_callback: Callable[[str, str], None]):
        self.connections = {}
        self.notify = notify_callback
        self._lock = threading.Lock()

    def create_connection(self, session_id: str, hostname: str, port: int,
                          username: str, password: str, timeout: int = 10) -> bool:
        """Create new SSH connection with validation"""
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
        """Get SSH connection by session ID"""
        with self._lock:
            return self.connections.get(session_id)

    def disconnect_session(self, session_id: str):
        """Disconnect SSH session"""
        with self._lock:
            if session_id in self.connections:
                self.connections[session_id].disconnect()
                del self.connections[session_id]

    def disconnect_all(self):
        """Disconnect all SSH sessions"""
        with self._lock:
            session_ids = list(self.connections.keys())
        
        for session_id in session_ids:
            self.disconnect_session(session_id)
