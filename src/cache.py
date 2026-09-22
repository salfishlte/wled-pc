import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path

import aiohttp

from src.finder import check_wled_ip

log = logging.getLogger(__name__)

CACHE_FILE = Path(tempfile.gettempdir()) / "wledctl_devices_cache.json"

# how long a cached device list is worth trying before we bother re-verifying it at all. 
CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def load_cached_devices() -> list[dict] | None:
    # returns cached device list, or None if no usable cache exists
    if not CACHE_FILE.exists():
        return None

    try:
        raw = json.loads(CACHE_FILE.read_text())
        devices = raw.get("devices")
        saved_at = raw.get("saved_at", 0)

        if not devices:
            return None

        if time.time() - saved_at > CACHE_MAX_AGE_SECONDS:
            return None

        return devices
    except (json.JSONDecodeError, OSError, AttributeError, TypeError) as e:
        log.warning("cache file unreadable, ignoring it: %s", e)
        return None


def save_devices_cache(devices: list[dict]) -> None:
    try:
        CACHE_FILE.write_text(json.dumps({"devices": devices, "saved_at": time.time()}))
    except OSError as e:
        log.warning("failed to write device cache: %s", e)


async def verify_cached_devices(devices: list[dict]) -> list[dict]:
    # quick parallel re-check of just the cached ips
    connector = aiohttp.TCPConnector(limit=50, use_dns_cache=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        results = await asyncio.gather(*[check_wled_ip(session, d["ip"]) for d in devices])

    verified = []
    for cached, fresh in zip(devices, results):
        if fresh is not None and fresh.get("mac") == cached.get("mac"):
            verified.append(fresh)

    return verified