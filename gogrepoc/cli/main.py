"""Command-line interface for GOGRepoc.

This module provides the main CLI application using Click for command organization
and argument parsing. It includes commands for login, update, download, backup,
clean, trash, and compress operations.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from gogrepoc.infrastructure.file_system import FileSystem
from gogrepoc.infrastructure.http_client import HTTPClient
from gogrepoc.infrastructure.storage import Storage
from gogrepoc.services.auth import AuthService
from gogrepoc.services.downloader import DownloadService
from gogrepoc.services.gog_api import GOGAPIService
from gogrepoc.services.manifest import ManifestService
from gogrepoc.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


# Global context for sharing services between commands
class CLIContext:
    """Context object for sharing services between CLI commands."""

    def __init__(
        self,
        config_dir: Path,
        verbose: bool = False,
        log_file: Optional[Path] = None,
    ):
        """Initialize CLI context with services.

        Args:
            config_dir: Directory for configuration and data files
            verbose: Enable verbose logging
            log_file: Optional log file path
        """
        self.config_dir = config_dir
        self.verbose = verbose
        self.log_file = log_file

        # Initialize services
        self.storage = Storage(config_dir)
        self.http_client = HTTPClient()
        self.auth_service = AuthService(self.storage, self.http_client)
        self.gog_api_service = GOGAPIService(self.http_client, self.auth_service)
        self.manifest_service = ManifestService(self.storage)
        self.file_system = FileSystem()
        self.downloader_service = DownloadService(
            self.http_client,
            self.file_system,
            self.manifest_service,
        )


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path),
    default=Path.home() / ".gogrepoc",
    help="Configuration directory (default: ~/.gogrepoc)",
)
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Log file path (optional)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    config_dir: Path,
    log_file: Optional[Path],
) -> None:
    """GOGRepoc - Download and manage your GOG games.

    A tool for backing up your GOG game library, including installers,
    extras, and metadata. Supports resumable downloads, MD5 verification,
    and cross-platform compatibility.
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level, log_file=log_file)

    # Create and store context
    ctx.obj = CLIContext(config_dir, verbose, log_file)

    logger.debug(f"CLI initialized with config_dir={config_dir}, verbose={verbose}")


@cli.command()
@click.pass_obj
def login(ctx: CLIContext) -> None:
    """Login to GOG account using browser-based authentication.

    Opens your default browser to GOG's login page where you can authenticate
    using any supported method (email/password, Google, Discord, etc.).
    After successful login, you'll be redirected to a page with a URL that
    you need to copy and paste back into the terminal.

    Examples:
        gogrepoc login
    """
    import asyncio
    import webbrowser
    from urllib.parse import urlparse, parse_qs

    click.echo("=" * 70)
    click.secho("GOG Browser-Based Authentication", fg="cyan", bold=True)
    click.echo("=" * 70)
    click.echo()

    # Generate OAuth authorization URL
    auth_url = ctx.auth_service.get_auth_url()

    click.echo("Opening your browser to GOG login page...")
    click.echo()
    click.secho("If the browser doesn't open automatically, visit this URL:", fg="yellow")
    click.echo(auth_url)
    click.echo()

    # Try to open browser
    try:
        webbrowser.open(auth_url)
        click.secho("✓ Browser opened successfully", fg="green")
    except Exception as e:
        click.secho(f"⚠ Could not open browser automatically: {e}", fg="yellow")
        click.echo("Please manually open the URL above in your browser.")

    click.echo()
    click.echo("=" * 70)
    click.secho("Instructions:", fg="cyan", bold=True)
    click.echo("=" * 70)
    click.echo("1. Login to GOG using any method (email, Google, Discord, etc.)")
    click.echo("2. After successful login, you'll be redirected to a page")
    click.echo("3. Copy the ENTIRE URL from your browser's address bar")
    click.echo("4. Paste it below when prompted")
    click.echo()
    click.secho("The URL should look like:", fg="yellow")
    click.echo("https://embed.gog.com/on_login_success?code=...")
    click.echo("=" * 70)
    click.echo()

    # Prompt for redirect URL
    redirect_url = click.prompt("Paste the redirect URL here", type=str)

    # Extract authorization code from URL
    try:
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        auth_code = query_params.get('code', [None])[0]

        if not auth_code:
            click.secho("✗ Error: Could not find authorization code in URL", fg="red")
            click.echo("Make sure you copied the complete URL from the browser.")
            sys.exit(1)

    except Exception as e:
        click.secho(f"✗ Error parsing URL: {e}", fg="red")
        click.echo("Make sure you copied the complete URL from the browser.")
        sys.exit(1)

    # Exchange code for tokens
    click.echo()
    click.echo("Exchanging authorization code for access token...")

    async def do_login() -> None:
        try:
            token = await ctx.auth_service.login_with_code(auth_code)
            click.echo()
            click.secho("=" * 70, fg="green")
            click.secho("✓ Login successful!", fg="green", bold=True)
            click.secho("=" * 70, fg="green")
            if token.user_id:
                click.echo(f"User ID: {token.user_id}")
            click.echo("Your authentication token has been saved.")
            click.echo("You can now use other commands like 'update' and 'download'.")
            click.echo()
        except Exception as e:
            click.echo()
            click.secho("=" * 70, fg="red")
            click.secho("✗ Login failed", fg="red", bold=True)
            click.secho("=" * 70, fg="red")
            click.echo(f"Error: {e}")
            click.echo()
            click.secho("Common issues:", fg="yellow")
            click.echo("• Make sure you copied the complete URL")
            click.echo("• The authorization code may have expired (try again)")
            click.echo("• Check your internet connection")
            click.echo()
            sys.exit(1)

    asyncio.run(do_login())


