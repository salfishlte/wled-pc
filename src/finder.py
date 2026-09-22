import asyncio
import json
import logging
import socket
from dataclasses import dataclass, asdict

import aiohttp

log = logging.getLogger(__name__)

EXPECTED_NETWORK_ERRORS = (
    aiohttp.ClientError,
    TimeoutError,
    json.JSONDecodeError,
)

@dataclass
class WledDevice:
    ip: str
    mac: str
    name: str
    version: str
    architecture: str

def get_local_ip_prefix() -> str:
    # determines ip-prefix
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = '127.0.0.1'
    finally:
        s.close()
    return '.'.join(ip.split('.')[:-1]) + '.'

async def check_wled_ip(session: aiohttp.ClientSession, ip: str) -> dict | None:
    # check ip for wled api
    url = f"http://{ip}/json/info"
    timeout = aiohttp.ClientTimeout(total=1.5, sock_connect=0.5)

    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                data = await response.json()

                if data.get("brand") == "wled" or "leds" in data:
                    mac_raw = data.get("mac", "")
                    if mac_raw:
                        mac = ":".join([mac_raw[i:i + 2] for i in range(0, len(mac_raw), 2)]).upper()
                    else:
                        mac = "?"

                    return asdict(WledDevice(
                        ip=ip,
                        mac=mac,
                        name=data.get("name", "wled device"),
                        version=data.get("ver", "n/a"),
                        architecture=data.get("arch", "n/a"),
                    ))
    except EXPECTED_NETWORK_ERRORS:
        # normal for devices that are offline / not wled / slow to respond
        pass
    except Exception as e:
        log.exception("unexpected error checking %s: %s", ip, e)

    return None

async def find_wled_devices() -> list[dict]:
    # scan network on 0..255
    prefix = get_local_ip_prefix()
    connector = aiohttp.TCPConnector(limit=100, use_dns_cache=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_wled_ip(session, f"{prefix}{i}") for i in range(1, 255)]
        results = await asyncio.gather(*tasks)

    return [item for item in results if item is not None]