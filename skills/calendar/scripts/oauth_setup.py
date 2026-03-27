#!/usr/bin/env python3
"""
OAuth Setup Script - Run ONCE to authorize Google Calendar access.
Works on headless servers (no browser needed).

Usage:
  python3 oauth_setup.py
"""

import os
import sys

# Check for required packages
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
except ImportError:
    print("Missing packages. Install with:")
    print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client --break-system-packages")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/calendar']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')


def main():
    print("=" * 50)
    print("Google Calendar OAuth Setup")
    print("=" * 50)

    # Check for credentials.json
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ Missing: {CREDENTIALS_FILE}")
        print("\nTo fix:")
        print("1. Go to console.cloud.google.com")
        print("2. APIs & Services → Credentials")
        print("3. Create OAuth client ID (Desktop app)")
        print("4. Download JSON and save as credentials.json")
        sys.exit(1)

    print(f"\n✓ Found credentials.json")

    # Check if already authorized
    if os.path.exists(TOKEN_FILE):
        print(f"✓ Token already exists at {TOKEN_FILE}")
        print("\nTo re-authorize, delete token.json and run again.")

        # Test the token
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds.valid:
                print("✓ Token is valid!")
            elif creds.expired and creds.refresh_token:
                print("⟳ Token expired but can be refreshed (will happen automatically)")
            else:
                print("⚠ Token invalid, delete token.json and run again")
        except Exception as e:
            print(f"⚠ Error reading token: {e}")
        return

    # Run OAuth flow - console mode for headless servers
    print("\n" + "=" * 50)
    print("AUTHORIZATION REQUIRED")
    print("=" * 50)

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    # Generate authorization URL
    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
    auth_url, _ = flow.authorization_url(prompt='consent')

    print("\n1. Open this URL in your browser:\n")
    print(auth_url)
    print("\n2. Log in with your Google account")
    print("3. Click 'Allow' to grant calendar access")
    print("4. Copy the authorization code shown")
    print("\n" + "=" * 50)

    code = input("Paste the authorization code here: ").strip()

    if not code:
        print("❌ No code provided")
        sys.exit(1)

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Save the token
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

        print(f"\n✅ Success! Token saved to {TOKEN_FILE}")
        print("\nThis token will auto-refresh - no daily login needed!")
        print("\nNow restart the middleware:")
        print("  systemctl restart telegram-middleware")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
