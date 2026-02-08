# GitHub Actions Workflows

## Electron Build Pipeline

The `electron-build.yml` workflow automatically builds the GOGRepoc Electron desktop application for Windows, macOS, and Linux.

### How to Trigger a Build

The workflow is triggered automatically when you push a version tag to GitHub:

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

Or create a tag for a specific commit:

```bash
git tag v1.0.0 <commit-hash>
git push origin v1.0.0
```

### Tag Format

Tags must follow the format `v*.*.*` (semantic versioning):
- `v1.0.0` ✅
- `v2.1.3` ✅
- `v0.1.0-beta` ✅
- `1.0.0` ❌ (missing 'v' prefix)
- `version-1.0` ❌ (wrong format)

### What Happens During Build

1. **Matrix Build**: Builds run in parallel on three platforms:
   - Windows (windows-latest)
   - macOS (macos-latest)
   - Linux (ubuntu-latest)

2. **Python Backend Build**:
   - Sets up Python 3.11
   - Installs dependencies
   - Runs PyInstaller to create standalone backend executable
   - Verifies the executable was created

3. **Electron Build**:
   - Sets up Node.js 20
   - Installs npm dependencies
   - Runs electron-builder for the target platform
   - Creates installers and packages

4. **Artifacts**:
   - Windows: `.exe` installer and portable executable
   - macOS: `.dmg` disk image and `.zip` archive
   - Linux: `.AppImage`, `.deb`, and `.rpm` packages

5. **GitHub Release**:
   - Creates a new GitHub release with the tag name
   - Attaches all built packages to the release
   - Generates release notes automatically
   - Includes SHA256 checksums for all files

### Viewing Build Status

After pushing a tag, you can view the build progress:

1. Go to your repository on GitHub
2. Click the "Actions" tab
3. Find your workflow run (named after your tag)
4. Click to see detailed logs for each platform

### Downloading Built Packages

Once the build completes:

1. Go to the "Releases" page on GitHub
2. Find your release (named after your tag)
3. Download the appropriate package for your platform:
   - **Windows**: `GOGRepoc-<version>-x64.exe` (installer) or `GOGRepoc-<version>-portable.exe`
   - **macOS**: `GOGRepoc-<version>.dmg` or `GOGRepoc-<version>-mac.zip`
   - **Linux**: `GOGRepoc-<version>.AppImage`, `.deb`, or `.rpm`

### Build Artifacts

Build artifacts are also available directly from the workflow run:

1. Go to Actions → Your workflow run
2. Scroll to the "Artifacts" section at the bottom
3. Download platform-specific builds (available for 7 days)

### Troubleshooting

**Build fails on Python backend:**
- Check that `requirements.txt` is up to date
- Verify `backend/gogrepoc.spec` is correct
- Check PyInstaller logs in the workflow output

**Build fails on Electron:**
- Verify `electron/package.json` has correct build configuration
- Check that backend executable exists in `backend/dist/`
- Review electron-builder logs in the workflow output

**Release not created:**
- Ensure you pushed a tag (not just created it locally)
- Verify tag format matches `v*.*.*`
- Check that all three platform builds succeeded

### Manual Testing Before Release

To test the build process locally before creating a release:

```bash
# Test Python backend build
cd backend
./build.sh  # or build.bat on Windows

# Test Electron build
cd ../electron
npm run build:win   # Windows
npm run build:mac   # macOS
npm run build:linux # Linux
```

### Versioning Strategy

Follow semantic versioning:
- **Major** (v2.0.0): Breaking changes
- **Minor** (v1.1.0): New features, backwards compatible
- **Patch** (v1.0.1): Bug fixes

Pre-release versions:
- `v1.0.0-alpha.1`: Alpha release
- `v1.0.0-beta.1`: Beta release
- `v1.0.0-rc.1`: Release candidate

### Secrets and Permissions

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions. No additional secrets are required unless you want to:

- **Code signing** (macOS): Add `CSC_LINK` and `CSC_KEY_PASSWORD` secrets
- **Code signing** (Windows): Add certificate secrets
- **Auto-update**: Configure electron-updater with appropriate secrets

### Caching

The workflow uses caching to speed up builds:
- Python dependencies are cached by `setup-python`
- npm dependencies are cached by `setup-node`

Caches are automatically invalidated when dependencies change.