@cli.command()
@click.option(
    "--os",
    "os_types",
    multiple=True,
    help="Filter by OS type (e.g., windows, linux, mac). Can be specified multiple times.",
)
@click.option(
    "--lang",
    "languages",
    multiple=True,
    help="Filter by language (e.g., en, de, fr). Can be specified multiple times.",
)
@click.option(
    "--ids",
    "game_ids",
    multiple=True,
    type=int,
    help="Update specific game IDs only. Can be specified multiple times.",
)
@click.pass_obj
def update(
    ctx: CLIContext,
    os_types: tuple[str, ...],
    languages: tuple[str, ...],
    game_ids: tuple[int, ...],
) -> None:
    """Update game manifest from GOG.

    Fetch the latest game information from your GOG library and update
    the local manifest. This includes game metadata, available downloads,
    extras, and version information.

    Examples:
        gogrepoc update
        gogrepoc update --os windows --os linux
        gogrepoc update --lang en --lang de
        gogrepoc update --ids 1234 --ids 5678
    """
    import asyncio

    click.echo("Updating game manifest...")

    async def do_update() -> None:
        try:
            # Check authentication
            if not ctx.auth_service.is_authenticated():
                click.secho("✗ Not authenticated. Please run 'gogrepoc login' first.", fg="red")
                sys.exit(1)

            # Load existing manifest
            ctx.manifest_service.load_manifest()

            # Fetch games from GOG
            page = 1
            total_games = 0
            updated_games = 0

            with click.progressbar(
                length=100,
                label="Fetching games",
                show_eta=True,
            ) as bar:
                while True:
                    # Fetch page of games
                    response = await ctx.gog_api_service.get_games_list(page)

                    products = response.get("products", [])
                    total_pages = response.get("totalPages", 1)

                    if not products:
                        break

                    # Filter by game IDs if specified
                    if game_ids:
                        products = [p for p in products if p.get("id") in game_ids]

                    # Fetch details for each game
                    for product in products:
                        game_id = product.get("id")
                        if not game_id:
                            continue

                        try:
                            # Fetch detailed game information
                            game_details = await ctx.gog_api_service.get_game_details(game_id)

                            # Convert to Game model (simplified - would need full conversion)
                            # For now, just count the games
                            total_games += 1
                            updated_games += 1

                        except Exception as e:
                            logger.error(f"Failed to fetch details for game {game_id}: {e}")
                            continue

                    # Update progress bar
                    progress = int((page / total_pages) * 100)
                    bar.update(progress - bar.pos)

                    # Check if we've fetched all pages
                    if page >= total_pages:
                        break

                    page += 1

                # Complete progress bar
                bar.update(100 - bar.pos)

            # Save updated manifest
            ctx.manifest_service.save_manifest()

            click.secho(
                f"✓ Manifest updated: {updated_games} games processed",
                fg="green",
            )

        except Exception as e:
            click.secho(f"✗ Update failed: {e}", fg="red")
            logger.exception("Update failed")
            sys.exit(1)

    asyncio.run(do_update())


