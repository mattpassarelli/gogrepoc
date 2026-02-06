"""API routes for GOGRepoc web interface.

This module provides all REST API endpoints for the GOGRepoc application,
including authentication, manifest management, and download operations.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from gogrepoc.api.schemas import (
    AddWithoutDownloadRequest,
    AddWithoutDownloadResponse,
    AuthStatusResponse,
    DownloadProgress,
    DownloadRequest,
    DownloadResponse,
    LoginRequest,
    LoginResponse,
    ManifestResponse,
    UpdateRequest,
    UpdateResponse,
    GameSchema,
    DownloadSchema,
    ExtraSchema,
)
from gogrepoc.core.exceptions import AuthError, FileSystemError, NetworkError
from gogrepoc.core.models import Game, Download, Extra
from gogrepoc.infrastructure.file_system import FileSystem
from gogrepoc.infrastructure.http_client import HTTPClient
from gogrepoc.infrastructure.storage import Storage
from gogrepoc.services.auth import AuthService
from gogrepoc.services.downloader import DownloadService
from gogrepoc.services.gog_api import GOGAPIService
from gogrepoc.services.manifest import ManifestService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Global storage for download tasks
download_tasks: dict[str, dict[str, Any]] = {}


# Dependency injection
def get_storage() -> Storage:
    """Get Storage instance."""
    return Storage()


def get_http_client() -> HTTPClient:
    """Get HTTPClient instance."""
    return HTTPClient()


def get_auth_service(
    storage: Storage = Depends(get_storage),
    http_client: HTTPClient = Depends(get_http_client),
) -> AuthService:
    """Get AuthService instance."""
    return AuthService(storage, http_client)


def get_manifest_service(storage: Storage = Depends(get_storage)) -> ManifestService:
    """Get ManifestService instance."""
    service = ManifestService(storage)
    # Load manifest on first access
    try:
        service.load_manifest()
    except Exception as e:
        logger.warning(f"Failed to load manifest: {e}")
    return service


def get_gog_api_service(
    http_client: HTTPClient = Depends(get_http_client),
    auth_service: AuthService = Depends(get_auth_service),
) -> GOGAPIService:
    """Get GOGAPIService instance."""
    return GOGAPIService(http_client, auth_service)


def get_file_system() -> FileSystem:
    """Get FileSystem instance."""
    return FileSystem()


def get_download_service(
    http_client: HTTPClient = Depends(get_http_client),
    file_system: FileSystem = Depends(get_file_system),
    manifest_service: ManifestService = Depends(get_manifest_service),
) -> DownloadService:
    """Get DownloadService instance."""
    return DownloadService(http_client, file_system, manifest_service)


# Helper functions
def game_to_schema(game: Game) -> GameSchema:
    """Convert Game model to GameSchema."""
    return GameSchema(
        id=game.id,
        title=game.title,
        folder_name=game.folder_name,
        long_title=game.long_title,
        downloads=[download_to_schema(d) for d in game.downloads],
        galaxy_downloads=[download_to_schema(d) for d in game.galaxy_downloads],
        shared_downloads=[download_to_schema(d) for d in game.shared_downloads],
        extras=[extra_to_schema(e) for e in game.extras],
        serials=game.serials,
        changelog=game.changelog,
        image_url=game.image_url,
        bg_url=game.bg_url,
        store_url=game.store_url,
        has_updates=game.has_updates,
    )


def download_to_schema(download: Download) -> DownloadSchema:
    """Convert Download model to DownloadSchema."""
    return DownloadSchema(
        name=download.name,
        href=download.href,
        size=download.size,
        md5=download.md5,
        os_type=download.os_type,
        lang=download.lang,
        version=download.version,
        desc=download.desc,
        updated=download.updated,
        verified=download.verified,
    )


def extra_to_schema(extra: Extra) -> ExtraSchema:
    """Convert Extra model to ExtraSchema."""
    return ExtraSchema(
        name=extra.name,
        href=extra.href,
        size=extra.size,
        desc=extra.desc,
        updated=extra.updated,
    )


# Authentication endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate with GOG.

    Accepts user credentials and attempts to authenticate with GOG API.
    Returns authentication status and stores token on success.

    Args:
        request: Login credentials (username, password, optional 2FA code)
        auth_service: Authentication service dependency

    Returns:
        LoginResponse with success status and message

    Raises:
        HTTPException: 401 if authentication fails
    """
    logger.info(f"Login attempt for user: {request.username}")

    try:
        await auth_service.login(
            request.username,
            request.password,
            two_factor_code=request.two_factor_code,
        )

        return LoginResponse(
            success=True,
            message="Login successful",
            authenticated=True,
        )

    except AuthError as e:
        logger.warning(f"Login failed for {request.username}: {e}")
        
        # Check if 2FA is required
        if auth_service.requires_two_factor(str(e)):
            return LoginResponse(
                success=False,
                message="Two-factor authentication required",
                authenticated=False,
            )
        
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/check-auth", response_model=AuthStatusResponse)
async def check_auth(
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthStatusResponse:
    """Check authentication status.

    Returns whether the user is currently authenticated with a valid token.

    Args:
        auth_service: Authentication service dependency

    Returns:
        AuthStatusResponse with authentication status
    """
    authenticated = auth_service.is_authenticated()
    
    user_id = None
    if authenticated:
        try:
            token = await auth_service.get_valid_token()
            user_id = token.user_id
        except AuthError:
            authenticated = False

    return AuthStatusResponse(
        authenticated=authenticated,
        user_id=user_id,
    )


# Manifest endpoints
@router.get("/manifest", response_model=ManifestResponse)
async def get_manifest(
    os_types: Optional[list[str]] = Query(None),
    languages: Optional[list[str]] = Query(None),
    manifest_service: ManifestService = Depends(get_manifest_service),
) -> ManifestResponse:
    """Get current game manifest.

    Returns the list of games in the manifest, optionally filtered by
    OS type and language.

    Args:
        os_types: Optional list of OS types to filter (e.g., ['windows', 'linux'])
        languages: Optional list of languages to filter (e.g., ['en', 'de'])
        manifest_service: Manifest service dependency

    Returns:
        ManifestResponse with list of games
    """
    logger.info(f"Fetching manifest (OS: {os_types}, Languages: {languages})")

    # Get games, applying filters if specified
    if os_types or languages:
        games = manifest_service.filter_games(os_types=os_types, languages=languages)
    else:
        games = manifest_service.get_all_games()

    # Convert to schemas
    game_schemas = [game_to_schema(game) for game in games]

    return ManifestResponse(
        games=game_schemas,
        total_count=len(game_schemas),
    )


# Update endpoint
@router.post("/update", response_model=UpdateResponse)
async def update_manifest(
    request: UpdateRequest,
    gog_api_service: GOGAPIService = Depends(get_gog_api_service),
    manifest_service: ManifestService = Depends(get_manifest_service),
) -> UpdateResponse:
    """Update game manifest from GOG API.

    Fetches the latest game information from GOG and updates the local manifest.
    Can update all games or specific games by ID.

    Args:
        request: Update request with filters
        gog_api_service: GOG API service dependency
        manifest_service: Manifest service dependency

    Returns:
        UpdateResponse with update statistics

    Raises:
        HTTPException: 401 if not authenticated, 503 if GOG API is unavailable
    """
    logger.info(f"Starting manifest update (game_ids: {request.game_ids})")

    games_updated = 0
    games_added = 0

    try:
        # If specific game IDs requested, update only those
        if request.game_ids:
            for game_id in request.game_ids:
                try:
                    # Fetch game details from GOG
                    game_data = await gog_api_service.get_game_details(game_id)
                    
                    # Parse game data into Game object
                    # This is a simplified version - actual implementation would need
                    # to parse all the game data properly
                    game = _parse_game_data(game_data)
                    
                    # Check if game exists in manifest
                    existing_game = manifest_service.get_game_by_id(game_id)
                    if existing_game:
                        games_updated += 1
                    else:
                        games_added += 1
                    
                    # Update manifest
                    manifest_service.update_game(game)
                    
                except Exception as e:
                    logger.error(f"Failed to update game {game_id}: {e}")
                    # Continue with other games
                    continue
        else:
            # Update all games
            page = 1
            while True:
                try:
                    # Fetch games list page
                    games_data = await gog_api_service.get_games_list(page)
                    
                    products = games_data.get("products", [])
                    if not products:
                        break
                    
                    # Update each game
                    for product in products:
                        game_id = product.get("id")
                        if not game_id:
                            continue
                        
                        try:
                            # Fetch detailed game info
                            game_data = await gog_api_service.get_game_details(game_id)
                            game = _parse_game_data(game_data)
                            
                            # Check if game exists
                            existing_game = manifest_service.get_game_by_id(game_id)
                            if existing_game:
                                games_updated += 1
                            else:
                                games_added += 1
                            
                            manifest_service.update_game(game)
                            
                        except Exception as e:
                            logger.error(f"Failed to update game {game_id}: {e}")
                            continue
                    
                    # Check if there are more pages
                    total_pages = games_data.get("totalPages", 1)
                    if page >= total_pages:
                        break
                    
                    page += 1
                    
                except Exception as e:
                    logger.error(f"Failed to fetch games list page {page}: {e}")
                    break
        
        # Save updated manifest
        manifest_service.save_manifest()
        
        logger.info(
            f"Manifest update complete: {games_updated} updated, {games_added} added"
        )
        
        return UpdateResponse(
            success=True,
            message=f"Updated {games_updated} games, added {games_added} new games",
            games_updated=games_updated,
            games_added=games_added,
        )
        
    except AuthError as e:
        logger.error(f"Authentication error during update: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except NetworkError as e:
        logger.error(f"Network error during update: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_game_data(game_data: dict) -> Game:
    """Parse GOG API game data into Game model.
    
    This is a placeholder implementation. The actual implementation would need
    to properly parse all fields from the GOG API response.
    """
    # TODO: Implement proper game data parsing
    # This is a simplified version for now
    game_id = game_data.get("id", 0)
    title = game_data.get("title", "Unknown")
    
    return Game(
        id=game_id,
        title=title,
        folder_name=title.replace(" ", "_").lower(),
        long_title=title,
        downloads=[],
        galaxy_downloads=[],
        shared_downloads=[],
        extras=[],
        serials={},
        changelog=game_data.get("changelog"),
        image_url=game_data.get("image", ""),
        bg_url=game_data.get("backgroundImage", ""),
        store_url=f"https://www.gog.com/game/{title.lower().replace(' ', '_')}",
        has_updates=False,
    )


# Download endpoints
@router.post("/download", response_model=DownloadResponse)
async def start_download(
    request: DownloadRequest,
    manifest_service: ManifestService = Depends(get_manifest_service),
    download_service: DownloadService = Depends(get_download_service),
) -> DownloadResponse:
    """Start downloading games.

    Initiates a background download task for the specified games.
    Returns a task ID that can be used to track progress.

    Args:
        request: Download request with game IDs and options
        manifest_service: Manifest service dependency
        download_service: Download service dependency

    Returns:
        DownloadResponse with task ID for progress tracking

    Raises:
        HTTPException: 404 if games not found, 400 if invalid request
    """
    logger.info(f"Starting download for games: {request.game_ids}")

    # Validate games exist in manifest
    games_to_download = []
    for game_id in request.game_ids:
        game = manifest_service.get_game_by_id(game_id)
        if not game:
            raise HTTPException(
                status_code=404,
                detail=f"Game not found in manifest: {game_id}",
            )
        games_to_download.append(game)

    # Validate save directory
    save_dir = Path(request.save_dir)
    if not save_dir.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="Save directory must be an absolute path",
        )

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Initialize task state
    download_tasks[task_id] = {
        "status": "running",
        "current_game": None,
        "current_file": None,
        "bytes_downloaded": 0,
        "bytes_total": 0,
        "progress_percent": 0.0,
        "download_speed": 0.0,
        "eta_seconds": None,
        "error": None,
    }

    # Start download task in background
    asyncio.create_task(
        _download_task(
            task_id,
            games_to_download,
            save_dir,
            download_service,
        )
    )

    return DownloadResponse(
        success=True,
        message=f"Download started for {len(games_to_download)} games",
        task_id=task_id,
    )


async def _download_task(
    task_id: str,
    games: list[Game],
    save_dir: Path,
    download_service: DownloadService,
) -> None:
    """Background task for downloading games.

    Args:
        task_id: Task ID for tracking
        games: List of games to download
        save_dir: Directory to save downloads
        download_service: Download service instance
    """
    try:
        for game in games:
            # Update task state
            download_tasks[task_id]["current_game"] = game.title

            # Download game
            def progress_callback(
                filename: str,
                bytes_downloaded: int,
                total_bytes: int,
                file_index: int,
                total_files: int,
            ) -> None:
                """Update progress for current download."""
                download_tasks[task_id]["current_file"] = filename
                download_tasks[task_id]["bytes_downloaded"] = bytes_downloaded
                download_tasks[task_id]["bytes_total"] = total_bytes
                
                if total_bytes > 0:
                    progress = (bytes_downloaded / total_bytes) * 100
                    download_tasks[task_id]["progress_percent"] = progress

            await download_service.download_game(
                game,
                save_dir,
                progress_callback=progress_callback,
            )

        # Mark as completed
        download_tasks[task_id]["status"] = "completed"
        download_tasks[task_id]["progress_percent"] = 100.0
        logger.info(f"Download task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Download task {task_id} failed: {e}")
        download_tasks[task_id]["status"] = "failed"
        download_tasks[task_id]["error"] = str(e)


@router.get("/download-progress/{task_id}")
async def get_download_progress(task_id: str) -> StreamingResponse:
    """Get download progress via Server-Sent Events.

    Streams real-time progress updates for a download task.

    Args:
        task_id: Task ID from start_download

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: 404 if task not found
    """
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Download task not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for download progress."""
        while True:
            if task_id not in download_tasks:
                break

            task_state = download_tasks[task_id]
            
            # Create progress object
            progress = DownloadProgress(
                task_id=task_id,
                status=task_state["status"],
                current_game=task_state["current_game"],
                current_file=task_state["current_file"],
                bytes_downloaded=task_state["bytes_downloaded"],
                bytes_total=task_state["bytes_total"],
                progress_percent=task_state["progress_percent"],
                download_speed=task_state["download_speed"],
                eta_seconds=task_state["eta_seconds"],
                error=task_state["error"],
            )

            # Send SSE event
            yield f"data: {progress.model_dump_json()}\n\n"

            # Stop streaming if task is completed or failed
            if task_state["status"] in ["completed", "failed"]:
                break

            # Wait before next update
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# Add without download endpoint
@router.post("/add_without_download", response_model=AddWithoutDownloadResponse)
async def add_without_download(
    request: AddWithoutDownloadRequest,
    gog_api_service: GOGAPIService = Depends(get_gog_api_service),
    manifest_service: ManifestService = Depends(get_manifest_service),
) -> AddWithoutDownloadResponse:
    """Add games to manifest without downloading.

    Fetches game information from GOG and adds to manifest without
    downloading any files.

    Args:
        request: Request with game IDs to add
        gog_api_service: GOG API service dependency
        manifest_service: Manifest service dependency

    Returns:
        AddWithoutDownloadResponse with number of games added

    Raises:
        HTTPException: 401 if not authenticated, 503 if GOG API unavailable
    """
    logger.info(f"Adding games without download: {request.game_ids}")

    games_added = 0

    try:
        for game_id in request.game_ids:
            try:
                # Fetch game details
                game_data = await gog_api_service.get_game_details(game_id)
                game = _parse_game_data(game_data)
                
                # Add to manifest
                manifest_service.update_game(game)
                games_added += 1
                
            except Exception as e:
                logger.error(f"Failed to add game {game_id}: {e}")
                continue

        # Save manifest
        manifest_service.save_manifest()

        return AddWithoutDownloadResponse(
            success=True,
            message=f"Added {games_added} games to manifest",
            games_added=games_added,
        )

    except AuthError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except NetworkError as e:
        logger.error(f"Network error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
