"""CI checks for a Fabric Git-integrated repo.

Checks:
  1. Every item folder has a valid .platform file (type, displayName, logicalId).
  2. logicalIds are unique across the repo.
  3. Every notebook parses as Python (Fabric magics such as `!pip` are neutralised first).
  4. parameter.yml is well formed.
  5. Every GUID hardcoded in a notebook's META header (lakehouse / workspace ids)
     is covered by a find_value in parameter.yml, so it will not leak Dev ids into Test/Prod.

Usage: python scripts/validate_repo.py [fabric_root]
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import yaml

GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
META_ID_KEYS = ("default_lakehouse", "default_lakehouse_workspace_id", "id", "workspaceId")

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)
    print(f"::error::{msg}")


def check_platform_files(root: Path) -> None:
    seen: dict[str, Path] = {}
    platforms = sorted(root.rglob(".platform"))
    if not platforms:
        err(f"No .platform files found under {root}")
    for p in platforms:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            err(f"{p}: invalid JSON ({e})")
            continue
        meta, cfg = data.get("metadata", {}), data.get("config", {})
        for key in ("type", "displayName"):
            if not meta.get(key):
                err(f"{p}: metadata.{key} missing")
        logical_id = cfg.get("logicalId")
        if not logical_id:
            err(f"{p}: config.logicalId missing")
        elif logical_id in seen:
            err(f"{p}: duplicate logicalId also used by {seen[logical_id]}")
        else:
            seen[logical_id] = p
    print(f"Checked {len(platforms)} .platform file(s)")


def notebook_to_python(text: str) -> str:
    """Neutralise notebook-only syntax so the file can be parsed as Python."""
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("!", "%")):
            out.append("# " + line)  # shell / magic command
        else:
            out.append(line)
    return "\n".join(out)


def load_find_values(root: Path) -> set[str]:
    param = root / "parameter.yml"
    if not param.exists():
        return set()
    try:
        doc = yaml.safe_load(param.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        err(f"{param}: invalid YAML ({e})")
        return set()
    values: set[str] = set()
    for i, entry in enumerate(doc.get("find_replace", []) or []):
        if "find_value" not in entry or "replace_value" not in entry:
            err(f"{param}: find_replace[{i}] needs find_value and replace_value")
            continue
        values.add(str(entry["find_value"]).lower())
    return values


def check_notebooks(root: Path, find_values: set[str]) -> None:
    notebooks = sorted(root.rglob("notebook-content.py"))
    for nb in notebooks:
        text = nb.read_text(encoding="utf-8")
        try:
            ast.parse(notebook_to_python(text), filename=str(nb))
        except SyntaxError as e:
            err(f"{nb}:{e.lineno}: syntax error: {e.msg}")

        # GUIDs in the META header (dependencies block) are environment specific.
        header = text.split("# CELL", 1)[0]
        for guid in sorted(set(re.findall(GUID, header))):
            if guid.lower() not in find_values:
                err(
                    f"{nb}: hardcoded id {guid} in notebook metadata is not covered by "
                    f"a find_value in parameter.yml (it would point at the Dev workspace)"
                )
    print(f"Checked {len(notebooks)} notebook(s)")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "open_meteo_git_folder")
    if not root.is_dir():
        err(f"Fabric folder not found: {root}")
        return 1
    check_platform_files(root)
    find_values = load_find_values(root)
    check_notebooks(root, find_values)
    if errors:
        print(f"\n{len(errors)} problem(s) found")
        return 1
    print("All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
