import sys
import os

sys.path.insert(0, "/system/apps/govee")
os.chdir("/system/apps/govee")

from badgeware import io, brushes, shapes, screen, PixelFont, run
import network
import requests

import gc

# Load fonts
small_font = PixelFont.load("/system/assets/fonts/ark.ppf")
large_font = PixelFont.load("/system/assets/fonts/absolute.ppf")

# Colors
white = brushes.color(235, 245, 255)
green = brushes.color(46, 160, 67)
red = brushes.color(248, 81, 73)
phosphor = brushes.color(211, 250, 55)
background = brushes.color(13, 17, 23)
gray = brushes.color(100, 110, 120)

# State
WIFI_TIMEOUT = 60
WIFI_PASSWORD = None
WIFI_SSID = None

wlan = None
connected = False
ticks_start = None
devices = {}
loading = False
error_message = None
last_update = None
selected_stock = 0
auto_refresh = True
state = {}



def get_wifi_credentials():
    global WIFI_PASSWORD, WIFI_SSID
    
    if WIFI_SSID is not None:
        return True
    
    try:
        sys.path.insert(0, "/")
        from secrets import WIFI_PASSWORD, WIFI_SSID
        sys.path.pop(0)
    except ImportError:
        WIFI_PASSWORD = None
        WIFI_SSID = None
    
    return WIFI_SSID is not None


def wlan_start():
    global wlan, ticks_start, connected, WIFI_PASSWORD, WIFI_SSID
    
    if ticks_start is None:
        ticks_start = io.ticks
    
    if connected:
        return True
    
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        if wlan.isconnected():
            return True
        
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        print("Connecting to WiFi...")
    
    connected = wlan.isconnected()
    
    if io.ticks - ticks_start < WIFI_TIMEOUT * 1000:
        if connected:
            return True
    elif not connected:
        return False
    
    return True


