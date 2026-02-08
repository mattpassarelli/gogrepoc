# GOGRepoc Refactoring Tasks

## Overview
This implementation plan covers phases 2-7 of the GOGRepoc refactoring project. Phase 1 (Project Setup and Core Structure) has been completed. Phases 8-12 (Executable Packaging, CI/CD, Testing, Documentation, and Release) are out of scope for this implementation.

**Note:** Tasks 11 (Verification Service) and 12 (Import Service) have been removed to prioritize getting the CLI and API/UI functional for user testing. These can be added back later if needed.

## Phase 1: Project Setup and Core Structure ✓ COMPLETED

- [x] 1. Setup new project structure
  - [x] 1.1 Create pyproject.toml with uv configuration
  - [x] 1.2 Create new directory structure (core/, services/, infrastructure/, etc.)
  - [x] 1.3 Setup pytest configuration
  - [x] 1.4 Setup mypy for type checking
  - [x] 1.5 Setup pre-commit hooks (black, isort, flake8)
  - [x] 1.6 Create .gitignore for Python project
  - [x] 1.7 Create GitHub Actions workflows directory (.github/workflows/)

- [x] 2. Create core models and constants
  - [x] 2.1 Create core/models.py with dataclasses (Game, Download, Extra, Token)
    - Define Download dataclass with name, href, size, md5, os_type, lang, version, desc, updated, verified fields
    - Define Extra dataclass with name, href, size, desc, updated fields
    - Define Game dataclass with id, title, folder_name, long_title, downloads, galaxy_downloads, shared_downloads, extras, serials, changelog, image_url, bg_url, store_url, has_updates fields
    - Define Token dataclass for authentication tokens
    - Add type hints using Python 3.13+ syntax
    - _Requirements: 1.1, 1.2, 2.3_
  
  - [x] 2.2 Write unit tests for core models
    - Test model instantiation and field validation
    - Test serialization/deserialization if implemented
    - _Requirements: 3.1, 3.3_
  
  - [x] 2.3 Create core/exceptions.py with custom exception classes
    - Define AuthError for authentication failures
    - Define NetworkError for network-related issues
    - Define FileSystemError for file operation failures
    - Define VerificationError for file verification failures
    - All exceptions should include helpful error messages
    - _Requirements: 6.1, 6.2, 6.4_
  
  - [x] 2.4 Create core/constants.py with all constants from gogrepoc.py
    - Extract GOG API URLs and endpoints
    - Extract default configuration values
    - Extract file patterns and extensions
    - Use uppercase naming convention for constants
    - _Requirements: 1.1, 2.3_

## Phase 2: Infrastructure Layer

- [x] 3. Create HTTP client wrapper
  - [x] 3.1 Create infrastructure/http_client.py with HTTPClient class
    - Implement __init__ with timeout and max_retries parameters
    - Use httpx or requests library as base
    - Setup session with connection pooling
    - _Requirements: 1.1, 2.3, 6.3_
  
  - [x] 3.2 Implement retry logic with exponential backoff
    - Implement retry decorator or wrapper function
    - Use exponential backoff algorithm (2^retry_count seconds)
    - Handle transient errors (timeouts, 5xx responses)
    - Log retry attempts at appropriate level
    - _Requirements: 6.3, 9.2_
  
  - [x] 3.3 Implement get/head/post methods
    - Implement async get() method with retry logic
    - Implement async head() method for metadata requests
    - Implement async post() method for authentication
    - Add timeout handling for all methods
    - _Requirements: 1.1, 6.5_
  
  - [x] 3.4 Implement streaming download with progress callback
    - Implement async download_stream() method
    - Support progress callback for UI updates
    - Use chunked reading for memory efficiency
    - Handle partial downloads and resume support
    - _Requirements: 1.1, 1.3_
  
  - [x] 3.5 Write unit tests for HTTP client
    - Mock HTTP responses using pytest-httpx or responses library
    - Test retry logic with simulated failures
    - Test timeout handling
    - Test streaming download
    - _Requirements: 3.1, 3.3, 3.4_

