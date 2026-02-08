# GOGRepoc Refactoring Project Requirements

## Overview
Refactor the GOGRepoc project from a monolithic Python 2/3 compatible script into a modern, maintainable Python 3.13+ application with improved architecture, testing, and deployment.

## User Stories

### 1. As a developer, I want a modular codebase
**Description**: Split the monolithic `gogrepoc.py` file into logical modules for better maintainability and testing.

**Acceptance Criteria**:
- 1.1 Core GOG API interactions are in a separate `gog_api` module
- 1.2 File operations (download, verify, import) are in a `file_operations` module
- 1.3 Manifest management is in a `manifest` module
- 1.4 Authentication/session management is in an `auth` module with browser-based OAuth flow
- 1.5 Utility functions (hashing, file system operations) are in a `utils` module
- 1.6 CLI commands are in a `cli` module
- 1.7 Web API endpoints are in an `api` module
- 1.8 Each module has clear responsibilities and minimal coupling
- 1.9 No module exceeds 500 lines of code

### 1.5. As a user, I want browser-based authentication
**Description**: Use browser-based OAuth authentication instead of command-line username/password prompts, supporting all GOG login methods including Google and Discord sign-in.

**Acceptance Criteria**:
- 1.5.1 CLI `login` command opens the user's default browser to GOG's login page
- 1.5.2 User can authenticate using any GOG-supported method (email/password, Google, Discord, etc.)
- 1.5.3 After successful login, user copies the redirect URL from browser
- 1.5.4 CLI extracts the authorization code from the pasted URL
- 1.5.5 CLI exchanges the code for access/refresh tokens automatically
- 1.5.6 Tokens are stored securely for future use
- 1.5.7 No username/password arguments needed in CLI
- 1.5.8 Clear instructions displayed to guide the user through the process
- 1.5.9 Fallback to manual URL entry if browser doesn't open automatically

### 2. As a developer, I want Python 3.13+ only codebase
**Description**: Remove all Python 2 compatibility code and leverage modern Python 3.13+ features.

**Acceptance Criteria**:
- 2.1 All Python 2 compatibility imports are removed (e.g., `Queue`, `urlparse` from old locations)
- 2.2 All Python 2 specific code blocks are removed (e.g., `if sys.version_info[0] < 3`)
- 2.3 Use modern Python 3 features: type hints, pathlib, dataclasses, async/await where appropriate
- 2.4 Use f-strings instead of old string formatting
- 2.5 Use `datetime.fromisoformat()` instead of external dateutil library
- 2.6 Minimum Python version is 3.13
- 2.7 All code passes type checking with mypy
- 2.8 Code follows PEP 8 and modern Python best practices

### 3. As a developer, I want comprehensive test coverage
**Description**: Add unit tests to prevent regressions and ensure code quality.

**Acceptance Criteria**:
- 3.1 Unit tests exist for all core modules (gog_api, file_operations, manifest, auth, utils)
- 3.2 Test coverage is at least 80% for core business logic
- 3.3 Tests use pytest framework
- 3.4 Mock external dependencies (HTTP requests, file system operations)
- 3.5 Tests are organized in a `tests/` directory mirroring the source structure
- 3.6 Integration tests exist for critical workflows (login, update, download)
- 3.7 Tests can be run with a single command (`pytest`)
- 3.8 CI/CD pipeline runs tests automatically

### 4. As a user, I want a single executable application
**Description**: Package the application as a single executable that runs the web server and UI.

**Acceptance Criteria**:
- 4.1 Application can be built into a single executable using PyInstaller or similar
- 4.2 Executable includes the FastAPI backend
- 4.3 Executable includes the React UI (built and bundled)
- 4.4 Executable works on Windows, macOS, and Linux
- 4.5 Executable automatically starts the web server on launch
- 4.6 Executable opens the default browser to the UI on launch
- 4.7 Executable size is reasonable (< 100MB)
- 4.8 No external dependencies required to run the executable
- 4.9 Configuration can be provided via environment variables or config file

### 5. As a user, I want cross-platform compatibility
**Description**: Ensure the application works seamlessly on Windows, macOS, and Linux.

**Acceptance Criteria**:
- 5.1 All file path operations use `pathlib.Path`
- 5.2 Platform-specific code is isolated and clearly marked
- 5.3 Sleep/wake lock functionality works on all three platforms
- 5.4 File system operations handle platform differences (case sensitivity, path separators)
- 5.5 Tests pass on Windows, macOS, and Linux
- 5.6 Documentation includes platform-specific installation notes if needed