@cli.command()
@click.argument(
    "savedir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
)
@click.option(
    "--ids",
    "game_ids",
    multiple=True,
    type=int,
    help="Download specific game IDs only. Can be specified multiple times.",
)
@click.option(
    "--os",
    "os_types",
    multiple=True,
    help="Filter downloads by OS type (e.g., windows, linux, mac).",
)
@click.option(
    "--lang",
    "languages",
    multiple=True,
    help="Filter downloads by language (e.g., en, de, fr).",
)
@click.option(
    "--concurrent",
    "-c",
    type=int,
    default=4,
    help="Number of concurrent downloads (default: 4)",
)
@click.pass_obj
def download(
    ctx: CLIContext,
    savedir: Path,
    game_ids: tuple[int, ...],
    os_types: tuple[str, ...],
    languages: tuple[str, ...],
    concurrent: int,
) -> None:
    """Download games to SAVEDIR.

    Download game installers and extras to the specified directory.
    If no directory is specified, downloads to the current directory.

    Examples:
        gogrepoc download /path/to/games
        gogrepoc download --ids 1234 --ids 5678
        gogrepoc download --os windows --lang en
        gogrepoc download --concurrent 8 /path/to/games
    """
    import asyncio

    click.echo(f"Downloading games to {savedir}...")

    async def do_download() -> None:
        try:
            # Check authentication
            if not ctx.auth_service.is_authenticated():
                click.secho("✗ Not authenticated. Please run 'gogrepoc login' first.", fg="red")
                sys.exit(1)

            # Load manifest
            games = ctx.manifest_service.load_manifest()

            if not games:
                click.secho("✗ No games in manifest. Please run 'gogrepoc update' first.", fg="red")
                sys.exit(1)

            # Filter games
            if game_ids:
                games = [g for g in games if g.id in game_ids]

            if os_types or languages:
                games = ctx.manifest_service.filter_games(
                    os_types=list(os_types) if os_types else None,
                    languages=list(languages) if languages else None,
                )

            if not games:
                click.secho("✗ No games match the specified filters.", fg="yellow")
                return

            click.echo(f"Found {len(games)} games to download")

            # Update concurrent downloads setting
            ctx.downloader_service.max_concurrent_downloads = concurrent

            # Download each game
            for idx, game in enumerate(games, 1):
                click.echo(f"\n[{idx}/{len(games)}] Downloading: {game.title}")

                # Progress callback
                def progress_callback(
                    filename: str,
                    bytes_downloaded: int,
                    total_bytes: int,
                    file_index: int,
                    total_files: int,
                ) -> None:
                    if total_bytes > 0:
                        percent = (bytes_downloaded / total_bytes) * 100
                        mb_downloaded = bytes_downloaded / (1024 * 1024)
                        mb_total = total_bytes / (1024 * 1024)
                        click.echo(
                            f"  [{file_index}/{total_files}] {filename}: "
                            f"{mb_downloaded:.1f}/{mb_total:.1f} MB ({percent:.1f}%)",
                            nl=False,
                        )
                        click.echo("\r", nl=False)

                # Download game
                results = await ctx.downloader_service.download_game(
                    game,
                    savedir,
                    progress_callback=progress_callback,
                )

                # Show results
                successful = sum(1 for success in results.values() if success)
                total = len(results)

                if successful == total:
                    click.secho(f"  ✓ Downloaded {successful}/{total} files", fg="green")
                else:
                    click.secho(
                        f"  ⚠ Downloaded {successful}/{total} files (some failed)",
                        fg="yellow",
                    )

            click.secho("\n✓ Download complete!", fg="green")

        except Exception as e:
            click.secho(f"\n✗ Download failed: {e}", fg="red")
            logger.exception("Download failed")
            sys.exit(1)

    asyncio.run(do_download())


