# Production Deployment Checklist

This checklist ensures your Printer Logbook application is ready for production deployment.

## ✅ Pre-Deployment Security Check

### Personal Data Removal
- [ ] No personal IP addresses in code (check for 192.168.x.x patterns)
- [ ] Database is empty or contains only test data
- [ ] Upload directory is clean (no personal G-code files)
- [ ] No sensitive configuration in source code

### Configuration Security
- [ ] `.env` file is not committed to version control
- [ ] `.gitignore` includes sensitive files (`*.db`, `uploads/`, `instance/`, `.env`)
- [ ] Default configuration uses generic examples
- [ ] No hardcoded credentials or API keys

## 🚀 Deployment Steps

### 1. Environment Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd rudder

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Choose one of these methods:

**Option A: Environment Variables**
```bash
cp .env.example .env
# Edit .env with your production settings
```

**Option B: Interactive Setup**
```bash
python start.py
```

**Option C: Command Line**
```bash
python app.py --moonraker-url http://YOUR_PRINTER_IP:7125
```

### 3. Database Initialization
The database will be created automatically on first run, but you can verify:
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized')"
```

### 4. Start the Application
```bash
# Development mode
python app.py

# Or with the user-friendly launcher
python start.py

# Or with specific configuration
python app.py --moonraker-url http://192.168.1.10:7125 --poll-interval 10
```

## 🔧 Production Configuration

### Required Configuration
- `MOONRAKER_URL`: Your printer's Moonraker API URL (e.g., `http://192.168.1.10:7125`)

### Optional Configuration
- `POLL_INTERVAL`: How often to check print status (default: 15 seconds)
- `SQLALCHEMY_DATABASE_URI`: Database location (default: SQLite in instance/)
- `UPLOAD_FOLDER`: Where to store G-code files (default: uploads/)

### Environment Variables (.env file)
```env
# Required
MOONRAKER_URL=http://YOUR_PRINTER_IP:7125

# Optional
POLL_INTERVAL=15
SQLALCHEMY_DATABASE_URI=sqlite:///printer_logbook.db
UPLOAD_FOLDER=uploads
```

## 🌐 Web Server Deployment

### For Production Use with WSGI
1. Install a WSGI server:
   ```bash
   pip install gunicorn
   ```

2. Create `wsgi.py`:
   ```python
   from app import app
   if __name__ == "__main__":
       app.run()
   ```

3. Start with Gunicorn:
   ```bash
   gunicorn --bind 0.0.0.0:5000 wsgi:app
   ```

### Reverse Proxy (Nginx example)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔒 Security Considerations

### Network Security
- [ ] Moonraker instance is on a trusted network
- [ ] Consider VPN access for remote monitoring
- [ ] Use HTTPS in production if exposing externally

### Application Security
- [ ] Change Flask secret key for production
- [ ] Set `FLASK_ENV=production`
- [ ] Disable debug mode (`app.run(debug=False)`)
- [ ] Regular backup of database and uploads

### File Security
- [ ] Uploads directory has appropriate permissions
- [ ] Database file is not web-accessible
- [ ] Log files are properly rotated

## 📊 Monitoring & Maintenance

### Health Checks
- [ ] Test Moonraker connection: `curl http://YOUR_PRINTER_IP:7125/printer/info`
- [ ] Verify web interface loads: `curl http://localhost:5000`
- [ ] Check database connectivity

### Regular Maintenance
- [ ] Backup database regularly
- [ ] Clean old G-code files if disk space is limited
- [ ] Monitor log files for errors
- [ ] Update dependencies periodically

### Backup Strategy
```bash
# Create backup
python reset_data.py --backup-only

# Restore from backup
python reset_data.py --restore backup_20240101_120000
```

## 🐛 Troubleshooting

### Common Issues

**Cannot connect to Moonraker**
- Verify IP address and port
- Check network connectivity
- Ensure Moonraker is running

**Database errors**
- Check file permissions
- Verify SQLite is installed
- Run `python reset_data.py` to recreate

**File upload issues**
- Check uploads directory exists and is writable
- Verify disk space availability

### Logs and Debugging
```bash
# Run with debug logging
FLASK_DEBUG=1 python app.py

# Check system logs
tail -f /var/log/syslog | grep printer-logbook
```

## 📋 Post-Deployment Verification

### Functional Tests
- [ ] Web interface loads correctly
- [ ] Can connect to Moonraker
- [ ] File uploads work
- [ ] Database operations succeed
- [ ] Print monitoring detects jobs

### Performance Tests
- [ ] Response times are acceptable
- [ ] Memory usage is stable
- [ ] No resource leaks over time

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# Backup current data
python reset_data.py --backup-only

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart the application
```

### Database Migrations
If future versions require database changes, they will be documented in release notes.

## 📞 Support

### Getting Help
- Check the README.md for basic usage
- Review CONFIG.md for configuration details
- Check GitHub issues for known problems

### Reporting Issues
When reporting issues, include:
- Python version
- Operating system
- Configuration details (without sensitive info)
- Error messages and logs
- Steps to reproduce

---

**Last Updated:** 2024-08-01
**Version:** 1.0.0