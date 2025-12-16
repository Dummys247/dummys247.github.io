#!/usr/bin/env python3
import os
import sys
import json
import logging
import shutil
import time
import threading
import http.server
import socketserver
import socket
from datetime import datetime
from functools import partial

# Constants
CONFIG_FILE = 'deploy_config.json'
BACKUP_DIR = 'deploy_backups'
WWW_DIR = 'www'

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("deploy.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SecureHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, config=None, **kwargs):
        self.config = config
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self):
        # Apply security headers from config
        if self.config and 'security' in self.config:
            for header, value in self.config['security'].get('headers', {}).items():
                self.send_header(header, value)
        super().end_headers()

    def log_message(self, format, *args):
        logger.info(f"Request: {self.address_string()} - {format%args}")

def load_config():
    """Load configuration from JSON file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file {CONFIG_FILE} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {CONFIG_FILE}.")
        sys.exit(1)

def check_dependencies():
    """Check if necessary dependencies are installed."""
    logger.info("Checking dependencies...")
    try:
        import requests
    except ImportError:
        logger.warning("'requests' module not found. Installing...")
        os.system(f"{sys.executable} -m pip install requests")

def setup_environment(config):
    """Setup directories and environment."""
    logger.info("Setting up environment...")
    
    # Create WWW directory if not exists
    root_dir = config['server']['root_dir']
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)
        logger.info(f"Created root directory: {root_dir}")
    
    # Create Backup directory
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def backup_current_version(config):
    """Create a backup of the current WWW directory."""
    root_dir = config['server']['root_dir']
    if os.path.exists(root_dir) and os.listdir(root_dir):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
        shutil.copytree(root_dir, backup_path)
        logger.info(f"Backup created at: {backup_path}")
        return backup_path
    return None

def deploy_files(config):
    """Copy files from current directory to WWW directory (Simulation of build/deploy)."""
    root_dir = config['server']['root_dir']
    
    # Files to exclude from deployment
    excludes = [root_dir, BACKUP_DIR, '.git', '.vscode', '__pycache__', 'deploy.log', 'deploy.py', 'deploy_config.json', 'deploy_to_github.ps1', 'mirror_script.py', 'summon_demon.ps1']
    
    logger.info("Deploying files...")
    
    # Clean target directory (except for itself obviously)
    # Actually, for idempotent operations, we might want to sync. 
    # For simplicity, we copy everything not in excludes.
    
    count = 0
    for item in os.listdir('.'):
        if item in excludes or item.startswith('.'):
            continue
        
        src = item
        dst = os.path.join(root_dir, item)
        
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        count += 1
    
    logger.info(f"Deployed {count} items to {root_dir}")

def health_check(config):
    """Perform health check on the running server."""
    import requests
    import time
    
    host = config['server']['host']
    port = config['server']['port']
    endpoint = config['health_check']['endpoint']
    url = f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}{endpoint}"
    
    logger.info(f"Running health check on {url}...")
    
    retries = config['health_check']['retries']
    for i in range(retries):
        try:
            response = requests.get(url, timeout=config['health_check']['timeout'])
            if response.status_code == 200:
                logger.info("Health check PASSED.")
                return True
            else:
                logger.warning(f"Health check returned status code: {response.status_code}")
        except Exception as e:
            logger.warning(f"Health check attempt {i+1} failed: {e}")
        
        time.sleep(1)
    
    logger.error("Health check FAILED.")
    return False

def start_server(config):
    """Start the HTTP server."""
    host = config['server']['host']
    port = config['server']['port']
    root_dir = config['server']['root_dir']
    
    handler = partial(SecureHTTPRequestHandler, directory=root_dir, config=config)
    
    try:
        # Check if port is in use
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host if host != '0.0.0.0' else '127.0.0.1', port)) == 0:
                logger.error(f"Port {port} is already in use.")
                return None

        httpd = socketserver.TCPServer((host, port), handler)
        logger.info(f"Serving HTTP on {host} port {port} (http://{host}:{port}/) ...")
        
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        return httpd
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return None

def rollback(backup_path, config):
    """Rollback to the specified backup."""
    if not backup_path:
        logger.warning("No backup path provided for rollback.")
        return

    logger.warning("Initiating ROLLBACK...")
    root_dir = config['server']['root_dir']
    
    try:
        if os.path.exists(root_dir):
            shutil.rmtree(root_dir)
        shutil.copytree(backup_path, root_dir)
        logger.info("Rollback successful.")
    except Exception as e:
        logger.critical(f"Rollback failed: {e}")

def main():
    logger.info("Starting deployment process...")
    
    # 1. Load Config
    config = load_config()
    
    # 2. Check Dependencies
    check_dependencies()
    
    # 3. Setup Environment
    setup_environment(config)
    
    # 4. Backup
    backup_path = backup_current_version(config)
    
    # 5. Deploy Files
    try:
        deploy_files(config)
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        if backup_path:
            rollback(backup_path, config)
        sys.exit(1)
    
    # 6. Start Server
    server = start_server(config)
    if not server:
        logger.error("Server failed to start.")
        # Rollback logic could be applied here too if needed
        sys.exit(1)
    
    # 7. Health Check
    if not health_check(config):
        logger.error("Deployment verification failed.")
        server.shutdown()
        if backup_path:
            rollback(backup_path, config)
        sys.exit(1)
    
    logger.info("Deployment SUCCESSFUL. System is online.")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        server.shutdown()
        sys.exit(0)

if __name__ == '__main__':
    main()
