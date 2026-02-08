# GOGRepoc Backend

This directory contains the entry point script for the PyInstaller-bundled Python backend used in the Electron desktop application.

## Files

- `main.py` - Entry point script with CLI argument parsing and uvicorn server startup
- `gogrepoc.spec` - PyInstaller specification file (to be created)
- `dist/` - Output directory for PyInstaller builds (generated)

## Usage

### Development Mode

Run the backend directly with Python:

```bash
python backend/main.py
```

With custom host and port:

```bash
python backend/main.py --host 127.0.0.1 --port 9000
```

### Production Mode

The backend will be bundled into a standalone executable using PyInstaller. The Electron main process will spawn this executable with the appropriate port argument.

## Command-Line Arguments

- `--host` - Host to bind the server to (default: 127.0.0.1)
- `--port` - Port to bind the server to (default: 8000)

## Logging

The backend outputs logs to stdout/stderr, which are captured by the Electron main process for centralized logging. Access logging is disabled to reduce noise in the Electron logs.

## Requirements

- Python 3.13+
- uvicorn
- fastapi
- All gogrepoc dependencies

## Testing

Unit tests for the backend entry point are located in `tests/unit/test_backend_main.py`.

Run tests with:

```bash
pytest tests/unit/test_backend_main.py -v
```
