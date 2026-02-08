# GOGRepoc Refactoring Design Document

## Architecture Overview

The refactored application will follow a layered architecture:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  (React UI + FastAPI Endpoints)         │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         Application Layer               │
│  (CLI Commands + Business Logic)        │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         Domain Layer                    │
│  (Core Models + Services)               │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         Infrastructure Layer            │
│  (GOG API + File System + Storage)      │
└─────────────────────────────────────────┘
```

## Module Structure

```
gogrepoc/
├── __init__.py
├── __main__.py              # Entry point for executable
├── core/
│   ├── __init__.py
│   ├── models.py            # Data models (Game, Download, Manifest)
│   ├── exceptions.py        # Custom exceptions
│   └── constants.py         # Constants and configuration
├── services/
│   ├── __init__.py
│   ├── gog_api.py          # GOG API client
│   ├── auth.py             # Authentication service
│   ├── manifest.py         # Manifest management
│   ├── downloader.py       # Download orchestration
│   ├── verifier.py         # File verification
│   └── importer.py         # Import existing files
├── infrastructure/
│   ├── __init__.py
│   ├── http_client.py      # HTTP client wrapper
│   ├── file_system.py      # File system operations
│   ├── storage.py          # Token/manifest storage
│   └── platform.py         # Platform-specific code
├── cli/
│   ├── __init__.py
│   ├── main.py             # CLI entry point
│   └── commands.py         # CLI command implementations
├── api/
│   ├── __init__.py
│   ├── main.py             # FastAPI app
│   ├── routes.py           # API endpoints
│   └── schemas.py          # Pydantic models
├── ui/
│   └── build/              # Built React app (bundled)
└── utils/
    ├── __init__.py
    ├── hashing.py          # MD5 and file hashing
    ├── compression.py      # 7zip compression
    ├── logging_config.py   # Logging setup
    └── wakelock.py         # Sleep prevention

tests/
├── unit/
│   ├── test_models.py
│   ├── test_gog_api.py
│   ├── test_auth.py
│   ├── test_manifest.py
│   ├── test_downloader.py
│   ├── test_verifier.py
│   └── test_utils.py
├── integration/
│   ├── test_download_flow.py
│   ├── test_update_flow.py
│   └── test_verify_flow.py
└── conftest.py             # Pytest fixtures
```

## Core Models

### Game Model
```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Download:
    name: str
    href: str
    size: int
    md5: Optional[str]
    os_type: str
    lang: str
    version: Optional[str]
    desc: str
    updated: Optional[datetime]
    verified: bool = False

@dataclass
class Extra:
    name: str
    href: str
    size: int
    desc: str
    updated: Optional[datetime]

@dataclass
class Game:
    id: int
    title: str
    folder_name: str
    long_title: str
    downloads: List[Download]
    galaxy_downloads: List[Download]
    shared_downloads: List[Download]
    extras: List[Extra]
    serials: dict[str, str]
    changelog: Optional[str]
    image_url: str
    bg_url: str
    store_url: str
    has_updates: bool
```

## Service Layer Design

### GOG API Service
```python
class GOGAPIService:
    """Handles all interactions with GOG API"""
    
    def __init__(self, http_client: HTTPClient, auth_service: AuthService):
        self.http_client = http_client
        self.auth_service = auth_service
    
    async def get_games_list(self, page: int = 1) -> dict:
        """Fetch paginated games list"""
        
    async def get_game_details(self, game_id: int) -> dict:
        """Fetch detailed game information"""
        
    async def get_download_link(self, href: str) -> str:
        """Get actual download URL"""