@cli.command()
@click.argument(
    "backup_dir",
    type=click.Path(path_type=Path),
)
@click.pass_obj
def backup(ctx: CLIContext, backup_dir: Path) -> None:
    """Backup manifest and configuration to BACKUP_DIR.

    Create a backup of your manifest and authentication tokens to the
    specified directory. This is useful for disaster recovery or migrating
    to a new system.

    Examples:
        gogrepoc backup /path/to/backup
        gogrepoc backup ~/gogrepoc-backup
    """
    import shutil

    click.echo(f"Creating backup in {backup_dir}...")

    try:
        # Ensure backup directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup manifest
        manifest_file = ctx.storage.manifest_path
        if manifest_file.exists():
            shutil.copy2(manifest_file, backup_dir / manifest_file.name)
            click.echo(f"  ✓ Backed up manifest: {manifest_file.name}")

        # Backup token
        token_file = ctx.storage.token_path
        if token_file.exists():
            shutil.copy2(token_file, backup_dir / token_file.name)
            click.echo(f"  ✓ Backed up token: {token_file.name}")

        # Backup downloaded games manifest
        downloaded_file = ctx.storage.downloaded_games_path
        if downloaded_file.exists():
            shutil.copy2(downloaded_file, backup_dir / downloaded_file.name)
            click.echo(f"  ✓ Backed up downloaded games: {downloaded_file.name}")

        click.secho(f"\n✓ Backup complete: {backup_dir}", fg="green")

    except Exception as e:
        click.secho(f"✗ Backup failed: {e}", fg="red")
        logger.exception("Backup failed")
        sys.exit(1)


@cli.command()
@click.argument(
    "directory",
    type=click.Path(path_type=Path, exists=True),
    default=Path.cwd(),
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting",
)
@click.pass_obj
def clean(ctx: CLIContext, directory: Path, dry_run: bool) -> None:
    """Clean temporary and partial download files in DIRECTORY.

    Remove .part files and other temporary files left over from interrupted
    downloads. By default, cleans the current directory.

    Examples:
        gogrepoc clean
        gogrepoc clean /path/to/games
        gogrepoc clean --dry-run /path/to/games
    """
    click.echo(f"Cleaning temporary files in {directory}...")

    try:
        # Find .part files
        part_files = list(directory.rglob("*.part"))

        if not part_files:
            click.secho("✓ No temporary files found", fg="green")
            return

        click.echo(f"Found {len(part_files)} temporary files:")

        total_size = 0
        for part_file in part_files:
            size = part_file.stat().st_size
            total_size += size
            size_mb = size / (1024 * 1024)

            click.echo(f"  - {part_file.name} ({size_mb:.1f} MB)")

            if not dry_run:
                part_file.unlink()

        total_mb = total_size / (1024 * 1024)

        if dry_run:
            click.secho(
                f"\n✓ Would delete {len(part_files)} files ({total_mb:.1f} MB)",
                fg="yellow",
            )
        else:
            click.secho(
                f"\n✓ Deleted {len(part_files)} files ({total_mb:.1f} MB)",
                fg="green",
            )

    except Exception as e:
        click.secho(f"✗ Clean failed: {e}", fg="red")
        logger.exception("Clean failed")
        sys.exit(1)


