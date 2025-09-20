import paramiko
import threading
import time
import socket
from typing import Optional, Callable

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
    
    def start_reading(self):
        """Start background thread to read SSH output"""
        self.stop_reading = False
        self.read_thread = threading.Thread(target=self._read_output)
        self.read_thread.daemon = True
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
        """Send command to SSH session"""
        if self.channel and self.connected:
            try:
                self.channel.send(command)
            except Exception as e:
                self.notify(f"Error sending command: {e}", "error")
    
    def set_output_callback(self, callback: Callable[[str], None]):
        """Set callback function for SSH output"""
        self.output_callback = callback
    
    def resize_pty(self, width: int, height: int):
        """Resize the PTY"""
        if self.channel and self.connected:
            try:
                self.channel.resize_pty(width=width, height=height)
            except paramiko.SSHException as e:
                self.notify(f"Error resizing PTY: {e}", "error")

    def disconnect(self):
        """Close SSH connection"""
        self.stop_reading = True
        self.connected = False
        
        if self.read_thread:
            self.read_thread.join(timeout=2)
            if self.read_thread.is_alive():
                self.notify("Warning: SSH reading thread did not exit gracefully.", "warning")

        if self.channel:
            self.channel.close()
        
        if self.client:
            self.client.close()

class SSHManager:
    def __init__(self, notify_callback: Callable[[str, str], None]):
        self.connections = {}
        self.notify = notify_callback
    
    def create_connection(self, session_id: str, hostname: str, port: int, 
                         username: str, password: str, timeout: int = 10) -> bool:
        """Create new SSH connection"""
        if session_id in self.connections:
            self.disconnect_session(session_id)
        
        connection = SSHConnection(hostname, port, username, password, self.notify, timeout)
        if connection.connect():
            self.connections[session_id] = connection
            return True
        return False
    
    def get_connection(self, session_id: str) -> Optional[SSHConnection]:
        """Get SSH connection by session ID"""
        return self.connections.get(session_id)
    
    def disconnect_session(self, session_id: str):
        """Disconnect SSH session"""
        if session_id in self.connections:
            self.connections[session_id].disconnect()
            del self.connections[session_id]
    
    def disconnect_all(self):
        """Disconnect all SSH sessions"""
        for session_id in list(self.connections.keys()):
            self.disconnect_session(session_id)