```

### Authentication Service
```python
class AuthService:
    """Manages GOG authentication and tokens"""
    
    def __init__(self, storage: Storage, http_client: HTTPClient):
        self.storage = storage
        self.http_client = http_client
    
    def get_auth_url(self) -> str:
        """Generate GOG OAuth authorization URL for browser"""
        
    async def login_with_code(self, auth_code: str) -> Token:
        """Exchange authorization code for access token"""
        
    async def login(self, username: str, password: str, two_factor_code: Optional[str] = None) -> Token:
        """Authenticate with GOG (legacy/programmatic flow)"""
        
    async def refresh_token(self) -> Token:
        """Refresh expired token"""
        
    def is_authenticated(self) -> bool:
        """Check if valid token exists"""
```

### Manifest Service
```python
class ManifestService:
    """Manages game manifest"""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    def load_manifest(self) -> List[Game]:
        """Load manifest from disk"""
        
    def save_manifest(self, games: List[Game]) -> None:
        """Save manifest to disk"""
        
    def update_game(self, game: Game) -> None:
        """Update single game in manifest"""
        
    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        """Retrieve game from manifest"""
```

### Download Service
```python
class DownloadService:
    """Orchestrates file downloads"""
    
    def __init__(
        self,
        http_client: HTTPClient,
        file_system: FileSystem,
        manifest_service: ManifestService
    ):
        self.http_client = http_client
        self.file_system = file_system
        self.manifest_service = manifest_service
    
    async def download_game(
        self,
        game: Game,
        save_dir: Path,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Download all files for a game"""
        
    async def download_file(
        self,
        download: Download,
        dest_path: Path,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Download single file with resume support"""
```

### Verification Service
```python
class VerificationService:
    """Verifies downloaded files"""
    
    def __init__(self, file_system: FileSystem):
        self.file_system = file_system
    
    def verify_game(self, game: Game, game_dir: Path) -> VerificationResult:
        """Verify all files for a game"""
        
    def verify_file(
        self,
        file_path: Path,
        expected_size: int,
        expected_md5: Optional[str]
    ) -> bool:
        """Verify single file"""
```

## Infrastructure Layer

### HTTP Client
```python
class HTTPClient:
    """Wrapper around requests/httpx with retry logic"""
    
    def __init__(self, timeout: int = 60, max_retries: int = 4):
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def get(self, url: str, **kwargs) -> Response:
        """GET request with retry"""
        
    async def post(self, url: str, **kwargs) -> Response:
        """POST request with retry"""
        
    async def head(self, url: str, **kwargs) -> Response:
        """HEAD request with retry"""
        
    async def download_stream(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Stream download to file"""
```

### File System
```python
class FileSystem:
    """Abstraction over file system operations"""
    
    def ensure_dir(self, path: Path) -> None:
        """Create directory if not exists"""
        
    def move_file(self, src: Path, dest: Path) -> None:
        """Move file with conflict resolution"""
        
    def hash_file(self, path: Path) -> str:
        """Calculate MD5 hash"""
        
    def get_file_size(self, path: Path) -> int:
        """Get file size in bytes"""
        
    def preallocate_file(self, path: Path, size: int) -> None:
        """Preallocate disk space"""
```

### Storage
```python
class Storage:
    """Handles persistent storage of tokens and manifests"""
    
    def save_token(self, token: Token) -> None:
        """Save authentication token"""
        
    def load_token(self) -> Optional[Token]:
        """Load authentication token"""
        
    def save_manifest(self, manifest: List[Game]) -> None:
        """Save game manifest"""
        
    def load_manifest(self) -> List[Game]:
        """Load game manifest"""
```

## API Layer

### FastAPI Application
```python
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="GOGRepoc API")

# Mount React UI
app.mount("/", StaticFiles(directory="ui/build", html=True), name="ui")

# API routes
@app.post("/api/login")
async def login(request: LoginRequest, auth: AuthService = Depends()):
    """Authenticate with GOG"""

@app.post("/api/update")
async def update(request: UpdateRequest, services = Depends()):
    """Update game manifest"""

@app.post("/api/download")
async def download(request: DownloadRequest, services = Depends()):
    """Download games"""

@app.get("/api/manifest")
async def get_manifest(manifest_service: ManifestService = Depends()):
    """Get current manifest"""

@app.get("/api/download-progress/{task_id}")
async def get_progress(task_id: str):
    """Get download progress via SSE"""
```

## CLI Layer

### Command Structure
```python
import click

@click.group()
def cli():
    """GOGRepoc - Download your GOG games"""
    pass

@cli.command()
@click.argument('username', required=False)
@click.argument('password', required=False)
def login(username: Optional[str], password: Optional[str]):
    """Login to GOG"""
    
@cli.command()
@click.option('--os', multiple=True)
@click.option('--lang', multiple=True)
@click.option('--ids', multiple=True)
def update(os: tuple, lang: tuple, ids: tuple):
    """Update game manifest"""
    
@cli.command()
@click.argument('savedir', default='.')
@click.option('--ids', multiple=True)
@click.option('--os', multiple=True)
def download(savedir: str, ids: tuple, os: tuple):
    """Download games"""
```

## Executable Packaging

### PyInstaller Configuration
```python
# gogrepoc.spec
a = Analysis(
    ['gogrepoc/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gogrepoc/ui/build', 'ui/build'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.protocols',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gogrepoc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### Entry Point
```python
# gogrepoc/__main__.py
import sys
import webbrowser
import threading
from pathlib import Path
import uvicorn

def start_server():
    """Start FastAPI server"""
    uvicorn.run(
        "gogrepoc.api.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

def open_browser():
    """Open browser after short delay"""
    import time
    time.sleep(2)
    webbrowser.open("http://localhost:8000")

def main():
    if len(sys.argv) > 1:
        # CLI mode
        from gogrepoc.cli.main import cli
        cli()
    else:
        # GUI mode
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        print("GOGRepoc is running at http://localhost:8000")
        print("Press Ctrl+C to exit")
        
        try:
            server_thread.join()
        except KeyboardInterrupt:
            print("\nShutting down...")

if __name__ == "__main__":
    main()
```

## Testing Strategy

### Unit Tests
- Mock all external dependencies (HTTP, file system)
- Test each service in isolation
- Use pytest fixtures for common test data
- Aim for 80%+ coverage

### Integration Tests
- Test complete workflows (login → update → download)
- Use temporary directories for file operations
- Mock only external GOG API calls
- Test error handling and recovery

### Test Fixtures
```python
# tests/conftest.py
import pytest
from pathlib import Path
from gogrepoc.core.models import Game, Download

@pytest.fixture
def sample_game():
    return Game(
        id=1,
        title="test_game",
        folder_name="test_game",
        long_title="Test Game",
        downloads=[],
        galaxy_downloads=[],
        shared_downloads=[],
        extras=[],
        serials={},
        changelog=None,
        image_url="",
        bg_url="",
        store_url="",
        has_updates=False
    )

@pytest.fixture
def temp_game_dir(tmp_path):
    game_dir = tmp_path / "games"
    game_dir.mkdir()
    return game_dir

@pytest.fixture
def mock_http_client(mocker):
    return mocker.Mock(spec=HTTPClient)
```

## Migration Strategy

### Phase 1: Core Refactoring
1. Create new module structure
2. Extract models and constants
3. Create service layer
4. Migrate authentication logic
5. Add unit tests for services

### Phase 2: Infrastructure
1. Create HTTP client wrapper
2. Create file system abstraction
3. Create storage layer
4. Add platform-specific code
5. Add unit tests for infrastructure

### Phase 3: Application Layer
1. Migrate CLI commands
2. Update FastAPI endpoints
3. Add integration tests
4. Update React UI for new API

### Phase 4: Packaging
1. Configure PyInstaller
2. Bundle React build
3. Test executable on all platforms
4. Create installation documentation

### Phase 5: Cleanup
1. Remove Python 2 code
2. Update dependencies
3. Add type hints everywhere
4. Run linters and formatters
5. Update documentation

## Backward Compatibility

### Manifest Format
- Keep existing manifest file format
- Add migration function if format changes
- Support reading old format

### Configuration
- Support existing token file format
- Migrate to new format on first run
- Keep file locations the same

## Performance Considerations

- Use async/await for I/O operations
- Implement connection pooling
- Use streaming for large downloads
- Implement efficient file hashing (chunked reading)
- Cache manifest in memory
- Use database for large libraries (optional future enhancement)

## Security Considerations

- Never log passwords or tokens
- Use HTTPS for all GOG API calls
- Validate all user inputs
- Sanitize file paths
- Use secure token storage (keyring library)
- Implement rate limiting for API calls

## Deployment

### Development
```bash
uv sync
uv run python -m gogrepoc
```

### Production Build
```bash
# Build React UI
cd ui && npm run build && cd ..

# Build executable
uv run pyinstaller gogrepoc.spec

# Output: dist/gogrepoc or dist/gogrepoc.exe
```

## CI/CD with GitHub Actions

### Automated Testing Workflow
```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.13']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      
      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run type checking
        run: uv run mypy gogrepoc
      
      - name: Run linters
        run: |
          uv run black --check gogrepoc tests
          uv run isort --check gogrepoc tests
          uv run flake8 gogrepoc tests
      
      - name: Run tests
        run: uv run pytest --cov=gogrepoc --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

### Automated Build Workflow
```yaml
# .github/workflows/build.yml
name: Build Executables

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            artifact_name: gogrepoc-linux
            asset_name: gogrepoc-linux-x64
          - os: windows-latest
            artifact_name: gogrepoc.exe
            asset_name: gogrepoc-windows-x64.exe
          - os: macos-latest
            artifact_name: gogrepoc
            asset_name: gogrepoc-macos-x64
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      
      - name: Set up Python
        run: uv python install 3.13
      
      - name: Install dependencies
        run: uv sync
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Build React UI
        run: |
          cd ui
          npm ci
          npm run build
          cd ..
      
      - name: Build executable
        run: uv run pyinstaller gogrepoc.spec
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.asset_name }}
          path: dist/${{ matrix.artifact_name }}
      
      - name: Create release
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v1
        with:
          files: dist/${{ matrix.artifact_name }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Code Quality Workflow
```yaml
# .github/workflows/quality.yml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      
      - name: Set up Python
        run: uv python install 3.13
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run security checks
        run: uv run bandit -r gogrepoc
      
      - name: Check dependency vulnerabilities
        run: uv run safety check
      
      - name: Run complexity analysis
        run: uv run radon cc gogrepoc -a
```

## Documentation Updates

- Update README with new architecture
- Add API documentation (OpenAPI/Swagger)
- Add developer guide
- Add contribution guidelines
- Update installation instructions
- Add troubleshooting guide

## GitHub Actions Integration

The project uses GitHub Actions for automated CI/CD:

### Workflow Overview
1. **Test Workflow** - Runs on every push/PR
   - Executes on Windows, macOS, and Linux
   - Runs type checking (mypy)
   - Runs linters (black, isort, flake8)
   - Runs test suite with coverage reporting
   - Uploads coverage to Codecov

2. **Build Workflow** - Runs on version tags
   - Builds executables for all three platforms
   - Bundles React UI into executables
   - Uploads artifacts to GitHub Actions
   - Creates GitHub releases automatically
   - Attaches executables to releases

3. **Quality Workflow** - Runs on every push/PR
   - Security scanning with bandit
   - Dependency vulnerability checks with safety
   - Code complexity analysis with radon

### Benefits
- Automated testing ensures code quality
- Cross-platform builds without manual intervention
- Consistent build environment using `uv`
- Fast dependency installation with `uv`
- Automatic releases reduce manual work
- Security checks catch vulnerabilities early