- [x] 4. Create file system abstraction
  - [x] 4.1 Create infrastructure/file_system.py with FileSystem class
    - Use pathlib.Path for all path operations
    - Implement ensure_dir() for directory creation
    - Implement get_file_size() for file size queries
    - _Requirements: 1.1, 5.1, 2.3_
  
  - [x] 4.2 Implement file operations (move, copy, hash)
    - Implement move_file() with conflict resolution
    - Implement copy_file() for backup operations
    - Implement hash_file() using MD5 algorithm
    - Use chunked reading for large files
    - _Requirements: 1.3, 5.4_
  
  - [x] 4.3 Implement file preallocation for supported platforms
    - Detect platform using sys.platform
    - Implement preallocate_file() for Windows (using win32file)
    - Implement preallocate_file() for Linux (using fallocate)
    - Implement preallocate_file() for macOS (using fcntl)
    - Gracefully handle unsupported platforms
    - _Requirements: 5.2, 5.3_
  
  - [x] 4.4 Write unit tests for file system operations
    - Use pytest tmp_path fixture for temporary directories
    - Test directory creation and deletion
    - Test file move and copy operations
    - Test file hashing with known MD5 values
    - Test preallocation on current platform
    - _Requirements: 3.1, 3.3, 3.4_

- [x] 5. Create storage layer
  - [x] 5.1 Create infrastructure/storage.py with Storage class
    - Implement __init__ with storage directory path
    - Define file paths for tokens and manifests
    - Use JSON for serialization
    - _Requirements: 1.1, 1.5, 7.1_
  
  - [x] 5.2 Implement token save/load with encryption
    - Implement save_token() with secure storage
    - Implement load_token() with decryption
    - Use keyring library or file-based encryption
    - Handle missing token file gracefully
    - _Requirements: 1.4, 6.5_
  
  - [x] 5.3 Implement manifest save/load with backward compatibility
    - Implement save_manifest() with JSON serialization
    - Implement load_manifest() with JSON deserialization
    - Support old manifest format from gogrepoc.py
    - Add migration logic for format changes
    - _Requirements: 1.3, 1.5_
  
  - [x] 5.4 Implement downloaded games manifest
    - Implement save_downloaded_games() for tracking downloads
    - Implement load_downloaded_games() for resume support
    - Track download status and verification state
    - _Requirements: 1.3_
  
  - [x] 5.5 Write unit tests for storage operations
    - Test token save/load cycle
    - Test manifest save/load cycle
    - Test backward compatibility with old format
    - Test error handling for corrupted files
    - _Requirements: 3.1, 3.3, 3.4_

- [x] 6. Create platform-specific utilities
  - [x] 6.1 Create infrastructure/platform.py with platform detection
    - Implement get_platform() returning 'windows', 'macos', or 'linux'
    - Implement get_filesystem_type() for current directory
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 6.2 Implement wakelock functionality
    - Create Wakelock class with __enter__ and __exit__ methods
    - Implement Windows wakelock using ctypes and SetThreadExecutionState
    - Implement macOS wakelock using caffeinate subprocess
    - Implement Linux wakelock using systemd-inhibit or caffeine
    - Gracefully handle platforms without wakelock support
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 6.3 Write platform-specific tests
    - Test platform detection on current OS
    - Test wakelock context manager
    - Test filesystem type detection
    - _Requirements: 3.1, 3.3, 5.5_

## Phase 3: Service Layer

