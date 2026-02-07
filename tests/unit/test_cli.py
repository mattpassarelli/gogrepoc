"""Unit tests for CLI commands.

Tests the Click-based CLI application using CliRunner to simulate
command execution without actually running the commands.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from gogrepoc.cli.main import cli
from gogrepoc.core.models import Token, Game, Download
from datetime import datetime, timedelta


@pytest.fixture
def runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_services():
    """Create mock services for CLI testing."""
    with patch("gogrepoc.cli.main.Storage") as mock_storage, \
         patch("gogrepoc.cli.main.HTTPClient") as mock_http, \
         patch("gogrepoc.cli.main.AuthService") as mock_auth, \
         patch("gogrepoc.cli.main.GOGAPIService") as mock_gog_api, \
         patch("gogrepoc.cli.main.ManifestService") as mock_manifest, \
         patch("gogrepoc.cli.main.FileSystem") as mock_fs, \
         patch("gogrepoc.cli.main.DownloadService") as mock_downloader:
        
        # Configure mock instances
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        
        mock_http_instance = MagicMock()
        mock_http.return_value = mock_http_instance
        
        mock_auth_instance = MagicMock()
        mock_auth_instance.login = AsyncMock()
        mock_auth_instance.is_authenticated = MagicMock(return_value=True)
        mock_auth.return_value = mock_auth_instance
        
        mock_gog_api_instance = MagicMock()
        mock_gog_api_instance.get_games_list = AsyncMock()
        mock_gog_api_instance.get_game_details = AsyncMock()
        mock_gog_api.return_value = mock_gog_api_instance
        
        mock_manifest_instance = MagicMock()
        mock_manifest_instance.load_manifest = MagicMock(return_value=[])
        mock_manifest_instance.save_manifest = MagicMock()
        mock_manifest_instance.filter_games = MagicMock(return_value=[])
        mock_manifest.return_value = mock_manifest_instance
        
        mock_fs_instance = MagicMock()
        mock_fs.return_value = mock_fs_instance
        
        mock_downloader_instance = MagicMock()
        mock_downloader_instance.download_game = AsyncMock(return_value={})
        mock_downloader.return_value = mock_downloader_instance
        
        yield {
            "storage": mock_storage_instance,
            "http_client": mock_http_instance,
            "auth_service": mock_auth_instance,
            "gog_api_service": mock_gog_api_instance,
            "manifest_service": mock_manifest_instance,
            "file_system": mock_fs_instance,
            "downloader_service": mock_downloader_instance,
        }


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self, runner):
        """Test that CLI help message is displayed."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "GOGRepoc" in result.output
        assert "Download and manage your GOG games" in result.output

    def test_cli_version_option(self, runner):
        """Test CLI with verbose option."""
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_cli_config_dir_option(self, runner):
        """Test CLI with custom config directory."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["--config-dir", "/tmp/test", "--help"])
            assert result.exit_code == 0


class TestLoginCommand:
    """Test login command."""

    def test_login_with_credentials(self, runner, mock_services):
        """Test login command with username and password."""
        mock_services["auth_service"].login = AsyncMock(return_value=Token(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_at=datetime.now() + timedelta(hours=1),
            user_id="12345",
        ))

        result = runner.invoke(
            cli,
            ["login", "test@example.com", "password"],
        )

        assert result.exit_code == 0
        assert "Login successful" in result.output
        mock_services["auth_service"].login.assert_called_once()

    def test_login_prompts_for_credentials(self, runner, mock_services):
        """Test login command prompts for credentials when not provided."""
        mock_services["auth_service"].login = AsyncMock(return_value=Token(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_at=datetime.now() + timedelta(hours=1),
            user_id="12345",
        ))

        result = runner.invoke(
            cli,
            ["login"],
            input="test@example.com\npassword\n",
        )

        assert result.exit_code == 0
        assert "GOG username/email" in result.output
        assert "GOG password" in result.output

    def test_login_with_two_factor(self, runner, mock_services):
        """Test login command with two-factor authentication."""
        mock_services["auth_service"].login = AsyncMock(return_value=Token(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_at=datetime.now() + timedelta(hours=1),
            user_id="12345",
        ))

        result = runner.invoke(
            cli,
            ["login", "test@example.com", "password", "--two-factor", "123456"],
        )

        assert result.exit_code == 0
        assert "Login successful" in result.output

    def test_login_failure(self, runner, mock_services):
        """Test login command with authentication failure."""
        mock_services["auth_service"].login = AsyncMock(side_effect=Exception("Invalid credentials"))

        result = runner.invoke(
            cli,
            ["login", "test@example.com", "wrong_password"],
        )

        assert result.exit_code == 1
        assert "Login failed" in result.output


class TestUpdateCommand:
    """Test update command."""

    def test_update_basic(self, runner, mock_services):
        """Test basic update command."""
        mock_services["gog_api_service"].get_games_list.return_value = {
            "products": [],
            "page": 1,
            "totalPages": 1,
            "totalProducts": 0,
        }

        result = runner.invoke(cli, ["update"])

        assert result.exit_code == 0
        assert "Updating game manifest" in result.output
        assert "Manifest updated" in result.output

    def test_update_with_filters(self, runner, mock_services):
        """Test update command with OS and language filters."""
        mock_services["gog_api_service"].get_games_list.return_value = {
            "products": [],
            "page": 1,
            "totalPages": 1,
            "totalProducts": 0,
        }

        result = runner.invoke(
            cli,
            ["update", "--os", "windows", "--lang", "en"],
        )

        assert result.exit_code == 0

    def test_update_with_game_ids(self, runner, mock_services):
        """Test update command with specific game IDs."""
        mock_services["gog_api_service"].get_games_list.return_value = {
            "products": [{"id": 1234}],
            "page": 1,
            "totalPages": 1,
            "totalProducts": 1,
        }
        mock_services["gog_api_service"].get_game_details.return_value = {
            "id": 1234,
            "title": "Test Game",
        }

        result = runner.invoke(
            cli,
            ["update", "--ids", "1234"],
        )

        assert result.exit_code == 0

    def test_update_not_authenticated(self, runner, mock_services):
        """Test update command when not authenticated."""
        mock_services["auth_service"].is_authenticated.return_value = False

        result = runner.invoke(cli, ["update"])

        assert result.exit_code == 1
        assert "Not authenticated" in result.output


class TestDownloadCommand:
    """Test download command."""

    def test_download_basic(self, runner, mock_services):
        """Test basic download command."""
        # Create a sample game
        game = Game(
            id=1234,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game Long Title",
            downloads=[],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=[],
            serials={},
            changelog=None,
            image_url="",
            bg_url="",
            store_url="",
            has_updates=False,
        )

        mock_services["manifest_service"].load_manifest.return_value = [game]
        mock_services["downloader_service"].download_game.return_value = {}

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["download", "."])

            assert result.exit_code == 0
            assert "Downloading games" in result.output

    def test_download_with_filters(self, runner, mock_services):
        """Test download command with filters."""
        game = Game(
            id=1234,
            title="Test Game",
            folder_name="test_game",
            long_title="Test Game Long Title",
            downloads=[],
            galaxy_downloads=[],
            shared_downloads=[],
            extras=[],
            serials={},
            changelog=None,
            image_url="",
            bg_url="",
            store_url="",
            has_updates=False,
        )

        mock_services["manifest_service"].load_manifest.return_value = [game]
        mock_services["manifest_service"].filter_games.return_value = [game]
        mock_services["downloader_service"].download_game.return_value = {}

        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["download", ".", "--os", "windows", "--lang", "en"],
            )

            assert result.exit_code == 0

    def test_download_not_authenticated(self, runner, mock_services):
        """Test download command when not authenticated."""
        mock_services["auth_service"].is_authenticated.return_value = False

        result = runner.invoke(cli, ["download", "."])

        assert result.exit_code == 1
        assert "Not authenticated" in result.output

    def test_download_no_games(self, runner, mock_services):
        """Test download command with no games in manifest."""
        mock_services["manifest_service"].load_manifest.return_value = []

        result = runner.invoke(cli, ["download", "."])

        assert result.exit_code == 1
        assert "No games in manifest" in result.output


class TestBackupCommand:
    """Test backup command."""

    def test_backup_basic(self, runner, mock_services):
        """Test basic backup command."""
        with runner.isolated_filesystem():
            # Create dummy files
            config_dir = Path(".gogrepoc")
            config_dir.mkdir()
            (config_dir / "manifest.json").touch()
            (config_dir / "token.json").touch()

            mock_services["storage"].manifest_path = config_dir / "manifest.json"
            mock_services["storage"].token_path = config_dir / "token.json"
            mock_services["storage"].downloaded_games_path = config_dir / "downloaded.json"

            result = runner.invoke(cli, ["backup", "backup_dir"])

            assert result.exit_code == 0
            assert "Creating backup" in result.output

    def test_backup_creates_directory(self, runner, mock_services):
        """Test backup command creates backup directory if it doesn't exist."""
        with runner.isolated_filesystem():
            config_dir = Path(".gogrepoc")
            config_dir.mkdir()
            (config_dir / "manifest.json").touch()

            mock_services["storage"].manifest_path = config_dir / "manifest.json"
            mock_services["storage"].token_path = config_dir / "token.json"
            mock_services["storage"].downloaded_games_path = config_dir / "downloaded.json"

            result = runner.invoke(cli, ["backup", "new_backup_dir"])

            assert result.exit_code == 0


