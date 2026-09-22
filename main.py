#!/usr/bin/env python3
import asyncio
import platform
import sys
from src.finder import find_wled_devices, get_local_ip_prefix
from src import control
from src import settings
from src import cache


def check_platform_support():
    system = platform.system()
    if system not in ("Linux",):
        print(f"[!] {system} is not supported yet (untested, coming later).")
        print("[!] this tool currently only runs on linux.")
        sys.exit(1)

def print_color_palette():
    # colors select for rgb, with live ansi preview swatch
    print("\n---------------- palette ----------------")
    items = list(control.COLOR_PALETTE_RGB.items())
    for i in range(0, len(items), 3):
        row = items[i:i+3]
        line = ""
        for num, (name, rgb) in row:
            swatch = control.ansi_swatch(rgb)
            line += f"{num:3d}. {swatch} {name:<20} "
        print(line)
    print("-------------------------------------------")

async def handle_rgb_menu(target_ip: str):
    # select menu for rgb
    print("\n--- select color ---")
    print("1. select from palette")
    print("2. enter own hex-code")
    
    sub_choice = input("\nchoice: ").strip()
    
    if sub_choice == "1":
        print_color_palette()
        try:
            num = int(input("\nenter number of color: "))
            if num in control.COLOR_PALETTE_RGB:
                name, rgb = control.COLOR_PALETTE_RGB[num]
                print(f"preview: {control.ansi_swatch(rgb, '      ')} {name}")
                payload = {"on": True, "seg": [{"col": [rgb]}]}
                if await control.send_state(target_ip, payload):
                    print(f"selected: {name}")
            else:
                print("[!] error, no color by this number")
        except ValueError:
            print("[!] error, enter valid number")

    elif sub_choice == "2":
        hex_code = input("enter your own hex-code (for example, #ffffff): ").strip()
        try:
            rgb = control.hex_to_rgb(hex_code)
            print(f"preview: {control.ansi_swatch(rgb, '      ')} {hex_code}")
            payload = {"on": True, "seg": [{"col": [rgb]}]}
            if await control.send_state(target_ip, payload):
                print(f"selected: {hex_code}")
        except ValueError as e:
            print(f"[!] error: {e}")

async def handle_settings_menu(target_ip: str):
    # settings
    while True:
        print("\n========================================")
        print("               settings                   ")
        print("==========================================")
        print("1. led & hardware outputs (count / ma limit)")
        print("2. power up behavior (turn on after boot)")
        print("3. change device name")
        print("4. nightlight (auto dim/off timer)")
        print("5. udp sync (multi-device)")
        print("6. save preset")
        print("7. load preset")
        print("8. reboot device")
        print("0. back")

        choice = input("\nchoice: ").strip()

        if choice == "1":
            try:
                count = int(input("enter led count: "))
                ma = int(input("enter max current limit (mA): "))
                if await settings.set_led_output(target_ip, count, ma):
                    print("[+] hardware outputs updated successfully")
            except ValueError:
                print("[!] enter correct number!")

        elif choice == "2":
            p_choice = input("turn leds on after power up? (1 - yes, 0 - no): ").strip()
            if p_choice in ["0", "1"]:
                if await settings.set_power_on_behavior(target_ip, p_choice == "1"):
                    print("[+] power up behavior updated")

        elif choice == "3":
            new_name = input("enter new device name: ").strip()
            if new_name:
                if await settings.set_device_name(target_ip, new_name):
                    print(f"[+] device renamed to: {new_name}")

        elif choice == "4":
            nl_choice = input("enable nightlight? (1 - yes, 0 - no): ").strip()
            if nl_choice in ["0", "1"]:
                enabled = nl_choice == "1"
                duration = 60
                target_bri = 0
                if enabled:
                    try:
                        duration = int(input("duration in minutes (1-255): "))
                        target_bri = int(input("target brightness at the end (0-255, 0 = off): "))
                    except ValueError:
                        print("[!] enter correct number!")
                        continue
                if await settings.set_nightlight(target_ip, enabled, duration, target_bri):
                    print(f"[+] nightlight {'enabled' if enabled else 'disabled'}")

        elif choice == "5":
            send_choice = input("send state to other devices? (1 - yes, 0 - no): ").strip()
            recv_choice = input("receive state from other devices? (1 - yes, 0 - no): ").strip()
            if send_choice in ["0", "1"] and recv_choice in ["0", "1"]:
                if await settings.set_udp_sync(target_ip, send_choice == "1", recv_choice == "1"):
                    print("[+] udp sync settings updated")

        elif choice == "6":
            try:
                slot = int(input("save current state to preset slot (1-250): "))
                if await settings.save_preset(target_ip, slot):
                    print(f"[+] saved to preset {slot}")
            except ValueError:
                print("[!] enter correct number!")

        elif choice == "7":
            try:
                slot = int(input("load preset slot (1-250): "))
                if await settings.load_preset(target_ip, slot):
                    print(f"[+] loaded preset {slot}")
            except ValueError:
                print("[!] enter correct number!")

        elif choice == "8":
            confirm = input("device will briefly go offline. reboot now? (yes/no): ").strip().lower()
            if confirm == "yes":
                if await settings.reboot_device(target_ip):
                    print("[+] reboot command sent")

        elif choice == "0":
            break

