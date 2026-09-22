import json
import logging
from dataclasses import dataclass, asdict

import aiohttp

from src import control

log = logging.getLogger(__name__)

EXPECTED_NETWORK_ERRORS = (
    aiohttp.ClientError,
    TimeoutError,
    json.JSONDecodeError,
)

@dataclass
class IdConfig:
    name: str

    def to_payload(self) -> dict:
        return {"id": asdict(self)}

@dataclass
class NetworkConfig:
    off: bool

    def to_payload(self) -> dict:
        return {"nw": asdict(self)}

@dataclass
class LedHwConfig:
    total: int
    maxpwr: int

    def to_payload(self) -> dict:
        return {"hw": {"led": asdict(self)}}

async def save_config(ip: str, payload: dict) -> bool:
    # send http requests
    url = f"http://{ip}/json/cfg"
    timeout = aiohttp.ClientTimeout(total=2.0, sock_connect=1.0)
    connector = aiohttp.TCPConnector(use_dns_cache=False)

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=payload, timeout=timeout) as resp:
                return resp.status == 200
    except EXPECTED_NETWORK_ERRORS as e:
        print(f"\n[!] failed to update settings for {ip} ({e})")
        return False
    except Exception as e:
        log.exception("unexpected error updating settings for %s: %s", ip, e)
        return False

async def set_device_name(ip: str, new_name: str) -> bool:
    # change name
    return await save_config(ip, IdConfig(name=new_name).to_payload())

async def set_power_on_behavior(ip: str, turn_on: bool) -> bool:
    # change power behaivor
    return await save_config(ip, NetworkConfig(off=not turn_on).to_payload())

async def set_led_output(ip: str, count: int, max_ma: int) -> bool:
    # led output
    return await save_config(ip, LedHwConfig(total=count, maxpwr=max_ma).to_payload())

async def set_nightlight(ip: str, enabled: bool, duration_min: int = 60, target_bri: int = 0) -> bool:
    # nightlight
    duration_min = max(1, min(255, duration_min))
    target_bri = max(0, min(255, target_bri))
    payload = {
        "nl": {
            "on": enabled,
            "dur": duration_min,
            "mode": 1,  # 1 = fade
            "tbri": target_bri,
        }
    }
    return await control.send_state(ip, payload)

async def set_udp_sync(ip: str, send: bool, recv: bool) -> bool:
    # sync state
    payload = {"udpn": {"send": send, "recv": recv}}
    return await control.send_state(ip, payload)

async def save_preset(ip: str, slot: int) -> bool:
    # save current state
    slot = max(1, min(250, slot))
    return await control.send_state(ip, {"psave": slot})

async def load_preset(ip: str, slot: int) -> bool:
    # apply a saved preset
    slot = max(1, min(250, slot))
    return await control.send_state(ip, {"ps": slot})

async def reboot_device(ip: str) -> bool:
    # restart
    return await control.send_state(ip, {"rb": True})