class TestCleanCommand:
    """Test clean command."""

    def test_clean_basic(self, runner, mock_services):
        """Test basic clean command."""
        with runner.isolated_filesystem():
            # Create dummy .part files
            Path("file1.exe.part").touch()
            Path("file2.bin.part").touch()

            result = runner.invoke(cli, ["clean", "."])

            assert result.exit_code == 0
            assert "Cleaning temporary files" in result.output
            assert "Deleted 2 files" in result.output

    def test_clean_dry_run(self, runner, mock_services):
        """Test clean command with dry-run option."""
        with runner.isolated_filesystem():
            # Create dummy .part files
            part_file = Path("file1.exe.part")
            part_file.touch()

            result = runner.invoke(cli, ["clean", ".", "--dry-run"])

            assert result.exit_code == 0
            assert "Would delete" in result.output
            assert part_file.exists()  # File should still exist

    def test_clean_no_files(self, runner, mock_services):
        """Test clean command when no temporary files exist."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["clean", "."])

            assert result.exit_code == 0
            assert "No temporary files found" in result.output


class TestTrashCommand:
    """Test trash command."""

    def test_trash_basic(self, runner, mock_services):
        """Test basic trash command."""
        with runner.isolated_filesystem():
            # Create dummy files
            file1 = Path("file1.txt")
            file1.touch()

            result = runner.invoke(cli, ["trash", str(file1)])

            assert result.exit_code == 0
            assert "Moving" in result.output

    def test_trash_nonexistent_file(self, runner, mock_services):
        """Test trash command with nonexistent file."""
        result = runner.invoke(cli, ["trash", "nonexistent.txt"])

        # Click will fail with exit code 2 because the file doesn't exist
        # (the path validation fails)
        assert result.exit_code == 2


class TestCompressCommand:
    """Test compress command."""

    def test_compress_basic(self, runner, mock_services):
        """Test basic compress command."""
        with runner.isolated_filesystem():
            # Create dummy file
            file1 = Path("file1.txt")
            file1.write_text("test content")

            with patch("gogrepoc.utils.compression.compress_file") as mock_compress:
                # Mock compress_file to create the archive
                def create_archive(src, dest, compression_level=5):
                    dest.touch()
                    # Make it smaller than source
                    dest.write_bytes(b"compressed")

                mock_compress.side_effect = create_archive

                result = runner.invoke(cli, ["compress", str(file1)])

                assert result.exit_code == 0
                assert "Compressing" in result.output
                mock_compress.assert_called_once()

    def test_compress_with_level(self, runner, mock_services):
        """Test compress command with custom compression level."""
        with runner.isolated_filesystem():
            file1 = Path("file1.txt")
            file1.write_text("test content")

            with patch("gogrepoc.utils.compression.compress_file") as mock_compress:
                def create_archive(src, dest, compression_level=5):
                    dest.touch()
                    dest.write_bytes(b"compressed")

                mock_compress.side_effect = create_archive

                result = runner.invoke(cli, ["compress", "--level", "9", str(file1)])

                assert result.exit_code == 0
                # Check that compression_level=9 was passed
                call_args = mock_compress.call_args
                assert call_args[1]["compression_level"] == 9

    def test_compress_nonexistent_file(self, runner, mock_services):
        """Test compress command with nonexistent file."""
        result = runner.invoke(cli, ["compress", "nonexistent.txt"])

        # Click will fail with exit code 2 because the file doesn't exist
        # (the path validation fails)
        assert result.exit_code == 2


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self, runner):
        """Test CLI with invalid command."""
        result = runner.invoke(cli, ["invalid_command"])

        assert result.exit_code != 0
        assert "Error" in result.output or "No such command" in result.output

    def test_missing_required_argument(self, runner):
        """Test CLI with missing required argument."""
        result = runner.invoke(cli, ["trash"])

        assert result.exit_code != 0

    def test_invalid_option_value(self, runner):
        """Test CLI with invalid option value."""
        result = runner.invoke(cli, ["compress", "--level", "99", "file.txt"])

        assert result.exit_code != 0
