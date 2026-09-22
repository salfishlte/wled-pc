import json
import logging
from dataclasses import dataclass, asdict, field

import aiohttp

from includes.colors import COLOR_PALETTE

log = logging.getLogger(__name__)

def hex_to_rgb(hex_str: str) -> list[int]:
    # convert hex > rgb
    clean_hex = hex_str.lstrip('#')
    if len(clean_hex) != 6:
        raise ValueError("[!] enter correct hex")
    try:
        return [int(clean_hex[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        raise ValueError("[!] enter correct hex")

COLOR_PALETTE_RGB = {
    num: (name, hex_to_rgb(hex_code))
    for num, (name, hex_code) in COLOR_PALETTE.items()
}

def ansi_swatch(rgb: list[int], text: str = "  ") -> str:
    # live preview of a color in  terminal
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m{text}\033[0m"

@dataclass
class DeviceCapabilities:
    is_rgb: bool = False
    is_cct: bool = False
    is_white_only: bool = True
    name: str = "WLED"

@dataclass
class SegmentState:
    cct: int | None = None

    def to_payload(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class StatePayload:
    on: bool | None = None
    bri: int | None = None
    seg: list[SegmentState] = field(default_factory=list)

    def to_payload(self) -> dict:
        payload = {k: v for k, v in asdict(self).items() if v is not None and k != "seg"}
        if self.seg:
            payload["seg"] = [s.to_payload() for s in self.seg]
        return payload

EXPECTED_NETWORK_ERRORS = (
    aiohttp.ClientError,
    TimeoutError,
    json.JSONDecodeError,
)

async def send_state(ip: str, payload: StatePayload | dict) -> bool:
    # send json-status
    url = f"http://{ip}/json/state"
    timeout = aiohttp.ClientTimeout(total=2.0, sock_connect=1.0)
    connector = aiohttp.TCPConnector(use_dns_cache=False)

    body = payload.to_payload() if isinstance(payload, StatePayload) else payload

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=body, timeout=timeout) as resp:
                return resp.status == 200
    except EXPECTED_NETWORK_ERRORS as e:
        print(f"\n[!] failed to send request for {ip} ({e})")
        return False
    except Exception as e:
        log.exception("unexpected error sending state to %s: %s", ip, e)
        return False

async def get_device_capabilities(ip: str) -> dict:
    # wled give me some answers for questions
    url = f"http://{ip}/json"
    default_caps = asdict(DeviceCapabilities())

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=2.0)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    info = data.get("info", {})
                    leds = info.get("leds", {})

                    is_rgbw = leds.get("rgbw", False)
                    is_cct = leds.get("cct", 0) > 0 or info.get("cct", False)

                    # if device dont have rgb, rgbw, cct - its pwmwhite
                    is_white_only = not is_rgbw and not is_cct and leds.get("wv", False)
                    is_rgb = not is_white_only

                    return asdict(DeviceCapabilities(
                        is_rgb=is_rgb,
                        is_cct=is_cct,
                        is_white_only=is_white_only,
                        name=info.get("name", "WLED"),
                    ))
    except EXPECTED_NETWORK_ERRORS as e:
        print(f"\n[!] failed to get capabilities for {ip} ({e})")
    except Exception as e:
        log.exception("unexpected error getting capabilities for %s: %s", ip, e)

    return default_caps

async def get_effects(ip: str) -> list[str]:
    # fetch list of effect names, index in list == fx id used by set_effect
    url = f"http://{ip}/json/eff"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=2.0)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data if isinstance(data, list) else []
    except EXPECTED_NETWORK_ERRORS as e:
        print(f"\n[!] failed to get effects for {ip} ({e})")
    except Exception as e:
        log.exception("unexpected error getting effects for %s: %s", ip, e)
    return []

async def set_effect(ip: str, fx_id: int, speed: int | None = None, intensity: int | None = None) -> bool:
    seg: dict = {"fx": fx_id}
    if speed is not None:
        seg["sx"] = max(0, min(255, speed))
    if intensity is not None:
        seg["ix"] = max(0, min(255, intensity))
    return await send_state(ip, {"on": True, "seg": [seg]})

async def set_brightness(ip: str, percent: int) -> bool:
    # brightness control
    bri_val = int(max(0, min(100, percent)) * 2.55)
    return await send_state(ip, StatePayload(on=bri_val > 0, bri=bri_val))

async def set_cct_temperature(ip: str, cct_val: int) -> bool:
    # cct control
    cct_val = max(0, min(255, cct_val))
    return await send_state(ip, StatePayload(on=True, seg=[SegmentState(cct=cct_val)]))