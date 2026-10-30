"""Sanity check: can the service principal call the Fabric API and see its workspaces?

Run locally (never commit the secret):
  export AZURE_TENANT_ID=... AZURE_CLIENT_ID=... AZURE_CLIENT_SECRET=...
  pip install azure-identity requests
  python scripts/check_access.py
"""

import os
import sys

import requests
from azure.identity import ClientSecretCredential

cred = ClientSecretCredential(
    tenant_id=os.environ["AZURE_TENANT_ID"],
    client_id=os.environ["AZURE_CLIENT_ID"],
    client_secret=os.environ["AZURE_CLIENT_SECRET"],
)
token = cred.get_token("https://api.fabric.microsoft.com/.default").token
resp = requests.get(
    "https://api.fabric.microsoft.com/v1/workspaces",
    headers={"Authorization": f"Bearer {token}"},
    timeout=30,
)
print("HTTP", resp.status_code)
if resp.status_code != 200:
    print(resp.text)
    sys.exit(1)
for ws in resp.json().get("value", []):
    print(f"{ws['id']}  {ws['displayName']}")
