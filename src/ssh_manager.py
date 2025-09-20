import paramiko
import threading
import time
from typing import Optional, Callable
from enum import Enum

class SSHConnectionError(Enum):
    """Enumeration of SSH connection error types."""
    AUTHENTICATION_FAILED = "Authentication failed"
    TIMEOUT = "Connection timeout"
    NETWORK_ERROR = "Network error"
    HOST_UNKNOWN = "Unknown host"
    GENERIC_ERROR = "Connection failed"

class SSHConnectionException(Exception):
    """Custom exception for SSH connection errors."""
    def __init__(self, error_type: SSHConnectionError, message: str = None):
        self.error_type = error_type
        self.message = message or error_type.value
        super().__init__(self.message)

class SSHConnection:
    def __init__(self, hostname: str, port: int, username: str, password: str):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        self.channel = None
        self.connected = False
        self.output_callback = None
        self.read_thread = None
        self.stop_reading = False
        
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

    def _create_shell_channel(self) -> None:
        """Create and configure an interactive shell channel."""
        self.channel = self.client.invoke_shell()
        self.channel.settimeout(0.1)
        self.connected = True
        self.start_reading()

    def connect(self, retries: int = 3) -> bool:
        """Establish SSH connection with retry mechanism"""
        for attempt in range(retries):
            try:
                self._create_ssh_client()
                self._create_shell_channel()
                return True
                
            except paramiko.AuthenticationException:
                print(f"SSH connection failed: Authentication failed for user {self.username}")
                return False  # Don't retry on authentication failures
            except paramiko.SSHException as e:
                if "timed out" in str(e).lower():
                    print(f"SSH connection failed: Connection timeout when connecting to {self.hostname}:{self.port}")
                else:
                    print(f"SSH connection failed: SSH error - {e}")
                if attempt < retries - 1:
                    print(f"Retrying connection... ({attempt + 1}/{retries - 1})")
                    time.sleep(1)
            except TimeoutError:
                print(f"SSH connection failed: Connection timeout when connecting to {self.hostname}:{self.port}")
                if attempt < retries - 1:
                    print(f"Retrying connection... ({attempt + 1}/{retries - 1})")
                    time.sleep(1)
            except Exception as e:
                print(f"SSH connection failed: {e}")
                if attempt < retries - 1:
                    print(f"Retrying connection... ({attempt + 1}/{retries - 1})")
                    time.sleep(1)
        
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
                if self.channel and self.channel.recv_ready():
                    data = self.channel.recv(1024).decode('utf-8', errors='ignore')
                    if data and self.output_callback:
                        self.output_callback(data)
                time.sleep(0.01)  # Small delay to prevent high CPU usage
            except Exception as e:
                if not self.stop_reading:
                    print(f"Error reading SSH output: {e}")
                break
    
    def send_command(self, command: str):
        """Send command to SSH session"""
        if self.channel and self.connected:
            try:
                self.channel.send(command)
            except Exception as e:
                print(f"Error sending command: {e}")
    
    def set_output_callback(self, callback: Callable[[str], None]):
        """Set callback function for SSH output"""
        self.output_callback = callback
    
    def disconnect(self):
        """Close SSH connection"""
        self.stop_reading = True
        self.connected = False
        
        if self.read_thread:
            self.read_thread.join(timeout=1)
        
        if self.channel:
            self.channel.close()
        
        if self.client:
            self.client.close()

class SSHManager:
    def __init__(self):
        self.connections = {}
    
    def create_connection(self, session_id: str, hostname: str, port: int, 
                         username: str, password: str, retries: int = 3) -> bool:
        """Create new SSH connection"""
        if session_id in self.connections:
            self.disconnect_session(session_id)
        
        connection = SSHConnection(hostname, port, username, password)
        if connection.connect(retries=retries):
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