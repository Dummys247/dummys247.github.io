import unittest
import json
import os
import requests
import threading
import time
from deploy import start_server, load_config

class TestDeployment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load config
        cls.config = load_config()
        # Use a different port for testing to avoid conflicts
        cls.config['server']['port'] = 8081
        cls.config['server']['root_dir'] = './www'
        
        # Ensure root dir exists
        if not os.path.exists(cls.config['server']['root_dir']):
            os.makedirs(cls.config['server']['root_dir'])
            with open(os.path.join(cls.config['server']['root_dir'], 'index.html'), 'w') as f:
                f.write('<html><body>Test</body></html>')

        # Start server in background
        cls.server = start_server(cls.config)
        time.sleep(1) # Wait for startup

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()

    def test_health_endpoint(self):
        """Test if the server responds to the health check endpoint."""
        url = f"http://localhost:{self.config['server']['port']}/"
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)

    def test_security_headers(self):
        """Test if security headers are present."""
        url = f"http://localhost:{self.config['server']['port']}/"
        response = requests.get(url)
        headers = self.config['security']['headers']
        for key, value in headers.items():
            self.assertIn(key, response.headers)
            self.assertEqual(response.headers[key], value)

    def test_content_serving(self):
        """Test if content is actually served."""
        url = f"http://localhost:{self.config['server']['port']}/index.html"
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
