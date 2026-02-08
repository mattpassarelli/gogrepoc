# GOGRepoc Desktop - User Guide

Welcome to GOGRepoc Desktop! This guide will help you install, configure, and use the application to manage your GOG game library.

## Table of Contents

- [Installation](#installation)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [Getting Started](#getting-started)
- [Basic Usage](#basic-usage)
- [Features](#features)
- [Settings](#settings)
- [Common Issues](#common-issues)
- [FAQ](#faq)

## Installation

### Windows

**System Requirements**:
- Windows 10 or later (64-bit)
- 500 MB free disk space
- Internet connection

**Installation Steps**:

1. **Download the installer**:
   - Download `GOGRepoc-Setup-2.0.0.exe` from the releases page

2. **Run the installer**:
   - Double-click the downloaded file
   - If Windows Defender SmartScreen appears, click "More info" → "Run anyway"
   - Follow the installation wizard
   - Choose installation location (default: `C:\Program Files\GOGRepoc`)

3. **Launch the application**:
   - Use the desktop shortcut or Start menu entry
   - First launch may take a few seconds while the backend initializes

**Portable Version**:
- Download `GOGRepoc-2.0.0-portable.exe`
- No installation required - just run the executable
- Settings stored in the same directory as the executable

**Uninstallation**:
- Use Windows Settings → Apps → GOGRepoc → Uninstall
- Or run the uninstaller from the installation directory

### macOS

**System Requirements**:
- macOS 10.15 (Catalina) or later
- Apple Silicon or Intel processor
- 500 MB free disk space
- Internet connection

**Installation Steps**:

1. **Download the disk image**:
   - Download `GOGRepoc-2.0.0.dmg` from the releases page

2. **Install the application**:
   - Double-click the DMG file to mount it
   - Drag the GOGRepoc icon to the Applications folder
   - Eject the disk image

3. **First launch**:
   - Open Applications folder
   - Right-click GOGRepoc → Open (first time only)
   - Click "Open" in the security dialog
   - Subsequent launches: just double-click

**Gatekeeper Issues**:
If macOS blocks the app:
1. Open System Preferences → Security & Privacy
2. Click "Open Anyway" next to the GOGRepoc message
3. Or use Terminal:
   ```bash
   xattr -d com.apple.quarantine /Applications/GOGRepoc.app
   ```

**Uninstallation**:
- Drag GOGRepoc from Applications to Trash
- Delete settings (optional):
  ```bash
  rm -rf ~/Library/Application\ Support/gogrepoc-desktop
  rm -rf ~/Library/Logs/gogrepoc-desktop
  ```

### Linux

**System Requirements**:
- Modern Linux distribution (Ubuntu 20.04+, Fedora 35+, etc.)
- 64-bit processor
- 500 MB free disk space
- Internet connection

**Installation Options**:

#### AppImage (Recommended)

1. **Download AppImage**:
   - Download `GOGRepoc-2.0.0.AppImage`

2. **Make executable**:
   ```bash
   chmod +x GOGRepoc-2.0.0.AppImage
   ```

3. **Run**:
   ```bash
   ./GOGRepoc-2.0.0.AppImage
   ```

4. **Optional: Integrate with system**:
   - Right-click AppImage → "Integrate and run"
   - Or use AppImageLauncher

**Requirements**:
- FUSE library: `sudo apt install fuse` (Ubuntu/Debian)

#### Debian/Ubuntu (.deb)

```bash
# Download the .deb file
wget <url>/gogrepoc-desktop_2.0.0_amd64.deb

# Install
sudo dpkg -i gogrepoc-desktop_2.0.0_amd64.deb

# Fix dependencies if needed
sudo apt-get install -f

# Launch
gogrepoc-desktop
```

#### Fedora/RHEL (.rpm)

```bash
# Download the .rpm file
wget <url>/gogrepoc-desktop-2.0.0.x86_64.rpm

# Install
sudo rpm -i gogrepoc-desktop-2.0.0.x86_64.rpm

# Or with dnf
sudo dnf install gogrepoc-desktop-2.0.0.x86_64.rpm

# Launch
gogrepoc-desktop
```

**Uninstallation**:
- AppImage: Just delete the file
- .deb: `sudo apt remove gogrepoc-desktop`
- .rpm: `sudo rpm -e gogrepoc-desktop`

## Getting Started

### First Launch

1. **Application starts**:
   - The backend initializes (may take 5-10 seconds)
   - Main window appears with the GOGRepoc interface

2. **Login to GOG**:
   - Enter your GOG username and password
   - If you have two-factor authentication enabled, enter the code
   - Click "Login"

3. **Select download directory**:
   - Click "Select Directory" or use File → Select Download Directory
   - Choose where you want to download games
   - The application remembers your choice

4. **Load your library**:
   - Click "Load Manifest" to fetch your game library
   - This may take a minute depending on library size

### Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│ File  Edit  View  Help                                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Login Section                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Username: [________________]                      │  │
│  │ Password: [________________]                      │  │
│  │ 2FA Code: [______]                                │  │
│  │ [Login]                                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Download Directory                                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │ /path/to/downloads  [Select Directory]           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Game Library                                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ☐ Game 1                                          │  │
│  │ ☐ Game 2                                          │  │
│  │ ☐ Game 3                                          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  [Download Selected]  [Cancel]                          │
│                                                          │
│  Progress: ████████░░░░░░░░░░ 45%                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Basic Usage

### Downloading Games

1. **Login** to your GOG account (if not already logged in)

2. **Load your library**:
   - Click "Load Manifest"
   - Wait for your game list to appear

3. **Select games**:
   - Check the boxes next to games you want to download
   - Use filters to find specific games (if available)

4. **Choose download location**:
   - Click "Select Directory"
   - Choose where to save the games

5. **Start download**:
   - Click "Download Selected"
   - Monitor progress in the progress bar
   - Downloads continue in the background

6. **Download completes**:
   - Notification appears when finished
   - Games are saved in the selected directory

### Managing Downloads

**Pause/Resume**:
- Click "Pause" to temporarily stop downloads
- Click "Resume" to continue

**Cancel**:
- Click "Cancel" to stop and discard current downloads

**View Progress**:
- Progress bar shows overall completion
- Individual game progress shown in the list

### Filtering Games

Use filters to find specific games:
- **Platform**: Windows, macOS, Linux
- **Language**: English, French, German, etc.
- **Type**: Installers, extras, DLC
- **Status**: Owned, not downloaded, updated

## Features

### Automatic Backend Management

The application automatically:
- Starts the Python backend when you launch the app
- Monitors backend health
- Restarts the backend if it crashes
- Shuts down the backend when you close the app

You don't need to manage any background processes manually.

### Native File Dialogs

Directory selection uses your operating system's native file picker:
- Familiar interface
- Access to all your folders
- Remembers last selected location

### Settings Persistence

The application remembers:
- Last download directory
- Window size and position
- Login credentials (if saved)
- UI preferences

Settings are stored securely in your user directory.

### Error Recovery

If something goes wrong:
- Clear error messages explain the issue
- Automatic retry for transient failures
- Option to view logs for troubleshooting
- Graceful degradation (app remains usable)

### Logging

All operations are logged for troubleshooting:
- **Windows**: `%APPDATA%\gogrepoc-desktop\logs\`
- **macOS**: `~/Library/Logs/gogrepoc-desktop/`
- **Linux**: `~/.config/gogrepoc-desktop/logs/`

Access logs via Help → View Logs.

## Settings

### Application Settings

Settings are stored in:
- **Windows**: `%APPDATA%\gogrepoc-desktop\config.json`
- **macOS**: `~/Library/Application Support/gogrepoc-desktop/config.json`
- **Linux**: `~/.config/gogrepoc-desktop/config.json`

**Available Settings**:
- `lastDirectory`: Last selected download directory
- `windowBounds`: Window size and position
- `theme`: UI theme (light/dark/system)
- `autoUpdate`: Enable automatic updates (if supported)

### Resetting Settings

If the app behaves unexpectedly, reset settings:

1. Close the application
2. Delete the config file (see locations above)
3. Restart the application
4. Settings will be reset to defaults

## Common Issues

### "Backend failed to start"

**Cause**: The Python backend couldn't initialize

**Solutions**:
1. Click "Retry" in the error dialog
2. Check if another instance is running
3. Check if ports 8000-9000 are available
4. View logs for detailed error information
5. Restart your computer

### "Health check timeout"

**Cause**: Backend started but didn't respond in time

**Solutions**:
1. Wait a bit longer (first launch can be slow)
2. Check firewall settings (allow localhost connections)
3. Check antivirus settings (may block the backend)
4. View logs for errors

### Window appears off-screen

**Cause**: Multi-monitor setup changed

**Solution**:
1. Close the application
2. Delete the config file (see Settings section)
3. Restart the application
4. Window will appear at default position

### Downloads fail or are slow

**Causes**: Network issues, GOG server issues

**Solutions**:
1. Check your internet connection
2. Try again later (GOG servers may be busy)
3. Check GOG website status
4. Disable VPN if using one
5. Check firewall/antivirus settings

### "Permission denied" errors

**Cause**: Insufficient permissions for download directory

**Solutions**:
1. Choose a different download directory
2. Check folder permissions
3. Run as administrator (Windows) - not recommended
4. Use a directory in your user folder

### Application won't start

**Platform-specific solutions**:

**Windows**:
- Check Windows Defender / antivirus logs
- Run as administrator (once)
- Reinstall the application

**macOS**:
- Right-click → Open (bypass Gatekeeper)
- Check System Preferences → Security & Privacy
- Remove quarantine attribute (see Installation)

**Linux**:
- Make AppImage executable: `chmod +x`
- Install FUSE: `sudo apt install fuse`
- Check for missing libraries: `ldd GOGRepoc.AppImage`

## FAQ

### Do I need Python installed?

No! The application includes a bundled Python runtime. You don't need to install Python separately.

### Where are my games downloaded?

Games are downloaded to the directory you select. The application remembers your choice between sessions.

### Can I download multiple games at once?

Yes! Select multiple games and click "Download Selected". They will download sequentially.

### Does this work with GOG Galaxy?

GOGRepoc Desktop is independent of GOG Galaxy. You can use both, but they don't share settings or download locations.

### Is my login information secure?

Yes. Login credentials are sent directly to GOG's servers using HTTPS. The application doesn't store your password unless you explicitly choose to save it.

### Can I use this offline?

You need an internet connection to:
- Login to GOG
- Load your game library
- Download games

Once games are downloaded, you can install and play them offline.

### How do I update the application?

**Manual update**:
1. Download the latest version
2. Install over the existing version
3. Your settings are preserved

**Automatic updates** (if enabled):
- The app checks for updates on startup
- You'll be notified when an update is available
- Click "Update" to download and install

### Where can I get help?

1. Check this user guide
2. View logs (Help → View Logs)
3. Check the GitHub issues page
4. Create a new issue with:
   - Your operating system
   - App version (Help → About)
   - Steps to reproduce the problem
   - Log files (redact sensitive info)

### How do I uninstall?

See the [Installation](#installation) section for platform-specific uninstallation instructions.

### Can I move the application to a different computer?

Yes! Just install on the new computer. Your GOG library will be available after logging in.

To transfer settings:
1. Copy the config file from the old computer (see Settings section)
2. Place it in the same location on the new computer

### Does this support all GOG games?

Yes! GOGRepoc Desktop supports all games in your GOG library, including:
- Windows, macOS, and Linux versions
- DLC and extras
- Multiple languages
- Patches and updates

---

**Need more help?** Visit the [GitHub repository](https://github.com/your-repo/gogrepoc) or create an issue.