- [x] 7. Create authentication service
  - [x] 7.1 Create services/auth.py with AuthService class
    - Implement __init__ with Storage and HTTPClient dependencies
    - Define GOG authentication endpoints
    - _Requirements: 1.1, 1.4_
  
  - [x] 7.2 Implement login method
    - Implement async login(username, password) method
    - Send credentials to GOG API
    - Parse and store authentication token
    - Handle authentication errors with AuthError
    - _Requirements: 1.4, 6.1, 6.2_
  
  - [x] 7.2.1 Add browser-based OAuth methods to AuthService
    - Implement get_auth_url() method to generate OAuth authorization URL
    - Include client_id, redirect_uri, response_type, and layout parameters
    - Implement async login_with_code(auth_code) method
    - Exchange authorization code for access/refresh tokens via TOKEN_URL
    - Parse token response and create Token object
    - Store token using storage.save_token()
    - Handle errors (invalid code, network failures)
    - Return Token object on success
    - _Requirements: 1.5.1, 1.5.4, 1.5.5, 1.5.6_
  
  - [x] 7.3 Implement token refresh logic
    - Implement async refresh_token() method
    - Check token expiration before API calls
    - Automatically refresh expired tokens
    - _Requirements: 1.4_
  
  - [x] 7.4 Implement authentication status check
    - Implement is_authenticated() method
    - Check for valid, non-expired token
    - _Requirements: 1.4_
  
  - [x] 7.5 Implement two-factor authentication support
    - Handle 2FA challenge responses
    - Prompt for 2FA code when required
    - _Requirements: 1.4_
  
  - [x] 7.6 Write unit tests for authentication service
    - Mock GOG API responses
    - Test successful login flow
    - Test failed login with invalid credentials
    - Test token refresh logic
    - Test 2FA flow
    - _Requirements: 3.1, 3.3, 3.6_

- [x] 8. Create GOG API service
  - [x] 8.1 Create services/gog_api.py with GOGAPIService class
    - Implement __init__ with HTTPClient and AuthService dependencies
    - Define all GOG API endpoints as constants
    - _Requirements: 1.1_
  
  - [x] 8.2 Implement get_games_list method
    - Implement async get_games_list(page) method
    - Handle pagination for large libraries
    - Parse JSON response into Game objects
    - _Requirements: 1.1_
  
  - [x] 8.3 Implement get_game_details method
    - Implement async get_game_details(game_id) method
    - Fetch detailed game information including downloads
    - Parse downloads, extras, and metadata
    - _Requirements: 1.1_
  
  - [x] 8.4 Implement get_download_link method
    - Implement async get_download_link(href) method
    - Resolve download URLs from GOG API
    - Handle URL expiration and refresh
    - _Requirements: 1.1_
  
  - [x] 8.5 Implement fetch_file_info method
    - Implement async fetch_file_info(url) method
    - Use HEAD request to get file size and metadata
    - _Requirements: 1.1_
  
  - [x] 8.6 Implement MD5 XML fetching
    - Implement async fetch_md5_xml(url) method
    - Parse XML response for MD5 checksums
    - Handle missing or malformed XML
    - _Requirements: 1.1, 1.3_
  
  - [x] 8.7 Write unit tests for GOG API service
    - Mock all GOG API endpoints
    - Test games list pagination
    - Test game details parsing
    - Test download link resolution
    - Test MD5 XML parsing
    - _Requirements: 3.1, 3.3, 3.6_

- [x] 9. Create manifest service
  - [x] 9.1 Create services/manifest.py with ManifestService class
    - Implement __init__ with Storage dependency
    - Maintain in-memory cache of manifest
    - _Requirements: 1.1, 1.3_
  
  - [x] 9.2 Implement load_manifest method
    - Implement load_manifest() method
    - Load from storage and cache in memory
    - Handle missing manifest file
    - _Requirements: 1.3_
  
  - [x] 9.3 Implement save_manifest method
    - Implement save_manifest() method
    - Save in-memory cache to storage
    - _Requirements: 1.3_
  
  - [x] 9.4 Implement update_game method
    - Implement update_game(game) method
    - Update or add game to manifest
    - Mark games with updates
    - _Requirements: 1.3_
  
  - [x] 9.5 Implement get_game_by_id method
    - Implement get_game_by_id(game_id) method
    - Return game from in-memory cache
    - _Requirements: 1.3_
  
  - [x] 9.6 Implement game filtering logic
    - Implement filter_games(os_types, languages) method
    - Filter downloads by OS and language
    - Support multiple OS and language selections
    - _Requirements: 1.3_
  
  - [x] 9.7 Write unit tests for manifest service
    - Test manifest load/save cycle
    - Test game updates and additions
    - Test game filtering by OS and language
    - Test get_game_by_id with valid and invalid IDs
    - _Requirements: 3.1, 3.3, 3.6_