### 6. As a developer, I want improved error handling
**Description**: Replace generic exception handling with specific, informative error messages.

**Acceptance Criteria**:
- 6.1 Custom exception classes for different error types (AuthError, NetworkError, FileSystemError)
- 6.2 All exceptions include helpful error messages
- 6.3 Network errors include retry logic with exponential backoff
- 6.4 File system errors include path information
- 6.5 Errors are logged with appropriate severity levels
- 6.6 API endpoints return appropriate HTTP status codes
- 6.7 UI displays user-friendly error messages

### 7. As a developer, I want modern dependency management
**Description**: Use modern Python packaging and dependency management with `uv`.

**Acceptance Criteria**:
- 7.1 Project uses `pyproject.toml` for configuration
- 7.2 Dependencies are managed with `uv` package manager
- 7.3 Development dependencies are separate from runtime dependencies
- 7.4 Dependency versions are pinned for reproducibility
- 7.5 Unused dependencies are removed (e.g., html5lib if not needed, dateutil, pytz)
- 7.6 Optional dependencies are clearly marked
- 7.7 `uv.lock` file is committed for reproducible builds
- 7.8 Installation is fast and reliable with `uv sync`

### 8. As a user, I want improved UI/UX
**Description**: Enhance the React UI with better user experience.

**Acceptance Criteria**:
- 8.1 UI shows download progress in real-time
- 8.2 UI displays clear error messages
- 8.3 UI has loading states for all async operations
- 8.4 UI is responsive and works on different screen sizes
- 8.5 UI persists user preferences (download path, compression settings)
- 8.6 UI shows estimated download time and size
- 8.7 UI allows filtering and searching games
- 8.8 UI shows game metadata (cover art, description)

### 9. As a developer, I want improved logging
**Description**: Implement structured logging with appropriate levels.

**Acceptance Criteria**:
- 9.1 Use Python's `logging` module consistently
- 9.2 Log levels are used appropriately (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 9.3 Logs include timestamps and module names
- 9.4 Logs can be configured via environment variables
- 9.5 Sensitive information (passwords, tokens) is never logged
- 9.6 Log rotation is implemented for long-running processes
- 9.7 Logs are structured (JSON format option)

### 10. As a developer, I want API documentation
**Description**: Provide comprehensive API documentation.

**Acceptance Criteria**:
- 10.1 FastAPI automatic OpenAPI documentation is available
- 10.2 All API endpoints have docstrings
- 10.3 Request/response models are documented
- 10.4 Example requests are provided
- 10.5 Error responses are documented
- 10.6 Authentication requirements are documented

### 11. As a developer, I want automated CI/CD
**Description**: Implement continuous integration and deployment with GitHub Actions.

**Acceptance Criteria**:
- 11.1 Automated tests run on every push and pull request
- 11.2 Tests run on Windows, macOS, and Linux
- 11.3 Code quality checks (linting, type checking) run automatically
- 11.4 Test coverage is tracked and reported
- 11.5 Executables are built automatically on version tags
- 11.6 Built executables are uploaded as GitHub release artifacts
- 11.7 Security checks run on dependencies
- 11.8 Build status badges are displayed in README

## Technical Constraints

- Must maintain backward compatibility with existing manifest files
- Must support the same GOG API endpoints
- Must preserve existing CLI functionality for users who prefer command-line
- Must not require internet connection for verify/import/backup commands
- Must handle large game libraries (1000+ games) efficiently

## Non-Functional Requirements

- **Performance**: Download speeds should not be slower than current implementation
- **Security**: Credentials must be stored securely (encrypted or in system keychain)
- **Reliability**: Application should handle network interruptions gracefully
- **Maintainability**: Code should be easy to understand and modify
- **Testability**: All components should be testable in isolation

## Out of Scope

- GOG movie support (can be added later)
- Multi-user support
- Cloud storage integration
- Automatic game updates/patching
- Game launching functionality

## Success Metrics

- Code coverage > 80%
- All existing functionality preserved
- Executable builds successfully on all platforms
- No Python 2 code remains
- Module count > 5 (from current 1)
- Average module size < 500 lines
- Zero critical security vulnerabilities
- Documentation completeness > 90%
