#!/usr/bin/env python3
"""Zotero Web API wrapper.

Usage:
    python3 tools/fetch_zotero.py search "patient capital"
    python3 tools/fetch_zotero.py item ABCD1234
    python3 tools/fetch_zotero.py item https://www.zotero.org/users/123456/items/ABCD1234
    python3 tools/fetch_zotero.py collections
    python3 tools/fetch_zotero.py collection-items XYZ98765
    python3 tools/fetch_zotero.py download ABCD1234 raw/tmp/zotero/ABCD1234.pdf

Requires ZOTERO_API_KEY and ZOTERO_LIBRARY_ID in .env (see config/setup-guide.md).
ZOTERO_LIBRARY_TYPE defaults to "user" (personal library); set to "group" for a
shared group library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import _env  # noqa: F401 — load .env files for API keys

import requests

BASE_URL = "https://api.zotero.org"

ZOTERO_API_KEY = os.environ.get("ZOTERO_API_KEY", "")
ZOTERO_LIBRARY_ID = os.environ.get("ZOTERO_LIBRARY_ID", "")
ZOTERO_LIBRARY_TYPE = os.environ.get("ZOTERO_LIBRARY_TYPE", "user").strip().lower() or "user"

_HEADERS = {"Zotero-API-Version": "3"}
if ZOTERO_API_KEY:
    _HEADERS["Zotero-API-Key"] = ZOTERO_API_KEY

# Matches web links (https://www.zotero.org/users/<id>/items/<key> or
# .../groups/<id>/items/<key>) and desktop-app links
# (zotero://select/library/items/<key> or zotero://select/groups/<id>/items/<key>).
_LINK_RE = re.compile(
    r"zotero://select/library/items/(?P<key1>[A-Z0-9]+)"
    r"|zotero://select/(?P<ltype1>groups)/(?P<lid1>\d+)/items/(?P<key1b>[A-Z0-9]+)"
    r"|zotero\.org/(?P<ltype2>users|groups)/(?P<lid2>\d+)/items/(?P<key2>[A-Z0-9]+)"
)
_BARE_KEY_RE = re.compile(r"^[A-Z0-9]{8}$")


class ZoteroConfigError(RuntimeError):
    """Raised when ZOTERO_API_KEY / ZOTERO_LIBRARY_ID are missing."""


def _require_api_key() -> None:
    if not ZOTERO_API_KEY:
        raise ZoteroConfigError(
            "ZOTERO_API_KEY must be set in .env — see config/setup-guide.md "
            "(Key 5: Zotero API) or run /setup."
        )


def _require_library(library_id: str) -> None:
    if not library_id:
        raise ZoteroConfigError(
            "ZOTERO_LIBRARY_ID must be set in .env (or the reference must carry its "
            "own library id, as a full zotero.org/groups/<id>/... link does) — see "
            "config/setup-guide.md (Key 5: Zotero API) or run /setup."
        )


def resolve_ref(ref: str) -> tuple[str, str, str]:
    """Resolve a Zotero link or bare item key to (library_type, library_id, item_key).

    Falls back to the configured ZOTERO_LIBRARY_TYPE/ZOTERO_LIBRARY_ID when the
    link itself doesn't carry a library id (e.g. a personal-library desktop link
    or a bare item key).
    """
    m = _LINK_RE.search(ref)
    if m:
        ltype = m.group("ltype1") or m.group("ltype2")
        lid = m.group("lid1") or m.group("lid2")
        key = m.group("key1") or m.group("key1b") or m.group("key2")
        library_type = "groups" if ltype == "groups" else ZOTERO_LIBRARY_TYPE
        library_id = lid or ZOTERO_LIBRARY_ID
        return _normalize_type(library_type), library_id, key
    if _BARE_KEY_RE.match(ref.strip()):
        return _normalize_type(ZOTERO_LIBRARY_TYPE), ZOTERO_LIBRARY_ID, ref.strip()
    raise ValueError(f"Could not parse Zotero reference: {ref!r}")


def _normalize_type(library_type: str) -> str:
    library_type = library_type.strip().lower()
    if library_type in ("user", "users"):
        return "users"
    if library_type in ("group", "groups"):
        return "groups"
    raise ValueError(f"Unknown ZOTERO_LIBRARY_TYPE: {library_type!r} (expected user|group)")


def _library_path(library_type: str | None = None, library_id: str | None = None) -> str:
    library_type = _normalize_type(library_type or ZOTERO_LIBRARY_TYPE)
    library_id = library_id or ZOTERO_LIBRARY_ID
    return f"/{library_type}/{library_id}"


def _get(path: str, *, params: dict | None = None, stream: bool = False) -> requests.Response:
    resp = requests.get(f"{BASE_URL}{path}", headers=_HEADERS, params=params or {}, timeout=30, stream=stream)
    resp.raise_for_status()
    return resp


def search(query: str, limit: int = 25) -> list[dict]:
    """Search top-level items in the configured library by free-text query."""
    _require_api_key()
    _require_library(ZOTERO_LIBRARY_ID)
    resp = _get(f"{_library_path()}/items/top", params={"q": query, "limit": limit})
    return resp.json()


def item(ref: str) -> dict:
    """Fetch one item's metadata by bare key or Zotero link."""
    _require_api_key()
    library_type, library_id, key = resolve_ref(ref)
    _require_library(library_id)
    resp = _get(f"{_library_path(library_type, library_id)}/items/{key}")
    return resp.json()


