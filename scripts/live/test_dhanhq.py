import os

from dhanhq import dhanhq
from dotenv import load_dotenv

load_dotenv(".env")

client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

dhan = dhanhq(client_id, access_token)

try:
    print("Testing get_fund_limits using dhanhq...")
    res = dhan.get_fund_limits()
    print("Response:", res)
except Exception as e:
    print(f"Error: {e}")
