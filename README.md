

<div align="center">
  <img src="https://imgur.com/Hfeyj4b.png" alt="Rudder Logo" width="200"/>
</div>

# Rudder - 3D Printer Logbook

I had grown tired of trying to manually track the parameters I tweaked from one print to another. This web app starts to solve that.

A web application for tracking 3D printer activities, maintenance, and print parameters. This application helps you maintain a detailed log of your 3D printing activities and correlate print parameters with outcomes.

## Features

- Track print jobs and their outcomes
- Monitor print parameters and changes
- Log maintenance events
- Visual timeline of printer activities
- Store GCode files and their associated metadata
- Track print quality and functionality ratings

<div align="center">
  <img src="https://imgur.com/gEMzMEN" alt="ex1" width="200"/>
</div>

<div align="center">
  <img src="https://imgur.com/PKjq2i3" alt="ex2" width="200"/>
</div>

The print Jobs tab highlights slicer parameters from the previous print job that have been modified. This helps identify potential issues and optimize future prints.

## TODO

- multi-printer support?
- fixing timeline lag
- export a previous prints settings back into PS or SuSi


## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your Moonraker connection (choose one method):

   **Option A: Interactive Setup (Recommended for beginners)**
   ```bash
   python start.py
   ```

   **Option B: Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your printer's IP address
   python app.py
   ```

   **Option C: Command Line Arguments**
   ```bash
   python app.py --moonraker-url http://YOUR_PRINTER_IP:7125
   ```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Configuration

### Moonraker URL Setup

The application needs to connect to your 3D printer's Moonraker instance. You can configure this in several ways:

1. **Environment Variables** (`.env` file) - Recommended
2. **Command Line Arguments** - For advanced users
3. **Interactive Setup** - User-friendly guided setup

See [CONFIG.md](CONFIG.md) for detailed configuration instructions.

### Finding Your Moonraker URL

Your Moonraker URL typically follows this format: `http://PRINTER_IP:7125`

- Check your printer's web interface for the IP address
- Look in your router's admin panel for connected devices
- The default Moonraker port is `7125`

## Usage

### Adding a Print Job
1. Click "Add New Print" button
2. Enter the file name
3. Upload the GCode file
4. Submit the form

### Adding Maintenance Events
1. Click "Add Maintenance Event" button
2. Enter the maintenance description
3. Add any todo tasks if needed
4. Submit the form

### Viewing the Timeline
- The timeline view shows all print jobs and maintenance events in chronological order
- Click on any item to view more details

## Data Management

### Resetting/Cleaning Data

If you need to clear all data (useful for production deployment or testing):

**Safe reset with backup:**
```bash
python reset_data.py
```

**Quick reset without confirmation:**
```bash
python reset_data.py --force
```

**Create backup only:**
```bash
python reset_data.py --backup-only
```

**Restore from backup:**
```bash
python reset_data.py --restore backup_20240101_120000
```

### What Gets Reset
- All print job records from the database
- All maintenance event records
- All uploaded G-code files
- Database tables are recreated fresh

### Production Deployment Notes
- The application automatically creates an empty database on first run
- Upload and instance directories are excluded from git (see `.gitignore`)
- Always backup your data before major updates

## Development

The application is built using:
- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript
- Database: SQLite

## Contributing

Feel free to submit issues and enhancement requests!
