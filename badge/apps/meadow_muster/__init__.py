"""Herd skittish meadow critters into a pen before the bell."""

import math
import os
import random
import sys

from badgeware import State

APP_DIR = "/system/apps/meadow_muster"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

badge.mode(HIRES | VSYNC)
screen.fill_rule = image.EVEN_ODD
W, H = screen.width, screen.height
MID = W // 2
TOP, FENCE, EDGE = 39, H - 56, 14
GATE_LEFT, GATE_RIGHT = MID - 39, MID + 39
EXIT_TOP, EXIT_BOTTOM = 88, 140
RADIUS = 7
REPEL = 44

DARK = color.rgb(19, 43, 41)
GRASS = color.rgb(62, 120, 78)
MOWN = color.rgb(68, 130, 84)
PEN = color.rgb(40, 84, 64)
CREAM = color.rgb(255, 244, 202)
GOLD = color.rgb(255, 205, 97)
FENCE_INK = color.rgb(173, 125, 79)
CORAL = color.rgb(255, 155, 135)
FLOCK = (color.rgb(245, 169, 102), color.rgb(202, 180, 251),
         color.rgb(122, 224, 214), color.rgb(253, 207, 123))

record = {"best": 0}
State.load("meadow_muster", record)


def clamp(value, low, high):
    return max(low, min(high, value))


class Critter:
    def __init__(self, x, y, kind):
        self.x, self.y, self.kind = x, y, kind
        self.phase = random.random() * 6.28
        self.vx = self.vy = 0.0
        self.status = "field"

    def tick(self, dt, sx, sy, speed):
        self.phase += dt * (1.7 + 0.2 * self.kind)
        dx, dy = self.x - sx, self.y - sy
        distance = math.sqrt(dx * dx + dy * dy)
        if distance < REPEL:
            if distance < 0.1:
                dx, dy, distance = 0, 1, 1
            pace = speed * (1.0 - 0.55 * distance / REPEL)
            tx, ty = dx * pace / distance, dy * pace / distance
        else:
            tx = 10 * math.cos(self.phase)
            ty = 10 * math.sin(self.phase)
        self.vx += (tx - self.vx) * min(1, dt * 12)
        self.vy += (ty - self.vy) * min(1, dt * 12)
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y < TOP + RADIUS:
            self.y, self.vy = TOP + RADIUS, max(0, self.vy)
        if EXIT_TOP + RADIUS < self.y < EXIT_BOTTOM - RADIUS:
            if self.x < -RADIUS or self.x > W + RADIUS:
                self.status = "escaped"
                return
        else:
            self.x = clamp(self.x, EDGE + RADIUS, W - EDGE - RADIUS)

        if self.y >= FENCE - RADIUS:
            if GATE_LEFT + RADIUS <= self.x <= GATE_RIGHT - RADIUS:
                if self.y >= FENCE + RADIUS:
                    self.status = "penned"
            else:
                self.y, self.vy = FENCE - RADIUS, min(0, self.vy)


