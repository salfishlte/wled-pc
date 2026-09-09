import aiohttp


async def save_config(ip: str, payload: dict) -> bool:
    # send http requests 
    url = f"http://{ip}/json/cfg"
    timeout = aiohttp.ClientTimeout(total=2.0, sock_connect=1.0)
    connector = aiohttp.TCPConnector(use_dns_cache=False)
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=payload, timeout=timeout) as resp:
                return resp.status == 200
    except Exception as e:
        print(f"\n[!] failed to update settings for {ip} ({e})")
        return False


async def set_device_name(ip: str, new_name: str) -> bool:
    # change name 
    return await save_config(ip, {"id": {"name": new_name}})


async def set_power_on_behavior(ip: str, turn_on: bool) -> bool:
    # change power behaivor
    return await save_config(ip, {"nw": {"off": not turn_on}})


async def set_led_output(ip: str, count: int, max_ma: int) -> bool:
    # led output (in beta)
    payload = {
        "hw": {
            "led": {
                "total": count,
                "maxpwr": max_ma
            }
        }
    }
    return await save_config(ip, payload)