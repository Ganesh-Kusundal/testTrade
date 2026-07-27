#!/usr/bin/env python
"""Generate fresh Dhan access token using TOTP.

Usage:
    python scripts/generate_dhan_token.py
"""

import pyotp
import requests
import os
import sys

def generate_token():
    """Generate Dhan access token."""
    # Get credentials from environment
    client_id = os.environ.get('DHAN_CLIENT_ID')
    pin = os.environ.get('DHAN_PIN')
    totp_secret = os.environ.get('DHAN_TOTP_SECRET')
    
    if not all([client_id, pin, totp_secret]):
        print("❌ Missing credentials in .env file")
        print("Required: DHAN_CLIENT_ID, DHAN_PIN, DHAN_TOTP_SECRET")
        sys.exit(1)
    
    # Generate TOTP code
    totp_code = pyotp.TOTP(totp_secret).now()
    print(f"🔐 TOTP Code: {totp_code}")
    
    # Request token
    token_url = 'https://auth.dhan.co/app/generateAccessToken'
    payload = {
        'dhanClientId': client_id,
        'pin': pin,
        'totp': totp_code
    }
    
    print(f"📡 Requesting token for client: {client_id}...")
    resp = requests.post(token_url, data=payload, timeout=15)
    
    if resp.status_code != 200:
        print(f"❌ HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    
    body = resp.json()
    
    # Extract token
    access_token = body.get('accessToken')
    if not access_token:
        print(f"❌ Token not found in response: {body}")
        sys.exit(1)
    
    # Display info
    print(f"\n✅ Token generated successfully!")
    print(f"   Client: {body.get('dhanClientName')} ({body.get('dhanClientUcc')})")
    print(f"   Expires: {body.get('expiryTime')}")
    print(f"   Token: {access_token[:60]}...")
    
    # Save to .env
    env_file = '.env'
    if not os.path.exists(env_file):
        print(f"❌ .env file not found")
        sys.exit(1)
    
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith('DHAN_ACCESS_TOKEN='):
            new_lines.append(f'DHAN_ACCESS_TOKEN={access_token}\n')
        else:
            new_lines.append(line)
    
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Token saved to .env")
    return access_token

if __name__ == '__main__':
    # Load .env
    from dotenv import load_dotenv
    load_dotenv()
    
    generate_token()