class Round:
    def __init__(self, wave):
        self.wave = wave
        count = min(12, 4 + wave)
        self.goal = (count + 1) // 2
        self.critters = [
            Critter(37 + (i % 6) * ((W - 84) // 5) + random.randint(-5, 5),
                    88 + (i // 6) * 46 + random.randint(-9, 9), i % len(FLOCK))
            for i in range(count)
        ]
        self.sx, self.sy = MID, TOP + 16
        self.time = float(max(24, 42 - wave * 2))
        self.penned = self.escaped = 0

    def tick(self, dt, mx, my):
        pace = 132 * (0.7071 if mx and my else 1)
        self.sx = clamp(self.sx + pace * mx * dt, EDGE + 2, W - EDGE - 2)
        self.sy = clamp(self.sy + pace * my * dt, TOP + 2, FENCE - 3)
        self.time = max(0, self.time - dt)
        speed = min(108, 65 + self.wave * 5)
        for critter in self.critters:
            if critter.status != "field":
                continue
            critter.tick(dt, self.sx, self.sy, speed)
            if critter.status == "penned":
                self.penned += 1
            elif critter.status == "escaped":
                self.escaped += 1
        if self.time == 0 or self.penned + self.escaped == len(self.critters):
            return "clear" if self.penned >= self.goal else "over"
        return "play"


stage = Round(1)
score = 0
page = "title"


def box(x, y, w, h, ink):
    screen.pen = ink
    screen.rectangle(x, y, w, h)


def disk(x, y, radius, ink):
    screen.pen = ink
    screen.circle(vec2(x, y), radius)


def label(text, x, y, face, ink, centered=False):
    screen.font = face
    screen.pen = ink
    if centered:
        width, _ = screen.measure_text(text)
        x -= width // 2
    screen.text(text, x, y)


def draw_critter(x, y, kind):
    ink = FLOCK[kind]
    disk(x, y + 3, 8, PEN)
    disk(x - 4, y - 5, 4, ink)
    disk(x + 4, y - 5, 4, ink)
    disk(x, y, RADIUS, ink)
    disk(x - 2, y, 1, DARK)
    disk(x + 3, y, 1, DARK)


def draw_field():
    box(0, 0, W, H, GRASS)
    for y in range(TOP, H, 25):
        box(0, y, W, 11, MOWN)
    for x, y in ((44, 65), (85, 145), (114, 66), (216, 113), (278, 64), (281, 156)):
        disk(x, y, 2, CREAM)
        disk(x + 5, y + 4, 1, GOLD)

    for x in (EDGE - 3, W - EDGE):
        box(x, TOP, 3, EXIT_TOP - TOP, FENCE_INK)
        box(x, EXIT_BOTTOM, 3, FENCE - EXIT_BOTTOM, FENCE_INK)
    for x, marker in ((11, "<"), (W - 11, ">")):
        label(marker, x, (EXIT_TOP + EXIT_BOTTOM) // 2 - 7, font.nope, CORAL, True)

    box(GATE_LEFT, FENCE, GATE_RIGHT - GATE_LEFT, H - FENCE - 7, PEN)
    box(0, FENCE, GATE_LEFT, 4, FENCE_INK)
    box(GATE_RIGHT, FENCE, W - GATE_RIGHT, 4, FENCE_INK)
    box(GATE_LEFT - 3, FENCE, 3, H - FENCE - 5, FENCE_INK)
    box(GATE_RIGHT, FENCE, 3, H - FENCE - 5, FENCE_INK)
    box(GATE_LEFT, H - 8, GATE_RIGHT - GATE_LEFT, 3, FENCE_INK)
    label("PEN", MID, FENCE + 4, font.sins, GOLD, True)
    penned = 0
    for critter in stage.critters:
        if critter.status == "field":
            draw_critter(int(critter.x), int(critter.y), critter.kind)
        elif critter.status == "penned":
            disk(GATE_LEFT + 12 + penned % 6 * 11, FENCE + 23 + penned // 6 * 12,
                 4, FLOCK[critter.kind])
            penned += 1

    x, y = int(stage.sx), int(stage.sy)
    disk(x, y, 10, DARK)
    disk(x, y, 7, CREAM)
    box(x - 3, y + 3, 7, 3, CORAL)
    disk(x + 2, y - 2, 1, DARK)

    box(0, 0, W, TOP, DARK)
    label("ROUND %d" % stage.wave, 10, 7, font.nope, CREAM)
    label("PENNED %d/%d" % (stage.penned, stage.goal), MID, 7, font.nope, GOLD, True)
    label("%ds" % math.ceil(stage.time), W - 41, 7, font.nope,
          CORAL if stage.time < 8 else CREAM)
    label("SCORE %d" % score, 10, 24, font.sins, CREAM)
    label("ESCAPED %d" % stage.escaped, W - 76, 24, font.sins, CORAL)


def draw_card():
    box(26, 54, W - 52, 133, DARK)
    box(26, 54, W - 52, 3, GOLD)
    if page == "title":
        title, action = "MEADOW MUSTER", "SELECT TO START"
        first, second = "D-pad: move the shepherd", "Guide critters into the bottom pen"
    elif page == "pause":
        title, action = "PAUSED", "SELECT TO RESUME"
        first, second = "MENU also resumes", "BACK returns to title"
    elif page == "clear":
        title, action = "ROUND CLEAR", "SELECT FOR NEXT ROUND"
        first = "%d penned  /  %d escaped" % (stage.penned, stage.escaped)
        second = "SCORE %d" % score
    else:
        title, action = "ROUND OVER", "SELECT TO TRY AGAIN"
        first = "%d penned  /  %d needed" % (stage.penned, stage.goal)
        second = "SCORE %d  /  BEST %d" % (score, record["best"])
    label(title, MID, 66, font.futile, GOLD, True)
    label(first, MID, 109, font.nope, CREAM, True)
    label(second, MID, 129, font.nope, CREAM, True)
    label(action, MID, 159, font.nope, GOLD, True)


def update():
    global stage, score, page
    select = badge.pressed(BUTTON_SELECT)
    menu = badge.pressed(BUTTON_MENU)
    if page == "play":
        if menu:
            page = "pause"
        else:
            mx = int(badge.held(BUTTON_RIGHT)) - int(badge.held(BUTTON_LEFT))
            my = int(badge.held(BUTTON_DOWN)) - int(badge.held(BUTTON_UP))
            page = stage.tick(min(50, badge.ticks_delta) / 1000, mx, my)
            if page != "play":
                score += stage.penned * 100
                if page == "clear":
                    score += int(stage.time) * 10
                if score > record["best"]:
                    record["best"] = score
                    State.save("meadow_muster", record)
    elif page == "pause":
        if badge.pressed(BUTTON_BACK):
            page = "title"
            stage, score = Round(1), 0
        elif select or menu:
            page = "play"
    elif select:
        if page == "clear":
            stage = Round(stage.wave + 1)
        else:
            stage, score = Round(1), 0
        page = "play"

    draw_field()
    if page != "play":
        draw_card()


run(update)