def collections(limit: int = 100) -> list[dict]:
    """List collections in the configured library."""
    _require_api_key()
    _require_library(ZOTERO_LIBRARY_ID)
    resp = _get(f"{_library_path()}/collections", params={"limit": limit})
    return resp.json()


def collection_items(collection_key: str, limit: int = 100) -> list[dict]:
    """List top-level items in a collection."""
    _require_api_key()
    _require_library(ZOTERO_LIBRARY_ID)
    resp = _get(f"{_library_path()}/collections/{collection_key}/items/top", params={"limit": limit})
    return resp.json()


def _children(library_type: str, library_id: str, key: str) -> list[dict]:
    resp = _get(f"{_library_path(library_type, library_id)}/items/{key}/children")
    return resp.json()


def find_pdf_attachment(ref: str) -> dict | None:
    """Return the child attachment dict for the best PDF on an item, or None.

    An item's own record may itself be an attachment (ref points directly at
    one); otherwise this looks through its children for a stored PDF.
    """
    library_type, library_id, key = resolve_ref(ref)
    _require_library(library_id)
    data = item(ref)
    item_type = data.get("data", {}).get("itemType")
    if item_type == "attachment" and data.get("data", {}).get("contentType") == "application/pdf":
        return data
    for child in _children(library_type, library_id, key):
        child_data = child.get("data", {})
        if (
            child_data.get("itemType") == "attachment"
            and child_data.get("contentType") == "application/pdf"
            and child_data.get("linkMode", "").startswith("imported")
        ):
            return child
    return None


def download_attachment(ref: str, dest_path: str) -> str:
    """Download the best PDF attachment for an item to dest_path. Returns dest_path."""
    attachment = find_pdf_attachment(ref)
    if attachment is None:
        raise RuntimeError(f"No stored PDF attachment found for {ref!r}")
    library_type, library_id, _ = resolve_ref(ref)
    if not library_id:
        library_id = ZOTERO_LIBRARY_ID
    attachment_key = attachment["key"]
    resp = _get(f"{_library_path(library_type, library_id)}/items/{attachment_key}/file", stream=True)
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            f.write(chunk)
    return str(dest)


def main():
    parser = argparse.ArgumentParser(description="Zotero Web API wrapper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search library items")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("n", nargs="?", type=int, default=25, help="Max results")

    p_item = sub.add_parser("item", help="Get item metadata")
    p_item.add_argument("ref", help="Item key or Zotero link")

    sub.add_parser("collections", help="List collections in the library")

    p_citems = sub.add_parser("collection-items", help="List items in a collection")
    p_citems.add_argument("collection_key", help="Collection key")

    p_dl = sub.add_parser("download", help="Download an item's PDF attachment")
    p_dl.add_argument("ref", help="Item key or Zotero link")
    p_dl.add_argument("dest", help="Destination file path")

    args = parser.parse_args()

    try:
        if args.command == "search":
            result = search(args.query, args.n)
        elif args.command == "item":
            result = item(args.ref)
        elif args.command == "collections":
            result = collections()
        elif args.command == "collection-items":
            result = collection_items(args.collection_key)
        elif args.command == "download":
            result = {"downloaded_to": download_attachment(args.ref, args.dest)}
        else:
            result = {}
    except ZoteroConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
