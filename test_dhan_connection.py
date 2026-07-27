import os
import requests
from dotenv import load_dotenv
from config.endpoints import Dhan

load_dotenv(".env")

class SimpleHttpClient:
    def __init__(self, client_id, access_token):
        self.headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-type": "application/json",
            "Accept": "application/json"
        }
        self.base_url = Dhan.REST_BASE

    def get(self, path):
        url = f"{self.base_url}{path}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error Body: {response.text}")
        response.raise_for_status()
        return response.json()

client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

http_client = SimpleHttpClient(client_id, access_token)

try:
    res = http_client.get("/fundlimit")
    import json
    print("Success:")
    print(json.dumps(res, indent=2))
except Exception as e:
    print(f"Connection Failed: {e}")