- [x] 10. Create download service
  - [x] 10.1 Create services/downloader.py with DownloadService class
    - Implement __init__ with HTTPClient, FileSystem, and ManifestService dependencies
    - Setup thread pool for concurrent downloads
    - _Requirements: 1.1, 1.2_
  
  - [x] 10.2 Implement download_game method
    - Implement async download_game(game, save_dir, progress_callback) method
    - Download all files for a game (installers, extras)
    - Track overall progress across all files
    - Handle download failures and retries
    - _Requirements: 1.2, 1.3_
  
  - [x] 10.3 Implement download_file with resume support
    - Implement async download_file(download, dest_path, progress_callback) method
    - Check for existing partial downloads
    - Use HTTP Range header for resume
    - Verify file size matches expected
    - _Requirements: 1.2, 1.3_
  
  - [x] 10.4 Implement chunk-based download with MD5 verification
    - Download files in chunks (e.g., 8MB chunks)
    - Calculate MD5 hash during download
    - Verify MD5 against expected value
    - Move to final location only after verification
    - _Requirements: 1.2, 1.3_
  
  - [x] 10.5 Implement progress tracking
    - Track bytes downloaded per file
    - Track overall progress across all files
    - Call progress_callback with current status
    - Calculate download speed and ETA
    - _Requirements: 1.2, 8.1, 8.6_
  
  - [x] 10.6 Implement concurrent downloads
    - Use thread pool or asyncio for concurrent downloads
    - Limit concurrent downloads (e.g., 4 simultaneous)
    - Handle errors in individual downloads without stopping others
    - _Requirements: 1.2_
  
  - [x] 10.7 Write unit tests for download service
    - Mock HTTP downloads
    - Test single file download
    - Test resume functionality
    - Test MD5 verification
    - Test concurrent downloads
    - Test progress tracking
    - _Requirements: 3.1, 3.3, 3.6_

## Phase 4: Utilities

- [x] 11. Create utility modules
  - [x] 11.1 Create utils/hashing.py with MD5 functions
    - Implement calculate_md5(file_path) function
    - Use chunked reading for memory efficiency
    - Return hex digest string
    - _Requirements: 1.5_
  
  - [x] 11.2 Create utils/compression.py with 7zip wrapper
    - Implement compress_file(file_path, archive_path) function
    - Implement decompress_file(archive_path, dest_dir) function
    - Use subprocess to call 7zip binary
    - Handle 7zip not installed gracefully
    - _Requirements: 1.5_
  
  - [x] 11.3 Create utils/logging_config.py with logging setup
    - Implement setup_logging(level, log_file) function
    - Configure Python logging module
    - Use appropriate formatters with timestamps
    - Support both console and file logging
    - Never log sensitive information (passwords, tokens)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [x] 11.4 Create utils/wakelock.py with Wakelock class
    - Move wakelock implementation from infrastructure/platform.py
    - Implement as context manager
    - Support all three platforms
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 11.5 Write unit tests for utilities
    - Test MD5 calculation with known values
    - Test compression/decompression if 7zip available
    - Test logging configuration
    - Test wakelock context manager
    - _Requirements: 3.1, 3.3_

## Phase 5: CLI Layer