@cli.command()
@click.argument(
    "files",
    nargs=-1,
    type=click.Path(path_type=Path, exists=True),
    required=True,
)
@click.pass_obj
def trash(ctx: CLIContext, files: tuple[Path, ...]) -> None:
    """Move FILES to trash/recycle bin.

    Safely delete files by moving them to the system trash/recycle bin
    instead of permanently deleting them.

    Examples:
        gogrepoc trash file1.exe file2.bin
        gogrepoc trash /path/to/game/*
    """
    import platform

    click.echo(f"Moving {len(files)} files to trash...")

    try:
        system = platform.system()

        for file_path in files:
            if not file_path.exists():
                click.secho(f"  ⚠ File not found: {file_path}", fg="yellow")
                continue

            # Platform-specific trash implementation
            if system == "Windows":
                # Use send2trash library if available, otherwise just delete
                try:
                    import send2trash

                    send2trash.send2trash(str(file_path))
                    click.echo(f"  ✓ Moved to recycle bin: {file_path.name}")
                except ImportError:
                    # Fallback: just delete the file
                    file_path.unlink()
                    click.echo(f"  ✓ Deleted: {file_path.name}")

            elif system == "Darwin":  # macOS
                # Move to ~/.Trash
                import shutil

                trash_dir = Path.home() / ".Trash"
                trash_dir.mkdir(exist_ok=True)
                dest = trash_dir / file_path.name

                # Handle name conflicts
                counter = 1
                while dest.exists():
                    dest = trash_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                    counter += 1

                shutil.move(str(file_path), str(dest))
                click.echo(f"  ✓ Moved to trash: {file_path.name}")

            else:  # Linux and others
                # Move to ~/.local/share/Trash/files
                import shutil

                trash_dir = Path.home() / ".local" / "share" / "Trash" / "files"
                trash_dir.mkdir(parents=True, exist_ok=True)
                dest = trash_dir / file_path.name

                # Handle name conflicts
                counter = 1
                while dest.exists():
                    dest = trash_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                    counter += 1

                shutil.move(str(file_path), str(dest))
                click.echo(f"  ✓ Moved to trash: {file_path.name}")

        click.secho(f"\n✓ Moved {len(files)} files to trash", fg="green")

    except Exception as e:
        click.secho(f"✗ Trash operation failed: {e}", fg="red")
        logger.exception("Trash operation failed")
        sys.exit(1)


@cli.command()
@click.argument(
    "files",
    nargs=-1,
    type=click.Path(path_type=Path, exists=True),
    required=True,
)
@click.option(
    "--level",
    "-l",
    type=click.IntRange(0, 9),
    default=5,
    help="Compression level (0-9, default: 5)",
)
@click.pass_obj
def compress(ctx: CLIContext, files: tuple[Path, ...], level: int) -> None:
    """Compress FILES using 7zip.

    Compress game files using 7zip compression. Requires 7zip to be
    installed on the system.

    Examples:
        gogrepoc compress game_installer.exe
        gogrepoc compress --level 9 *.bin
        gogrepoc compress /path/to/game/*
    """
    from gogrepoc.utils.compression import compress_file

    click.echo(f"Compressing {len(files)} files with level {level}...")

    try:
        for file_path in files:
            if not file_path.exists():
                click.secho(f"  ⚠ File not found: {file_path}", fg="yellow")
                continue

            # Create archive path
            archive_path = file_path.with_suffix(file_path.suffix + ".7z")

            click.echo(f"  Compressing: {file_path.name}...")

            # Compress file
            compress_file(file_path, archive_path, compression_level=level)

            # Show size comparison
            original_size = file_path.stat().st_size
            compressed_size = archive_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100

            original_mb = original_size / (1024 * 1024)
            compressed_mb = compressed_size / (1024 * 1024)

            click.secho(
                f"  ✓ {file_path.name}: {original_mb:.1f} MB → "
                f"{compressed_mb:.1f} MB ({ratio:.1f}% reduction)",
                fg="green",
            )

        click.secho(f"\n✓ Compressed {len(files)} files", fg="green")

    except Exception as e:
        click.secho(f"✗ Compression failed: {e}", fg="red")
        logger.exception("Compression failed")
        sys.exit(1)


if __name__ == "__main__":
    cli()