async def handle_effects_menu(target_ip: str):
    # effects
    effects = await control.get_effects(target_ip)
    if not effects:
        print("[!] couldn't fetch effects list from device")
        return

    print("\n---------------- effects ----------------")
    for i, name in enumerate(effects):
        if name == "RSVD":
            continue  # reserved placeholder, not a real selectable effect
        print(f"{i:3d}. {name}")
    print("-------------------------------------------")

    try:
        fx_id = int(input("\nenter effect number: "))
        if not (0 <= fx_id < len(effects)) or effects[fx_id] == "RSVD":
            print("[!] error, no effect by this number")
            return
    except ValueError:
        print("[!] error, enter valid number")
        return

    speed = intensity = None
    tweak = input("set speed/intensity too? (1 - yes, 0 - skip): ").strip()
    if tweak == "1":
        try:
            speed = int(input("speed (0-255): "))
            intensity = int(input("intensity (0-255): "))
        except ValueError:
            print("[!] enter correct number, skipping speed/intensity")
            speed = intensity = None

    if await control.set_effect(target_ip, fx_id, speed, intensity):
        print(f"selected effect: {effects[fx_id]}")

async def interactive_menu(target_ip: str):
    # control-panel
    caps = await control.get_device_capabilities(target_ip)
    
    while True:
        print(f"\n==========================================")
        print(f" device: {caps['name']} [{target_ip}]")
        mode_label = "PWM White" if caps['is_white_only'] else ("RGB" + (" + CCT" if caps['is_cct'] else ""))
        print(f" mode: {mode_label}")
        print(f"==========================================")

        menu_actions = {}
        curr_idx = 1

        print(f"{curr_idx}. on/off")
        menu_actions[str(curr_idx)] = "on_off"
        curr_idx += 1

        print(f"{curr_idx}. brightness")
        menu_actions[str(curr_idx)] = "brightness"
        curr_idx += 1

        if caps['is_rgb']:
            print(f"{curr_idx}. change color")
            menu_actions[str(curr_idx)] = "color"
            curr_idx += 1

        if caps['is_cct']:
            print(f"{curr_idx}. change cct")
            menu_actions[str(curr_idx)] = "cct"
            curr_idx += 1

        print(f"{curr_idx}. effects")
        menu_actions[str(curr_idx)] = "effects"
        curr_idx += 1

        print(f"{curr_idx}. settings")
        menu_actions[str(curr_idx)] = "settings"

        print("0. exit")

        choice = input("\nchoice: ").strip()
        action = menu_actions.get(choice)

        if action == "on_off":
            state = input("1 - on, 0 - off: ").strip()
            await control.send_state(target_ip, {"on": state == "1"})

        elif action == "brightness":
            try:
                bri = int(input("enter your brightness (0-100%): "))
                await control.set_brightness(target_ip, bri)
            except ValueError:
                print("[!] enter correct number!")

        elif action == "color":
            await handle_rgb_menu(target_ip)

        elif action == "cct":
            try:
                cct_val = int(input("enter temp of cct (0 = warm, 255 = cold): "))
                await control.set_cct_temperature(target_ip, cct_val)
            except ValueError:
                print("[!] enter correct number!")

        elif action == "effects":
            await handle_effects_menu(target_ip)

        elif action == "settings":
            await handle_settings_menu(target_ip)

        elif choice == "0":
            sys.exit(0)

async def main():
    devices = []

    cached = cache.load_cached_devices()
    if cached:
        print(f"[?] found {len(cached)} device(s) in cache, verifying...\n")
        devices = await cache.verify_cached_devices(cached)

    if devices and len(devices) == len(cached):
        # skip network scan
        print(f"[+] all cached devices responded, skipping network scan\n")
    else:
        prefix = get_local_ip_prefix()
        print(f"[?] searching wled devices in {prefix}0/24...\n")
        devices = await find_wled_devices()
        if devices:
            cache.save_devices_cache(devices)

    if not devices:
        print("[!] error, no wled devices")
        return

    print(f"found: {len(devices)}\n")
    for idx, dev in enumerate(devices, 1):
        print(f"[{idx}] {dev['name']} | ip: {dev['ip']} | mac: {dev['mac']}")

    if len(devices) == 1:
        selected_ip = devices[0]['ip']
    else:
        try:
            choice = int(input("\nselect number of device: "))
            selected_ip = devices[choice - 1]['ip']
        except (ValueError, IndexError):
            print("[!] enter correct number!")
            return

    await interactive_menu(selected_ip)

if __name__ == "__main__":
    check_platform_support()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass