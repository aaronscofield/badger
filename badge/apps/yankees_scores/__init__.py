"""Look up Yankees scores by MLB schedule date."""

import os
import sys
import time


APP_DIR = "/system/apps/yankees_scores"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

URL = (
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=147&date=%s"
    "&hydrate=team&fields=dates,date,games,gameNumber,status,abstractGameState,"
    "detailedState,teams,away,home,score,team,abbreviation"
)
FIRST_YEAR, LAST_YEAR = 1903, 2099
WIFI_TIMEOUT_MS = 12000
REQUEST_TIMEOUT = 8
FIELDS = ("YEAR", "MONTH", "DAY")

badge.mode(HIRES | VSYNC)
screen.fill_rule = image.EVEN_ODD
NAVY = color.rgb(13, 23, 43)
PANEL = color.rgb(27, 44, 71)
WHITE = color.rgb(248, 249, 253)
MUTED = color.rgb(180, 199, 224)
RED = color.rgb(255, 121, 127)

date = list(time.localtime()[:3])
if not 2026 <= date[0] <= LAST_YEAR:
    date = [2026, 1, 1]
field = 0
page = "date"
games = []
game_index = 0
wlan = None
wifi_deadline = 0
error = ""


def days_in_month(year, month):
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    return 30 if month in (4, 6, 9, 11) else 31


def change_date(step):
    year, month, day = date
    if field == 0:
        year = max(FIRST_YEAR, min(LAST_YEAR, year + step))
    elif field == 1:
        month = (month - 1 + step) % 12 + 1
    else:
        day = (day - 1 + step) % days_in_month(year, month) + 1
    date[:] = [year, month, min(day, days_in_month(year, month))]


def date_key():
    return "%04d-%02d-%02d" % tuple(date)


def parse_games(payload, key):
    result = []
    for day in payload["dates"]:
        if day["date"] != key:
            continue
        for game in day["games"]:
            status = game["status"]
            teams = game["teams"]
            sides = []
            for name in ("away", "home"):
                team = teams[name]
                score = None if status["abstractGameState"] == "Preview" else team.get("score")
                sides.append((team["team"]["abbreviation"], "-" if score is None else str(score)))
            result.append((game["gameNumber"], status["detailedState"], sides))
    result.sort(key=lambda game: game[0])
    return result


def fetch_games(key):
    import requests

    response = requests.get(URL % key, timeout=REQUEST_TIMEOUT)
    try:
        if response.status_code != 200:
            raise OSError("MLB HTTP %d" % response.status_code)
        return parse_games(response.json(), key)
    finally:
        response.close()


def fail(message, cause=None):
    global page, error
    if cause is not None:
        print("Yankees Scores:", cause)
    error = message
    page = "error"


def start_lookup():
    global wlan, wifi_deadline, page, games, game_index
    games = []
    game_index = 0
    try:
        import network
    except ImportError:
        fail("Wi-Fi unavailable")
        return
    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        fail("Set Wi-Fi in Settings")
        return
    if not WIFI_SSID:
        fail("Set Wi-Fi in Settings")
        return

    try:
        if wlan is None:
            wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if wlan.ifconfig()[0] == "0.0.0.0":
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            wifi_deadline = time.ticks_add(time.ticks_ms(), WIFI_TIMEOUT_MS)
            page = "wifi"
        else:
            page = "fetch"
    except OSError as cause:
        fail("Wi-Fi connection failed", cause)


def panel(x, y, width, height, ink):
    screen.pen = ink
    screen.rectangle(x, y, width, height)


