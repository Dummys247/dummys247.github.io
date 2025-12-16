# System Deployment Guide

This document outlines the deployment process for **The 3rd Demon** web system. The deployment is managed by a robust Python script (`deploy.py`) that handles environment setup, security, and service execution.

## 1. Prerequisites

- **Python 3.8+** must be installed on the system.
- Administrative privileges are required if binding to Port 80.
- `pip` should be available to install dependencies.

## 2. Configuration

The system is configured via `deploy_config.json`. Key parameters:

- **server.port**: The port to serve the application on (Default: 8080).
- **server.root_dir**: The directory where the site will be deployed (Default: `./www`).
- **security.headers**: Custom HTTP headers for hardening (HSTS, X-Frame-Options, etc.).
- **health_check**: Settings for post-deployment verification.

## 3. Deployment Process

To deploy the system, run the following command:

```bash
python deploy.py
```

### What the script does:
1.  **Environment Check**: Verifies dependencies (installing `requests` if missing).
2.  **Backup**: Creates a timestamped backup of the current `www` directory in `deploy_backups/`.
3.  **Deployment**: Copies the latest source files to the production `www` folder.
4.  **Service Start**: Launches a secure, multi-threaded HTTP server.
5.  **Health Check**: Verifies the server is responding correctly on the configured port.
6.  **Rollback**: If any step fails, the system automatically restores the previous backup.

## 4. Verification

To verify the deployment in a clean environment, run the test suite:

```bash
python test_deployment.py
```

This runs unit tests to validate:
- Server availability
- Security headers (XSS Protection, NoSniff, etc.)
- Content delivery

## 5. Directory Structure

- `deploy.py`: Main deployment script.
- `deploy_config.json`: Configuration template.
- `www/`: Production serving directory (created automatically).
- `deploy_backups/`: Automatic backups for rollback.
- `deploy.log`: Execution logs.

## 6. Security Hardening

The server is configured with the following security headers by default:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS)

## 7. Troubleshooting

- **Port in use**: If the script fails with "Port 8080 is already in use", check `deploy.log` and change the port in `deploy_config.json`.
- **Permission denied**: Run the terminal as Administrator/Root if using ports < 1024.
- **Health Check Failed**: Ensure no firewall is blocking the connection to `localhost`.