- [x] 12. Create CLI commands
  - [x] 12.1 Create cli/main.py with Click application
    - Setup Click group for command organization
    - Add global options (--verbose, --config-dir)
    - Initialize logging based on verbosity
    - _Requirements: 1.6, 9.1_
  
  - [x] 12.2 Implement login command
    - Create @cli.command() for login
    - Accept username and password as arguments or prompt
    - Call AuthService.login()
    - Display success or error message
    - _Requirements: 1.6, 1.4_
  
  - [ ]* 12.2.1 Update login command to use browser-based OAuth flow (OPTIONAL - reverted to username/password)
    - Remove username/password arguments from login command
    - Generate OAuth authorization URL using AuthService.get_auth_url()
    - Open user's default browser to GOG login page using webbrowser.open()
    - Display clear instructions for user to login via browser
    - Prompt user to paste the redirect URL after successful login
    - Extract authorization code from pasted URL
    - Call AuthService.login_with_code() to exchange code for tokens
    - Handle errors gracefully (invalid URL, code extraction failure)
    - Display success message with user info
    - _Requirements: 1.5.1, 1.5.2, 1.5.3, 1.5.4, 1.5.5, 1.5.6, 1.5.7, 1.5.8, 1.5.9_
    - _Note: This task was implemented but reverted due to user preference for username/password flow. The OAuth methods remain in AuthService for future use._
  
  - [x] 12.3 Implement update command
    - Create @cli.command() for update
    - Add options for --os, --lang, --ids filters
    - Call GOGAPIService to fetch games
    - Update manifest with new game data
    - Display progress and summary
    - _Requirements: 1.6, 1.1, 1.3_
  
  - [x] 12.4 Implement download command
    - Create @cli.command() for download
    - Add options for save directory, filters, concurrency
    - Call DownloadService to download games
    - Display progress bar for downloads
    - _Requirements: 1.6, 1.2_
  
  - [x] 12.5 Implement backup command
    - Create @cli.command() for backup
    - Copy manifest and token files to backup location
    - Display backup location
    - _Requirements: 1.6_
  
  - [x] 12.6 Implement clean command
    - Create @cli.command() for clean
    - Remove temporary and partial download files
    - Display cleaned files
    - _Requirements: 1.6_
  
  - [x] 12.7 Implement trash command
    - Create @cli.command() for trash
    - Move specified files to trash/recycle bin
    - Use platform-specific trash functionality
    - _Requirements: 1.6, 5.1_
  
  - [x] 12.8 Implement compress command
    - Create @cli.command() for compress
    - Compress game files using 7zip
    - Add options for compression level
    - _Requirements: 1.6, 1.5_
  
  - [x] 12.9 Write integration tests for CLI commands
    - Test each command with Click's CliRunner
    - Mock service layer dependencies
    - Test command options and arguments
    - Test error handling
    - _Requirements: 3.1, 3.3, 3.6_

## Phase 6: API Layer

- [x] 13. Update FastAPI application
  - [x] 13.1 Create api/main.py with FastAPI app
    - Initialize FastAPI application
    - Configure CORS middleware
    - Configure error handling middleware
    - Setup logging for API requests
    - _Requirements: 1.7, 6.6, 9.1_
  
  - [x] 13.2 Create api/schemas.py with Pydantic models
    - Define LoginRequest and LoginResponse models
    - Define UpdateRequest and UpdateResponse models
    - Define DownloadRequest and DownloadResponse models
    - Define ManifestResponse model
    - Define ErrorResponse model
    - Add validation rules to all models
    - _Requirements: 1.7, 10.1, 10.3_
  
  - [x] 13.3 Create api/routes.py with endpoint implementations
    - Setup dependency injection for services
    - Create get_services() dependency function
    - _Requirements: 1.7_
  
  - [x] 13.4 Implement /api/login endpoint
    - Create POST /api/login endpoint
    - Accept LoginRequest body
    - Call AuthService.login()
    - Return LoginResponse with token status
    - Handle authentication errors with 401 status
    - _Requirements: 1.7, 1.4, 6.6_
  
  - [x] 13.5 Implement /api/check-auth endpoint
    - Create GET /api/check-auth endpoint
    - Check AuthService.is_authenticated()
    - Return authentication status
    - _Requirements: 1.7, 1.4_
  
  - [x] 13.6 Implement /api/update endpoint
    - Create POST /api/update endpoint
    - Accept UpdateRequest with filters
    - Call GOGAPIService and ManifestService
    - Return UpdateResponse with updated games count
    - _Requirements: 1.7, 1.1, 1.3_
  
  - [x] 13.7 Implement /api/manifest endpoint
    - Create GET /api/manifest endpoint
    - Return current manifest from ManifestService
    - Support filtering by OS and language
    - _Requirements: 1.7, 1.3_
  
  - [x] 13.8 Implement /api/download endpoint with progress tracking
    - Create POST /api/download endpoint
    - Accept DownloadRequest with game IDs
    - Start download task in background
    - Return task ID for progress tracking
    - _Requirements: 1.7, 1.2, 8.1_
  
  - [x] 13.9 Implement /api/download-progress/{task_id} endpoint
    - Create GET /api/download-progress/{task_id} endpoint
    - Use Server-Sent Events (SSE) for real-time updates
    - Stream progress updates from DownloadService
    - Close stream when download completes
    - _Requirements: 1.7, 8.1, 8.2_
  
  - [x] 13.10 Implement /api/add_without_download endpoint
    - Create POST /api/add_without_download endpoint
    - Add game to manifest without downloading
    - Return success status
    - _Requirements: 1.7, 1.3_
  
  - [x] 13.11 Add error handling middleware
    - Catch all exceptions in middleware
    - Return appropriate HTTP status codes
    - Return ErrorResponse with details
    - Log errors with appropriate severity
    - _Requirements: 6.6, 9.2_
  
  - [x] 13.12 Write API tests
    - Use TestClient from FastAPI
    - Test all endpoints with valid inputs
    - Test error cases (invalid auth, missing games)
    - Test progress streaming
    - _Requirements: 3.1, 3.3, 3.6, 10.4_

