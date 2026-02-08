# Browser-Based Authentication Update

## Overview
This update enhances the GOGRepoc authentication flow to match the reference repository's browser-based OAuth approach, providing a better user experience and supporting all GOG login methods.

## Current State
✅ **Backend is ready!** The `AuthService` already implements the full OAuth flow:
- Fetches auth page and login tokens
- Handles credential submission
- Supports 2FA (TOTP and email)
- Exchanges authorization codes for access tokens

❌ **CLI needs updating:** Currently prompts for username/password in the terminal

## Proposed Changes

### 1. New AuthService Methods
Add two new methods to `gogrepoc/services/auth.py`:

```python
def get_auth_url(self) -> str:
    """Generate GOG OAuth authorization URL for browser.
    
    Returns:
        Full URL to open in browser for user authentication
    """
    params = {
        'client_id': self.CLIENT_ID,
        'redirect_uri': self.REDIRECT_URI + '?origin=client',
        'response_type': 'code',
        'layout': 'client2'
    }
    # Build and return URL
    
async def login_with_code(self, auth_code: str) -> Token:
    """Exchange authorization code for access token.
    
    Args:
        auth_code: Authorization code from redirect URL
        
    Returns:
        Token object with access/refresh tokens
        
    Raises:
        AuthError: If code exchange fails
    """
    # Exchange code for tokens (similar to existing login step 3)
```

### 2. Updated CLI Login Command
Modify `gogrepoc/cli/main.py` login command:

**Before:**
```python
@cli.command()
@click.argument("username", required=False)
@click.argument("password", required=False)
def login(ctx, username, password):
    # Prompts for credentials
    # Calls auth_service.login(username, password)
```

**After:**
```python
@cli.command()
def login(ctx):
    """Login to GOG using browser-based authentication."""
    import webbrowser
    from urllib.parse import urlparse, parse_qs
    
    # 1. Generate auth URL
    auth_url = ctx.auth_service.get_auth_url()
    
    # 2. Open browser
    click.echo("Opening browser for GOG authentication...")
    click.echo(f"If browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)
    
    # 3. Prompt for redirect URL
    click.echo("\nAfter logging in, you'll be redirected to a page.")
    click.echo("Copy the FULL URL from your browser's address bar and paste it here.")
    redirect_url = click.prompt("Redirect URL")
    
    # 4. Extract code
    parsed = urlparse(redirect_url)
    query = parse_qs(parsed.query)
    code = query.get('code', [None])[0]
    
    if not code:
        click.secho("✗ Could not extract authorization code from URL", fg="red")
        sys.exit(1)
    
    # 5. Exchange code for token
    await ctx.auth_service.login_with_code(code)
    click.secho("✓ Login successful!", fg="green")
```

## Benefits

1. **Better UX**: Users authenticate through familiar browser interface
2. **More Login Options**: Supports Google, Discord, and other OAuth providers
3. **No Password in Terminal**: More secure - credentials never typed in CLI
4. **Matches Reference Repo**: Aligns with `gogrepoc_new.py` behavior
5. **2FA Friendly**: Browser handles 2FA naturally

## Implementation Tasks

See `tasks.md` for detailed implementation tasks:
- **Task 7.2.1**: Add `get_auth_url()` and `login_with_code()` to AuthService
- **Task 12.2.1**: Update CLI login command to use browser-based flow

## Testing

After implementation, test the flow:

```bash
# 1. Run login command
gogrepoc login

# Expected: Browser opens to GOG login page
# User logs in (with any method)
# User copies redirect URL
# User pastes URL in terminal
# Token is saved

# 2. Verify authentication
gogrepoc update

# Expected: Works without re-authentication
```

## Backward Compatibility

The existing `login(username, password)` method will remain for:
- Programmatic/automated use cases
- API/web UI authentication
- Testing purposes

The CLI will use the new browser-based flow by default.

## Reference

Based on: https://github.com/wing32s/gogrepoc
- See `gogrepoc_new.py` login command implementation
- OAuth flow matches GOG's official authentication method