def centered(label, x, y, face, ink):
    screen.font = face
    screen.pen = ink
    width, _ = screen.measure_text(label)
    screen.text(label, x - width // 2, y)


def draw():
    w, h = screen.width, screen.height
    screen.pen = NAVY
    screen.rectangle(screen.clip)
    panel(0, 0, w, 4, RED)
    centered("NEW YORK YANKEES", w // 2, 15, font.futile, WHITE)
    centered("MLB SCOREBOARD", w // 2, 43, font.sins, MUTED)

    if page == "date":
        centered("Choose a game date", w // 2, 79, font.nope, WHITE)
        cell = (w - 32) // 3
        for i, label in enumerate(FIELDS):
            x = 16 + i * cell
            panel(x, 109, cell - 4, 69, PANEL)
            if i == field:
                panel(x, 109, cell - 4, 3, RED)
            center = x + (cell - 4) // 2
            centered(label, center, 122, font.sins, RED if i == field else MUTED)
            value = "%04d" % date[i] if i == 0 else "%02d" % date[i]
            centered(value, center, 144, font.futile, WHITE)
        centered("LEFT/RIGHT field   UP/DOWN value", w // 2, h - 43, font.sins, MUTED)
        footer = "SELECT  Get scores"
    else:
        centered(date_key(), w // 2, 68, font.nope, WHITE)
        if page == "results" and games:
            number, status, sides = games[game_index]
            for i, (team, score) in enumerate(sides):
                x = 16 if i == 0 else w // 2 + 3
                width = w // 2 - 19
                panel(x, 94, width, 76, PANEL)
                center = x + width // 2
                side = "AWAY" if i == 0 else "HOME"
                centered(side + "  " + team, center, 106, font.nope, RED if team == "NYY" else MUTED)
                centered(score, center, 135, font.futile, WHITE)
            centered(status, w // 2, 176, font.nope, WHITE)
            if len(games) > 1:
                centered("LEFT/RIGHT  Game %d  (%d of %d)" % (number, game_index + 1, len(games)),
                         w // 2, h - 43, font.sins, MUTED)
            footer = "BACK  Date     SELECT  Refresh"
        elif page in ("wifi", "fetch"):
            message = "Connecting to Wi-Fi..." if page == "wifi" else "Fetching MLB scores..."
            centered(message, w // 2, 125, font.nope, WHITE)
            footer = "BACK  Date"
        else:
            message = error if page == "error" else "No Yankees game on this date"
            centered(message, w // 2, 125, font.nope, WHITE)
            footer = "BACK  Date     SELECT  Retry" if page == "error" else "BACK  Date     SELECT  Refresh"
    centered(footer, w // 2, h - 21, font.sins, WHITE)


def update():
    global page, field, games, game_index
    if page != "date" and badge.pressed(BUTTON_BACK):
        page = "date"
    elif page == "wifi":
        try:
            if wlan.ifconfig()[0] != "0.0.0.0":
                page = "fetch"
            elif time.ticks_diff(time.ticks_ms(), wifi_deadline) >= 0:
                wlan.disconnect()
                fail("Wi-Fi timed out")
        except OSError as cause:
            fail("Wi-Fi connection failed", cause)
    elif page == "fetch":
        # The previous frame shows the loading state before the HTTPS call.
        try:
            games = fetch_games(date_key())
            page = "results"
        except ImportError as cause:
            fail("HTTPS unavailable", cause)
        except OSError as cause:
            fail("Could not reach MLB", cause)
        except (ValueError, KeyError, TypeError, AttributeError) as cause:
            fail("Invalid MLB response", cause)
    elif page == "date":
        if badge.pressed(BUTTON_LEFT):
            field = (field - 1) % len(FIELDS)
        elif badge.pressed(BUTTON_RIGHT):
            field = (field + 1) % len(FIELDS)
        if badge.pressed(BUTTON_UP):
            change_date(1)
        elif badge.pressed(BUTTON_DOWN):
            change_date(-1)
        if badge.pressed(BUTTON_SELECT):
            start_lookup()
    elif badge.pressed(BUTTON_SELECT):
        start_lookup()
    elif games:
        if badge.pressed(BUTTON_LEFT):
            game_index = (game_index - 1) % len(games)
        elif badge.pressed(BUTTON_RIGHT):
            game_index = (game_index + 1) % len(games)
    draw()


run(update)