def fetch_devices():
    """Fetch list of devices from the Govee API"""
    try:
        from secrets import GOVEE_API_KEY
        url = "https://developer-api.govee.com/v1/devices"
        response = requests.get(
            url=url,
            headers={
                "Govee-API-Key": GOVEE_API_KEY,
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 429:
            print("Rate limited")
            return {}

        result = response.json()
        print(f"Fetch Devices - Response Body: {result}")

        # Parse result
        devices = result["data"]["devices"]
        dict = {}
        for item in devices:
            current_state = fetch_device_state(item["device"], item["model"])
            dict[item["deviceName"]] = {
                "id": item["device"],
                "model": item["model"],
                "commands": item["supportCmds"],
                "state": current_state
            }

        return dict

    except Exception as e:
        print(f"Error fetching devices from Govee {e}")
        return {}
    
def fetch_device_state(id, model):
    from secrets import GOVEE_API_KEY
    url = f"https://developer-api.govee.com/v1/devices/state?device={id}&model={model}"
    response = requests.get(
        url=url,
        headers={
            "Govee-API-Key": GOVEE_API_KEY,
            "Content-Type": "application/json"
        }
    )
    result = response.json()
    print(f"Device Status - Response Body: {result}")

    power_state = None
    properties = result["data"]["properties"]
    for property in properties:
        if property.get("powerState"):
            power_state = property.get("powerState")

    if not power_state:
        raise Exception("Unable to determine power state")

    return power_state

def inverse_state(device):
    global state
    if state[device] == "on":
        state[device] = "off"
        return "off"
    else:
        state[device] = "on"
        return "on"
    

def fetch_all_devices():
    global devices, loading, error_message, last_update, state
    
    loading = True
    error_message = None
    devices = fetch_devices()
    for key in devices.keys():
        state[key] = devices[key]["state"]
    
    loading = False
    last_update = io.ticks
    gc.collect()

def toggle_device(device):
    """Toggle a device on or off"""
    try:
        from secrets import GOVEE_API_KEY
        url = "https://developer-api.govee.com/v1/devices/control"
        new_state = inverse_state(device)
        json_data = {
                "device": "0E:2D:D4:AD:FC:EF:C8:BD",
                "model": "H5083",
                "cmd": {
                    "name": "turn",
                    "value": new_state
                }
            }
        response = requests.put(
            url=url,
            json=json_data,
            headers={
                "Govee-API-Key": GOVEE_API_KEY,
                "Content-Type": "application/json"
            }
        )
        
        result = response.json()
        print(f"Toggle Device - Response Body: {result}")

        # Parse result
        code = result["code"]
        message = result["message"]
        data = result["data"]

        returned_result = {
            "code": code,
            "message": message,
            "data": data
        }

        devices["Stereo"]["state"] = new_state

        # Clean up and return result
        del result
        return returned_result

    except Exception as e:
        print(f"Error toggling device {e}")
        return {}


def draw_device(name, state, y):
    """Draw a single device"""
    
    # Draw name
    screen.font = small_font
    screen.brush = white
    
    # Draw price
    screen.text(f"{name}", 5, y + 9)

    # Determine color
    if state == "on":
        color = green
    elif state == "off":
        color = red
    
    # Draw change
    change_text = f" {state}"
    screen.brush = color
    w, _ = screen.measure_text(change_text)
    screen.text(change_text, (155 - w) + 1, y + 9)


def center_text(text, y):
    w, _ = screen.measure_text(text)
    screen.text(text, 80 - (w / 2), y)


def draw_devices():
    # Clear screen
    screen.brush = background
    screen.draw(shapes.rectangle(0, 0, 160, 120))
    
    # Draw header
    screen.font = small_font
    screen.brush = phosphor
    screen.text("DEVICES", 2, 2)
    
    # Draw refresh indicator
    if auto_refresh and last_update:
        elapsed = (io.ticks - last_update) / 1000
        if elapsed < 60:
            screen.brush = gray
            w, _ = screen.measure_text("60s")
            screen.text(f"{int(60-elapsed)}s", 155 - w, 2)
    
    if loading:
        screen.font = large_font
        screen.brush = white
        center_text("Loading", 35)
        center_text("Devices", 50)
        screen.font = small_font
        screen.brush = gray
        # Animated dots
        dots = "." * ((int(io.ticks / 500) % 3) + 1)
        center_text(f"Please wait{dots}", 70)
        
    elif devices:
        # Draw devices
        y = 18
        for key in devices.keys():
            draw_device(key, devices[key]["state"], y)
            y += 20
    
    else:
        # No data yet - show loading message
        screen.font = large_font
        screen.brush = white
        center_text("Loading", 35)
        center_text("Devices", 50)
        screen.font = small_font
        screen.brush = gray
        # Animated dots
        dots = "." * ((int(io.ticks / 500) % 3) + 1)
        center_text(f"Please wait{dots}", 70)
    
    # Draw status bar
    screen.font = small_font
    if connected:
        screen.brush = phosphor
        screen.text("B:Toggle", 2, 108)
    else:
        screen.brush = gray
        screen.text("Connecting...", 2, 108)


def update():
    """Main update loop for device display"""
    global connected, loading, last_update, auto_refresh
    
    # Handle WiFi connection
    if not get_wifi_credentials():
        screen.brush = background
        screen.draw(shapes.rectangle(0, 0, 160, 120))
        screen.font = large_font
        screen.brush = white
        center_text("No WiFi Config", 40)
        screen.font = small_font
        screen.brush = phosphor
        center_text("Edit secrets.py", 60)
        return
    
    # Try to connect if not connected
    if not connected:
        connection_result = wlan_start()
        if not connection_result and ticks_start and (io.ticks - ticks_start) >= WIFI_TIMEOUT * 1000:
            # Only show error after timeout
            screen.brush = background
            screen.draw(shapes.rectangle(0, 0, 160, 120))
            screen.font = large_font
            screen.brush = white
            center_text("Connection Failed", 40)
            screen.font = small_font
            screen.brush = phosphor
            center_text("Check WiFi settings", 60)
            return
    
    # Fetch device data once connected
    if connected and not devices and not loading:
        fetch_all_devices()
    
    # Manual refresh on B button
    if io.BUTTON_B in io.pressed and not loading:
        toggle_device("Stereo")
        print(f"State: ", state)
    
    # Auto-refresh every 60 seconds
    if auto_refresh and last_update and (io.ticks - last_update) > 60000 and not loading:
        fetch_all_devices()
    
    draw_devices()


if __name__ == "__main__":
    run(update)
