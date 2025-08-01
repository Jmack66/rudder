# Configuration Guide

This guide explains how to configure the Printer Logbook application for your specific setup.

## Moonraker URL Configuration

The application needs to know where to find your Moonraker instance. You can configure this in several ways:

### Method 1: Environment Variables (Recommended)

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and update the `MOONRAKER_URL`:
   ```
   MOONRAKER_URL=http://YOUR_PRINTER_IP:7125
   ```

3. Start the application normally:
   ```bash
   python app.py
   ```

### Method 2: Command Line Arguments

You can specify the Moonraker URL directly when starting the application:

```bash
python app.py --moonraker-url http://192.168.1.10:7125
```

Additional command line options:
- `--moonraker-url`: Set the Moonraker URL
- `--poll-interval`: Set how often to check for print status (in seconds, default: 15)

Example with multiple options:
```bash
python app.py --moonraker-url http://192.168.1.10:7125 --poll-interval 10
```

### Method 3: Edit the Source Code (Not Recommended)

You can still edit the default value in `app.py`, but this makes it harder to manage different environments.

## Configuration Priority

The application uses the following priority order:
1. Command line arguments (highest priority)
2. Environment variables from `.env` file
3. Default values (lowest priority)

## Finding Your Moonraker URL

To find your Moonraker URL:

1. **Check your printer's web interface** - Usually displayed in the settings
2. **Use your printer's IP address** - The URL format is typically `http://PRINTER_IP:7125`
3. **Check your router's admin panel** - Look for connected devices
4. **Use network scanning tools** like `nmap` or check your router's DHCP client list

Common Moonraker ports:
- `7125` (default Moonraker port)
- `80` (if using a reverse proxy)

## Example Configurations

### Klipper with Mainsail/Fluidd on Raspberry Pi
```
MOONRAKER_URL=http://192.168.1.10:7125
```

### Klipper with custom port
```
MOONRAKER_URL=http://192.168.1.10:7126
```

### Using hostname instead of IP
```
MOONRAKER_URL=http://mainsail.local:7125
```

## Troubleshooting

### Connection Issues
- Verify the IP address and port are correct
- Make sure your printer is on the same network
- Check that Moonraker is running and accessible
- Test the URL in your browser: `http://YOUR_PRINTER_IP:7125/printer/info`

### Network Discovery
If you don't know your printer's IP address:

```bash
# Scan your local network (replace 192.168.1.0/24 with your network)
nmap -sn 192.168.1.0/24

# Or check for devices with port 7125 open
nmap -p 7125 192.168.1.0/24
```

## Environment File Reference

Complete `.env` file example:

```env
# Required: Moonraker URL
MOONRAKER_URL=http://192.168.1.10:7125

# Optional: Poll interval (seconds)
POLL_INTERVAL=15

# Optional: Database location
SQLALCHEMY_DATABASE_URI=sqlite:///printer_logbook.db

# Optional: Upload folder for G-code files
UPLOAD_FOLDER=uploads
```

## Security Notes

- Keep your `.env` file private (it's already in `.gitignore`)
- If your Moonraker instance is password-protected, you'll need to implement authentication
- Consider using HTTPS if your Moonraker supports it