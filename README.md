# GOGRepoc - GOG Game Collection Manager

## WIP Notice

In the effort of transparency, as it currently sits, a *massive* amount of this codebase's refactoring was done by Claude via Amazon's Kiro IDE. I had the opportunity to attend a training workshop and was told I needed a project idea in mind. Which lead to this refactor of the original forked project. 

At the time of this README commit, a large amount of this refactor was done by Kiro/Claude and remains mostly untested. As with a lot of AI code I've seen and written, it's pretty buggy and broken, having only a basic high-level grasps as to what is needed. I've started going through code by hand to start fixing things, mostly just relying on the AI to have generated workspace structure and boilerplate the new models and classes. Right now, Logging-In via the CLI works, but downloads are broken and the UI and electron builds are completely untested.

---


[![Build Electron Desktop App](https://github.com/yourusername/gogrepoc/actions/workflows/electron-build.yml/badge.svg)](https://github.com/yourusername/gogrepoc/actions/workflows/electron-build.yml)

Python-based tool for downloading and managing your GOG.com game collections and extras to your local computer for full offline enjoyment.

**Note:** This is a refactored version with improved architecture, modern Python practices, and multiple interfaces (CLI, API, Web UI).

## Features

* **Multiple Interfaces**: Command-line (CLI), REST API, Web UI, and Desktop Application
* **Desktop Application**: Native Electron-based desktop app for Windows, macOS, and Linux
* **Modern Architecture**: Clean separation of concerns with services, infrastructure, and API layers
* **Async Support**: Efficient async/await for network operations
* **Download Management**: Resume support, MD5 verification, concurrent downloads
* **Flexible Filtering**: Choose games by OS (Windows, Linux, Mac) and language
* **Progress Tracking**: Real-time download progress with Server-Sent Events (SSE)
* **Authentication**: Secure token storage with automatic refresh
* **Cross-Platform**: Works on Windows, Linux, and macOS

## Requirements

* Python 3.13+ (uses modern Python features)
* Dependencies (install via `pip install -r requirements.txt`):
  - `httpx` - Modern async HTTP client
  - `click` - CLI framework
  - `fastapi` - Web API framework
  - `uvicorn` - ASGI server
  - `pydantic` - Data validation
  - `html5lib` - HTML parsing
  - `beautifulsoup4` - Web scraping
  - `cryptography` - Secure token storage

## Installation

### Desktop Application (Recommended for Most Users)

The easiest way to use GOGRepoc is with the native desktop application. Download the latest release for your platform:

**[Download Latest Release](https://github.com/yourusername/gogrepoc/releases/latest)**

**Windows**:
- Download `GOGRepoc-<version>-x64.exe` (installer) or `GOGRepoc-<version>-portable.exe`
- Run the installer or portable executable
- No Python installation required

**macOS**:
- Download `GOGRepoc-<version>.dmg`
- Open the DMG and drag GOGRepoc to Applications
- Right-click → Open (first time only, to bypass Gatekeeper)
- No Python installation required

**Linux**:
- Download `GOGRepoc-<version>.AppImage`, `.deb`, or `.rpm`
- **AppImage**: `chmod +x GOGRepoc-*.AppImage && ./GOGRepoc-*.AppImage`
- **Debian/Ubuntu**: `sudo dpkg -i gogrepoc-desktop_*_amd64.deb`
- **Fedora/RHEL**: `sudo rpm -i gogrepoc-desktop-*.x86_64.rpm`
- No Python installation required

For desktop app documentation, see [electron/README.md](electron/README.md).

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/gogrepoc.git
cd gogrepoc

# Install dependencies
uv pip install -r requirements.txt
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/gogrepoc.git
cd gogrepoc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### CLI Usage

The CLI provides a simple command-line interface for managing your GOG collection.

#### 1. Login to GOG

```bash
python -m gogrepoc.cli.main login
# Or provide credentials directly:
python -m gogrepoc.cli.main login user@example.com password
# With 2FA:
python -m gogrepoc.cli.main login user@example.com password --two-factor 123456
```

#### 2. Update Game Manifest

Fetch your game library from GOG:

```bash
# Update all games
python -m gogrepoc.cli.main update

# Update specific games by ID
python -m gogrepoc.cli.main update --ids 1234 5678

# Filter by OS and language
python -m gogrepoc.cli.main update --os windows --os linux --lang en
```

#### 3. Download Games

```bash
# Download all games to a directory
python -m gogrepoc.cli.main download /path/to/games

# Download specific games
python -m gogrepoc.cli.main download /path/to/games --ids 1234 5678

# Filter downloads
python -m gogrepoc.cli.main download /path/to/games --os windows --lang en

# Adjust concurrent downloads (default: 4)
python -m gogrepoc.cli.main download /path/to/games --concurrent 8
```

#### 4. Other CLI Commands

```bash
# Backup manifest and tokens
python -m gogrepoc.cli.main backup /path/to/backup

# Clean temporary files
python -m gogrepoc.cli.main clean /path/to/games
python -m gogrepoc.cli.main clean /path/to/games --dry-run

# Move files to trash
python -m gogrepoc.cli.main trash file1.exe file2.bin

# Compress files with 7zip
python -m gogrepoc.cli.main compress file1.exe --level 9
```

#### CLI Global Options

```bash
# Enable verbose logging
python -m gogrepoc.cli.main --verbose update

# Use custom config directory
python -m gogrepoc.cli.main --config-dir ~/.my-gog-config login

# Write logs to file
python -m gogrepoc.cli.main --log-file gogrepo.log update
```

### API Usage

The REST API provides programmatic access to all GOGRepoc functionality.

#### Starting the API Server

```bash
# Start with uvicorn
uvicorn gogrepoc.api.main:app --host 0.0.0.0 --port 8000

# With auto-reload for development
uvicorn gogrepoc.api.main:app --reload --port 8000
```

#### API Endpoints

**Authentication:**
- `POST /api/login` - Login with GOG credentials
- `GET /api/check-auth` - Check authentication status

**Manifest Management:**
- `GET /api/manifest` - Get game manifest (with optional filters)
- `POST /api/update` - Update manifest from GOG
- `POST /api/add_without_download` - Add games to manifest without downloading

**Downloads:**
- `POST /api/download` - Start download task
- `GET /api/download-progress/{task_id}` - Stream download progress (SSE)

**Health:**
- `GET /health` - Health check endpoint

#### API Examples

```bash
# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password"}'

# Check auth status
curl http://localhost:8000/api/check-auth

# Get manifest
curl http://localhost:8000/api/manifest

# Get manifest with filters
curl "http://localhost:8000/api/manifest?os_types=windows&languages=en"

# Update manifest
curl -X POST http://localhost:8000/api/update \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [1234, 5678], "os_types": ["windows"], "languages": ["en"]}'

# Start download
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"game_ids": [1234], "save_dir": "/tmp/games", "os_types": ["windows"]}'

# Monitor download progress (Server-Sent Events)
curl http://localhost:8000/api/download-progress/task-id-here
```

#### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Web UI Usage

The Web UI provides a modern, user-friendly interface for managing your GOG collection.

#### Starting the Web UI

**Option 1: Development Mode (with hot reload)**

```bash
# Terminal 1: Start the API server
uvicorn gogrepoc.api.main:app --reload --port 8000

# Terminal 2: Start the React dev server
cd ui
npm install  # First time only
npm start
```

Then open `http://localhost:3000` in your browser.

**Option 2: Production Mode**

```bash
# Build the React app
cd ui
npm install  # First time only
npm run build
cd ..

# Start the API server (serves both API and UI)
uvicorn gogrepoc.api.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in your browser.

**Option 3: Separate Servers**

```bash
# Terminal 1: Start the API server
uvicorn gogrepoc.api.main:app --port 8000

# Terminal 2: Serve the built UI
cd ui
npm run build  # First time only
python -m http.server 3000 --directory build
```

Then open `http://localhost:3000` in your browser.

#### Web UI Features

* **Clean Interface**: Modern, responsive design with dark mode support
* **Game Library**: Browse and search your GOG game collection
* **Download Queue**: Select games and manage download queue
* **Real-time Progress**: Live download progress with speed and ETA
* **Filtering**: Filter games by OS, language, and download status
* **Settings**: Configure download directory, compression, and preferences

#### Web UI Workflow

1. **Login**: Enter your GOG credentials
2. **Update Library**: Click "Update List" to fetch your games from GOG
3. **Browse Games**: View your game collection in the Available Games list
4. **Select Games**: Click games to select them for download
5. **Configure**: Set download directory and options
6. **Download**: Click "Download Games" to start
7. **Monitor**: Watch real-time progress in the download panel

## Configuration

### Config Directory

By default, GOGRepoc stores configuration in `~/.gogrepoc/`:
- `gog-token.dat` - Encrypted authentication token
- `gog-manifest.dat` - Game manifest (JSON)
- `gog-downloaded-games.dat` - Download tracking

You can change this with the `--config-dir` option (CLI) or by setting environment variables.

### Environment Variables

```bash
# API server configuration
export GOGREPOC_HOST=0.0.0.0
export GOGREPOC_PORT=8000
export GOGREPOC_CONFIG_DIR=~/.gogrepoc

# Logging
export GOGREPOC_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
export GOGREPOC_LOG_FILE=gogrepo.log
```

## Architecture

The refactored codebase follows clean architecture principles:

```
gogrepoc/
├── api/           # FastAPI REST API
│   ├── main.py    # FastAPI app and middleware
│   ├── routes.py  # API endpoints
│   └── schemas.py # Pydantic models
├── cli/           # Click-based CLI
│   └── main.py    # CLI commands
├── core/          # Domain models and exceptions
│   ├── models.py      # Game, Download, Token models
│   ├── exceptions.py  # Custom exceptions
│   └── constants.py   # Constants
├── services/      # Business logic
│   ├── auth.py        # Authentication service
│   ├── gog_api.py     # GOG API client
│   ├── manifest.py    # Manifest management
│   └── downloader.py  # Download service
├── infrastructure/ # External dependencies
│   ├── http_client.py  # HTTP client wrapper
│   ├── storage.py      # File storage
│   ├── file_system.py  # File operations
│   └── platform.py     # Platform detection
└── utils/         # Utilities
    ├── logging_config.py
    ├── compression.py
    ├── hashing.py
    └── wakelock.py
```

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test files
python -m pytest tests/unit/test_cli.py
python -m pytest tests/unit/test_api.py
python -m pytest tests/unit/test_auth.py

# Run with coverage
python -m pytest --cov=gogrepoc --cov-report=html

# Run with verbose output
python -m pytest -v
```

## Development

### Releases and CI/CD

The project uses GitHub Actions for automated builds and releases:

**Creating a Release**:
1. Update version in `package.json` and `pyproject.toml`
2. Commit changes: `git commit -am "Release v1.0.0"`
3. Create and push tag: `git tag v1.0.0 && git push origin v1.0.0`
4. GitHub Actions automatically builds for all platforms
5. Release is created with installers attached

**Build Status**: Check the [Actions tab](https://github.com/yourusername/gogrepoc/actions) for build status

**Versioning**: Follow [Semantic Versioning](https://semver.org/):
- **Major** (v2.0.0): Breaking changes
- **Minor** (v1.1.0): New features, backwards compatible
- **Patch** (v1.0.1): Bug fixes

For detailed build documentation, see [.github/workflows/README.md](.github/workflows/README.md).

### Code Style

The project uses:
- `black` for code formatting
- `isort` for import sorting
- `flake8` for linting
- `mypy` for type checking

```bash
# Format code
black gogrepoc tests

# Sort imports
isort gogrepoc tests

# Lint
flake8 gogrepoc tests

# Type check
mypy gogrepoc
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Troubleshooting

### Authentication Issues

If you get authentication errors:
1. Delete `~/.gogrepoc/gog-token.dat`
2. Run `python -m gogrepoc.cli.main login` again
3. If using 2FA, make sure to provide the code with `--two-factor`

### Download Issues

If downloads fail or hang:
1. Check your internet connection
2. Try reducing concurrent downloads: `--concurrent 2`
3. Check GOG's server status
4. Look at logs for specific error messages

### API Server Issues

If the API server won't start:
1. Check if port 8000 is already in use
2. Try a different port: `uvicorn gogrepoc.api.main:app --port 8080`
3. Check logs for error messages

### Web UI Issues

If the Web UI doesn't load:
1. Make sure the API server is running
2. Check browser console for errors
3. Verify CORS settings if using separate servers
4. Clear browser cache and reload

## License

GPLv3+

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## Credits

Based on the original gogrepo by [original author].
Refactored and modernized by the community.

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing issues for solutions
- Consult the documentation

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.
