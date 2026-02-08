"""Backend entry point for Electron desktop application.

This module provides the CLI entry point for the PyInstaller-bundled
FastAPI backend. It handles command-line argument parsing and server
startup with configurable host and port settings.
"""

import argparse
import logging
import sys

import uvicorn

from gogrepoc.api.main import app


def setup_logging() -> None:
    """Configure logging for Electron integration.
    
    Sets up logging to output to stdout/stderr which will be captured
    by the Electron main process for centralized logging.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed command-line arguments with host and port settings.
    """
    parser = argparse.ArgumentParser(
        description="GOGRepoc Backend Server for Electron Desktop Application"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)"
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the backend server.
    
    Parses command-line arguments, configures logging, and starts
    the uvicorn server with the FastAPI application.
    """
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Parse command-line arguments
    args = parse_args()
    
    logger.info(f"Starting GOGRepoc backend server on {args.host}:{args.port}")
    
    # Run uvicorn server
    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=False,  # Reduce noise in Electron logs
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
