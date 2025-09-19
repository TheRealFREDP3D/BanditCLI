import paramiko
import threading
import time
from typing import Optional, Callable

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
                timeout=10
            )
            
            # Create interactive shell
            self.channel = self.client.invoke_shell()
            self.channel.settimeout(0.1)
            self.connected = True
            
            # Start reading output in background
            self.start_reading()
            
            return True
            
        except Exception as e:
            print(f"SSH connection failed: {e}")
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
                         username: str, password: str) -> bool:
        """Create new SSH connection"""
        if session_id in self.connections:
            self.disconnect_session(session_id)
        
        connection = SSHConnection(hostname, port, username, password)
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