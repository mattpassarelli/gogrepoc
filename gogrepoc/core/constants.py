"""Constants and configuration values for GOGRepoc.

This module contains all constant values used throughout the application,
including GOG API URLs, HTTP settings, file patterns, and default configurations.
"""

# =============================================================================
# Application Metadata
# =============================================================================

APP_NAME = 'gogrepoc.py'
APP_VERSION = '0.4.0-a'
APP_URL = 'https://github.com/mattpassarelli/gogrepoc'
APP_AUTHOR = 'eddie3,kalaynr,mattpassarelli'

# =============================================================================
# GitHub API URLs
# =============================================================================

REPO_HOME_URL = "https://api.github.com/repos/kalanyr/gogrepoc"
NEW_RELEASE_URL = "/releases/latest"

# =============================================================================
# GOG URLs and Endpoints
# =============================================================================

# Main GOG URLs
GOG_HOME_URL = 'https://www.gog.com'
GOG_ACCOUNT_URL = 'https://www.gog.com/account'
GOG_LOGIN_URL = 'https://login.gog.com/login_check'

# GOG Galaxy Authentication URLs
GOG_AUTH_URL = 'https://auth.gog.com/auth'
GOG_TOKEN_URL = 'https://auth.gog.com/token'
GOG_EMBED_URL = 'https://embed.gog.com'
GOG_GALAXY_REDIRECT_URL = GOG_EMBED_URL + '/on_login_success'

# GOG API Credentials
GOG_CLIENT_ID = '46899977096215655'
GOG_SECRET = '9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9'

# =============================================================================
# GOG Media Types
# =============================================================================

GOG_MEDIA_TYPE_GAME = '1'
GOG_MEDIA_TYPE_MOVIE = '2'

# =============================================================================
# HTTP Request Settings
# =============================================================================

HTTP_FETCH_DELAY = 1  # in seconds
HTTP_RETRY_DELAY = 5  # in seconds
HTTP_RETRY_COUNT = 4
HTTP_TIMEOUT = 60  # in seconds
HTTP_GAME_DOWNLOADER_THREADS = 4
HTTP_PERM_ERRORCODES = (404, 403)  # HTTP error codes that should not be retried
USER_AGENT = f'GOGRepoC/{APP_VERSION}'

# =============================================================================
# File Path Constants
# =============================================================================

GAME_STORAGE_DIR = '.'
TOKEN_FILENAME = 'gog-token.dat'
MANIFEST_FILENAME = 'gog-manifest.dat'
RESUME_MANIFEST_FILENAME = 'gog-resume-manifest.dat'
DOWNLOADED_GAMES_FILENAME = 'gog-downloaded-games.dat'
CONFIG_FILENAME = 'gog-config.dat'
SERIAL_FILENAME = '!serial.txt'
INFO_FILENAME = '!info.txt'

# File Extensions
TEMP_EXT = '.tmp'
BACKUP_EXT = '.bak'

# =============================================================================
# Directory Names
# =============================================================================

MD5_DIR_NAME = '!md5_xmls'
ORPHAN_DIR_NAME = '!orphaned'
DOWNLOADING_DIR_NAME = '!downloading'
PROVISIONAL_DIR_NAME = '!provisional'
IMAGES_DIR_NAME = '!images'

# =============================================================================
# File Patterns and Extensions
# =============================================================================

# File extensions that don't have MD5 data from GOG
SKIP_MD5_FILE_EXT = ['.txt', '.zip', '']
# Add numbered extensions (.001, .002, ..., .020)
for i in range(1, 21):
    SKIP_MD5_FILE_EXT.append(f'.{i:03d}')

# Installer file extensions
INSTALLERS_EXT = ['.exe', '.bin', '.dmg', '.pkg', '.sh']

# =============================================================================
# Exclusion Lists
# =============================================================================

ORPHAN_DIR_EXCLUDE_LIST = [
    ORPHAN_DIR_NAME,
    DOWNLOADING_DIR_NAME,
    IMAGES_DIR_NAME,
    MD5_DIR_NAME,
    '!misc',
]

ORPHAN_FILE_EXCLUDE_LIST = [INFO_FILENAME, SERIAL_FILENAME]

# =============================================================================
# Language Configuration
# =============================================================================

# Language table mapping two-letter codes to their Unicode GOG API names
LANG_TABLE = {
    'en': 'English',
    'bl': 'български',  # Bulgarian
    'ru': 'русский',  # Russian
    'gk': 'Ελληνικά',  # Greek
    'sb': 'Српска',  # Serbian
    'ar': 'العربية',  # Arabic
    'br': 'Português do Brasil',  # Brazilian Portuguese
    'jp': '日本語',  # Japanese
    'ko': '한국어',  # Korean
    'fr': 'français',  # French
    'cn': '中文',  # Chinese
    'cz': 'český',  # Czech
    'hu': 'magyar',  # Hungarian
    'pt': 'português',  # Portuguese
    'tr': 'Türkçe',  # Turkish
    'sk': 'slovenský',  # Slovak
    'nl': 'nederlands',  # Dutch
    'ro': 'română',  # Romanian
    'es': 'español',  # Spanish
    'pl': 'polski',  # Polish
    'it': 'italiano',  # Italian
    'de': 'Deutsch',  # German
    'da': 'Dansk',  # Danish
    'sv': 'svenska',  # Swedish
    'fi': 'Suomi',  # Finnish
    'no': 'norsk',  # Norwegian
}

VALID_LANG_TYPES = list(LANG_TABLE.keys())
DEFAULT_FALLBACK_LANG = 'en'

# =============================================================================
# Operating System Configuration
# =============================================================================

VALID_OS_TYPES = ['windows', 'linux', 'mac']

# =============================================================================
# File System Configuration
# =============================================================================

# File systems that support preallocation on Windows
WINDOWS_PREALLOCATION_FS = ["NTFS", "exFAT", "FAT32"]

# File systems that support preallocation on POSIX systems (Linux, macOS)
POSIX_PREALLOCATION_FS = ["exfat", "vfat", "ntfs", "btrfs", "ext4", "ocfs2", "xfs"]

# =============================================================================
# Windows API Constants
# =============================================================================

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
CREATE_NEW = 0x1
OPEN_EXISTING = 0x3
FILE_BEGIN = 0x0

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_MAX_MB = 180
LOG_BACKUPS = 9

# =============================================================================
# Manifest Configuration
# =============================================================================

MANIFEST_SYNTAX_VERSION = 1
RESUME_MANIFEST_SYNTAX_VERSION = 1
RESUME_SAVE_THRESHOLD = 50