## Phase 7: UI Updates

- [x] 14. Update React UI
  - [x] 14.1 Update API client to use new endpoints
    - Update API base URL configuration
    - Update all API calls to use new endpoint paths
    - Update request/response types to match new schemas
    - Add error handling for API calls
    - _Requirements: 1.7, 8.2_
  
  - [x] 14.2 Add real-time progress display using SSE
    - Implement EventSource for /api/download-progress endpoint
    - Update UI with progress events
    - Display download speed and ETA
    - Handle connection errors and reconnection
    - _Requirements: 8.1, 8.6_
  
  - [x] 14.3 Add loading states for all operations
    - Add loading spinners for login
    - Add loading spinners for manifest updates
    - Add loading spinners for downloads
    - Disable buttons during operations
    - _Requirements: 8.3_
  
  - [x] 14.4 Add error boundary for error handling
    - Implement React error boundary component
    - Display user-friendly error messages
    - Add retry buttons for failed operations
    - Log errors to console for debugging
    - _Requirements: 8.2, 6.7_
  
  - [x] 14.5 Add game filtering and search
    - Add search input for game titles
    - Add filters for OS type
    - Add filters for language
    - Add filters for download status
    - Update game list based on filters
    - _Requirements: 8.7_
  
  - [x] 14.6 Add settings persistence (localStorage)
    - Save download directory preference
    - Save compression settings
    - Save filter preferences
    - Save UI theme preference
    - Load settings on app startup
    - _Requirements: 8.5_
  
  - [x] 14.7 Add download size and time estimates
    - Display total download size for selected games
    - Calculate estimated download time based on speed
    - Update estimates in real-time during downloads
    - _Requirements: 8.6_
  
  - [x] 14.8 Improve responsive design
    - Test UI on different screen sizes
    - Use responsive grid layouts
    - Adjust font sizes for mobile
    - Make buttons touch-friendly
    - _Requirements: 8.4_
  
  - [x] 14.9 Add game metadata display
    - Display game cover art (image_url)
    - Display game description
    - Display game changelog
    - Display available downloads and extras
    - Add modal or detail view for game info
    - _Requirements: 8.8_
  
  - [x] 14.10 Write UI component tests
    - Use React Testing Library
    - Test component rendering
    - Test user interactions (clicks, inputs)
    - Test API integration with mocked responses
    - _Requirements: 3.1, 3.3_

## Notes

- Tasks marked with `*` are optional test-related sub-tasks
- Each task references specific requirements for traceability
- Phases 8-12 (Executable Packaging, CI/CD, Testing, Documentation, Release) are out of scope
- Focus on implementing core functionality with proper error handling and logging
- Use Python 3.13+ features throughout (type hints, dataclasses, pathlib, f-strings)
- All services should use dependency injection for testability
- All file operations should use pathlib.Path
- All network operations should include retry logic and timeout handling
