#!/usr/bin/env python3
"""Diagnostic script to check token validity and flow."""
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

from scalpr.brokers.dhan.auth import is_expiring_soon, is_token_fresh

load_dotenv()

# Decode token
token = os.environ.get("DHAN_ACCESS_TOKEN", "")
if not token:
    print("ERROR: DHAN_ACCESS_TOKEN not set")
    sys.exit(1)

parts = token.split(".")
if len(parts) != 3:
    print(f"ERROR: Invalid JWT format (parts={len(parts)})")
    sys.exit(1)

# Decode payload
payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
payload = json.loads(base64.urlsafe_b64decode(payload_b64))
exp = datetime.fromtimestamp(payload["exp"])
now = datetime.now()

print(f"Token signature: {parts[2][:20]}... (length={len(parts[2])})")
print(f"Token expiry: {exp}")
print(f"Now: {now}")
print(f"Hours until expiry: {(exp - now).total_seconds() / 3600:.1f}")
print(f"Token is fresh: {exp > now}")

# Check if signature looks like a placeholder
if len(parts[2]) < 20:
    print(f"WARNING: Token signature looks truncated ({len(parts[2])} chars)")

print(f"\nis_token_fresh (15min buffer): {is_token_fresh(token)}")
print(f"is_expiring_soon (15min buffer): {is_expiring_soon(token)}")
