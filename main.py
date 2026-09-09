#!/usr/bin/env python3
import asyncio
import sys
from src.finder import find_wled_devices, get_local_ip_prefix
from src import control
from src import settings


def print_color_palette():
    # colors select for rgb
    print("\n---------------- palette ----------------")
    items = list(control.COLOR_PALETTE_RGB.items())
    for i in range(0, len(items), 4):
        row = items[i:i+4]
        line = ""
        for num, (name, _) in row:
            line += f"{num:2d}. {name:<18} "
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
            payload = {"on": True, "seg": [{"col": [rgb]}]}
            if await control.send_state(target_ip, payload):
                print(f"selected: {hex_code}")
        except ValueError as e:
            print(f"[!] error: {e}")


async def handle_settings_menu(target_ip: str):
    # hardware and system settings
    while True:
        print("\n========================================")
        print("               settings                   ")
        print("==========================================")
        print("1. led & hardware outputs (count / ma limit)")
        print("2. power up behavior (turn on after boot)")
        print("3. change device name")
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

        elif choice == "0":
            break


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

        elif action == "settings":
            await handle_settings_menu(target_ip)

        elif choice == "0":
            sys.exit(0)


async def main():
    prefix = get_local_ip_prefix()
    print(f"[?] searching wled devices in {prefix}0/24...\n")
    devices = await find_wled_devices()
    
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
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass