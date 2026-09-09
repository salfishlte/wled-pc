import aiohttp
from includes.colors import COLOR_PALETTE

def hex_to_rgb(hex_str: str) -> list[int]:
    # convert hex > rgb
    clean_hex = hex_str.lstrip('#')
    if len(clean_hex) != 6:
        raise ValueError("[!] enter correct hex")
    return [int(clean_hex[i:i+2], 16) for i in (0, 2, 4)]

COLOR_PALETTE_RGB = {
    num: (name, hex_to_rgb(hex_code)) 
    for num, (name, hex_code) in COLOR_PALETTE.items()
}


async def send_state(ip: str, payload: dict) -> bool:
    # send json-status
    url = f"http://{ip}/json/state"
    timeout = aiohttp.ClientTimeout(total=2.0, sock_connect=1.0)
    connector = aiohttp.TCPConnector(use_dns_cache=False)
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=payload, timeout=timeout) as resp:
                return resp.status == 200
    except Exception as e:
        print(f"\n[!] failed to send request for {ip} ({e})")
        return False


async def get_device_capabilities(ip: str) -> dict:
    # wled give me some answers for questions
    url = f"http://{ip}/json"
    default_caps = {
        "is_rgb": False,
        "is_cct": False,
        "is_white_only": True,
        "name": "WLED"
    }
    
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

                    return {
                        "is_rgb": is_rgb,
                        "is_cct": is_cct,
                        "is_white_only": is_white_only,
                        "name": info.get("name", "WLED")
                    }
    except Exception:
        pass
        
    return default_caps


async def set_brightness(ip: str, percent: int) -> bool:
    # brightness control
    bri_val = int(max(0, min(100, percent)) * 2.55)
    return await send_state(ip, {"on": True if bri_val > 0 else False, "bri": bri_val})


async def set_cct_temperature(ip: str, cct_val: int) -> bool:
    # cct control
    cct_val = max(0, min(255, cct_val))
    return await send_state(ip, {"on": True, "seg": [{"cct": cct_val}]})