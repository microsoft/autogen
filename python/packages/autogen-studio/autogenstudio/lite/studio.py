import os
import json
import tempfile
import threading
import time
import webbrowser
import subprocess
from pathlib import Path
from typing import Union, Dict, Any
import uvicorn
from autogen_core import ComponentModel


class LiteStudio:
    """
    Core class for managing AutoGen Studio lite mode instances.
    Supports both file-based and programmatic team configurations.
    """
    
    def __init__(
        self,
        team: Union[str, Path, Dict[str, Any], ComponentModel, None] = None,
        host: str = "127.0.0.1",
        port: int = 8080,
        session_name: str = "Lite Session",
        auto_open: bool = True
    ):
        """
        Initialize LiteStudio instance.
        
        Args:
            team: Team configuration - can be:
                - str: Path to team JSON file
                - Path: Path object to team JSON file
                - Dict[str, Any]: Team configuration dictionary  
                - ComponentModel: AutoGen ComponentModel instance
                - None: Creates default team
            host: Host to run server on
            port: Port to run server on  
            session_name: Name for the auto-created session
            auto_open: Whether to auto-open browser
        """
        self.host = host
        self.port = port
        self.session_name = session_name
        self.auto_open = auto_open
        self.server_process = None
        self.server_thread = None
        
        # Handle team loading
        self.team_file_path = self._load_team(team)
        
    def _load_team(self, team: Union[str, Path, Dict[str, Any], ComponentModel, None]) -> str:
        """
        Load team from file path, object, or create default.
        Returns the file path to the team JSON.
        
        Args:
            team: Can be file path (str/Path), dict, ComponentModel, or None
        """
        if team is None:
            # Create default team
            from autogenstudio.gallery.builder import create_default_lite_team
            return create_default_lite_team()
            
        elif isinstance(team, (str, Path)):
            # File path provided
            team_path = Path(team)
            if not team_path.exists():
                raise FileNotFoundError(f"Team file not found: {team_path}")
            return str(team_path.absolute())
            
        elif isinstance(team, dict):
            # Team dict provided - save to temp file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.json', 
                delete=False
            )
            try:
                json.dump(team, temp_file, indent=2)
                temp_file.flush()
                return temp_file.name
            finally:
                temp_file.close()
                
        elif isinstance(team, ComponentModel):
            # ComponentModel - use model_dump directly
            team_dict = team.model_dump()
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.json', 
                delete=False
            )
            try:
                json.dump(team_dict, temp_file, indent=2)
                temp_file.flush()
                return temp_file.name
            finally:
                temp_file.close()
                
        else:
            # Try to serialize other team objects
            team_dict = None
            
            # Try dump_component() method (AutoGen teams)
            if hasattr(team, 'dump_component'):
                component = team.dump_component()
                if hasattr(component, 'model_dump'):
                    team_dict = component.model_dump()
                elif hasattr(component, 'dict'):
                    team_dict = component.dict()
                else:
                    team_dict = dict(component)
            
            # Try model_dump() method (Pydantic v2)
            elif hasattr(team, 'model_dump'):
                team_dict = team.model_dump()
                
            # Try dict() method (Pydantic v1)
            elif hasattr(team, 'dict'):
                team_dict = team.dict()
                
            if team_dict is None:
                raise ValueError(f"Cannot serialize team object of type {type(team)}. "
                               f"Expected: file path, dict, ComponentModel, or object with dump_component()/model_dump()/dict() method.")
            
            # Save serialized team to temp file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.json', 
                delete=False
            )
            try:
                json.dump(team_dict, temp_file, indent=2)
                temp_file.flush()
                return temp_file.name
            finally:
                temp_file.close()
    
    def _get_env_file_path(self) -> str:
        """Get path for environment variables file."""
        app_dir = os.path.join(os.path.expanduser("~"), ".autogenstudio")
        if not os.path.exists(app_dir):
            os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "temp_env_vars.env")
    
    def _setup_environment(self) -> str:
        """
        Setup environment variables for lite mode.
        Returns path to the environment file.
        """
        env_vars = {
            "AUTOGENSTUDIO_HOST": self.host,
            "AUTOGENSTUDIO_PORT": str(self.port),
            "AUTOGENSTUDIO_LITE_MODE": "true",
            "AUTOGENSTUDIO_API_DOCS": "false",
            "AUTOGENSTUDIO_AUTH_DISABLED": "true",
            "AUTOGENSTUDIO_LITE_SESSION_NAME": self.session_name,
            "AUTOGENSTUDIO_LITE_TEAM_FILE": self.team_file_path,
            "AUTOGENSTUDIO_DATABASE_URI": "sqlite:///:memory:",
        }
        
        env_file_path = self._get_env_file_path()
        with open(env_file_path, "w") as temp_env:
            for key, value in env_vars.items():
                temp_env.write(f"{key}={value}\n")
                
        return env_file_path
    
    def _setup_browser_opening(self):
        """Setup browser opening in a separate thread."""
        if self.auto_open:
            def open_browser():
                time.sleep(3)  # Wait for server startup
                url = f"http://{self.host}:{self.port}/lite"
                webbrowser.open(url)
            
            threading.Thread(target=open_browser, daemon=True).start()
    
    def start(self, background: bool = False):
        """
        Start the lite studio server.
        
        Args:
            background: If True, run server in background thread
        """
        # Check if already running
        if self.server_thread and self.server_thread.is_alive():
            raise RuntimeError("LiteStudio is already running")
        
        # Setup environment
        env_file_path = self._setup_environment()
        
        # Setup browser opening
        self._setup_browser_opening()
        
        if background:
            # Run server in background thread
            def run_server():
                uvicorn.run(
                    "autogenstudio.web.app:app",
                    host=self.host,
                    port=self.port,
                    workers=1,
                    env_file=env_file_path,
                )
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
        else:
            # Run server in foreground (blocking)
            uvicorn.run(
                "autogenstudio.web.app:app",
                host=self.host,
                port=self.port,
                workers=1,
                env_file=env_file_path,
            )
    
    def stop(self):
        """Stop the lite studio server."""
        if self.server_thread and self.server_thread.is_alive():
            # For background threads, we can't easily stop uvicorn
            # This is a limitation - in production you'd want proper shutdown
            self.server_thread.join(timeout=5)
            self.server_thread = None
    
    def __enter__(self):
        """Context manager entry - start in background."""
        self.start(background=True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb): # type: ignore
        """Context manager exit - stop server."""
        self.stop()
    
    @classmethod
    def shutdown_port(cls, port: int):
        """
        Utility to shutdown any process running on the specified port.
        
        Args:
            port: Port number to shutdown
        """
        try:
            # Try to find and kill process on port (Unix/Linux/Mac)
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    subprocess.run(["kill", "-9", pid], check=False)
                    
        except (subprocess.SubprocessError, FileNotFoundError):
            # lsof might not be available on all systems
            pass
