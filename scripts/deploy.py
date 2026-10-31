"""Deploy the Fabric items in this repo to one workspace using fabric-cicd.

Environment variables (set by the GitHub Actions workflow):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET  service principal credentials
  FABRIC_WORKSPACE_ID                                    target workspace id
  FABRIC_ENVIRONMENT                                     TEST or PROD (key used in parameter.yml)

Local run as yourself instead of a service principal:
  az login
  USE_AZURE_CLI=1 FABRIC_WORKSPACE_ID=<id> FABRIC_ENVIRONMENT=TEST python scripts/deploy.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from azure.identity import AzureCliCredential, ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items

REPO_DIR = Path(__file__).resolve().parent.parent / "open_meteo_git_folder"
# Lakehouse is listed so it exists before the notebook that references it.
ITEM_TYPES = ["Lakehouse", "Notebook"]


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def get_credential():
    if os.environ.get("USE_AZURE_CLI") == "1":
        return AzureCliCredential()
    return ClientSecretCredential(
        tenant_id=require("AZURE_TENANT_ID"),
        client_id=require("AZURE_CLIENT_ID"),
        client_secret=require("AZURE_CLIENT_SECRET"),
    )


def main() -> None:
    workspace = FabricWorkspace(
        workspace_id=require("FABRIC_WORKSPACE_ID"),
        environment=require("FABRIC_ENVIRONMENT"),
        repository_directory=str(REPO_DIR),
        item_type_in_scope=ITEM_TYPES,
        token_credential=get_credential(),
    )
    publish_all_items(workspace)
    # Removes in-scope items from the workspace that are no longer in the repo.
    unpublish_all_orphan_items(workspace)


if __name__ == "__main__":
    main()
