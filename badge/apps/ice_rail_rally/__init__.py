"""An original downhill mine-cart stunt game."""

import math
import os
import sys

from badgeware import State

APP_DIR = "/system/apps/ice_rail_rally"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

badge.mode(HIRES | VSYNC)
screen.fill_rule = image.EVEN_ODD
W, H = screen.width, screen.height
MID = W // 2
HORIZON = 68
JUMP_TIME = 0.72
BENDS = (-1, 1, 1, -1, 1, -1, -1, 1)

DARK = color.rgb(13, 22, 38)
ROCK = color.rgb(26, 43, 61)
FACET = color.rgb(35, 57, 78)
TRACK = color.rgb(41, 47, 62)
TIE = color.rgb(113, 83, 75)
STEEL = color.rgb(164, 194, 214)
ICE = color.rgb(95, 233, 236)
WHITE = color.rgb(242, 251, 255)
GOLD = color.rgb(255, 197, 88)
CORAL = color.rgb(255, 121, 106)

record = {"best": 0}
State.load("ice_rail_rally", record)


class Ride:
    def __init__(self):
        self.distance = 0.0
        self.bonus = 0
        self.carts = 3
        self.bend = 0
        self.next_bend = 110
        self.air = 0.0
        self.stunt = ""
        self.last_stunt = ""
        self.chain = 0
        self.message = ""
        self.flash = 0.0
        self.lean = 0
        self.grinding = False

    def score(self):
        return int(self.distance + self.bonus)

    def direction(self):
        return BENDS[self.bend % len(BENDS)]

    def tick(self, dt, lean, jump, up, down, spin):
        self.flash = max(0, self.flash - dt)
        self.lean = lean
        self.grinding = False
        if jump and not self.air:
            self.air = JUMP_TIME
            self.stunt = ""
        if self.air:
            if not self.stunt:
                self.stunt = "FLIP" if up else "SPIN" if spin else ""
            self.air = max(0, self.air - dt)
            if not self.air and self.stunt:
                if self.stunt != self.last_stunt:
                    self.chain = min(5, self.chain + 1)
                    points = (100 if self.stunt == "FLIP" else 80) * self.chain
                    self.bonus += points
                    self.message = "%s +%d  x%d" % (self.stunt, points, self.chain)
                else:
                    self.chain = 0
                    self.message = "MIX UP YOUR STUNTS"
                self.last_stunt = self.stunt
                self.flash = 0.95
        elif down and not lean:
            self.bonus += dt * 30
            self.grinding = True

        speed = min(57, 30 + self.bend * 2)
        self.distance += speed * dt
        if self.distance >= self.next_bend:
            if lean == self.direction() and not self.air:
                self.bonus += 50
                self.message = "CLEAN TURN +50"
            else:
                self.carts -= 1
                self.chain = 0
                self.last_stunt = ""
                self.air = 0.0
                self.message = "DERAILED!"
            self.flash = 0.95
            self.bend += 1
            self.next_bend += 90 + (self.bend % 3) * 9


ride = Ride()
page = "title"


def box(x, y, width, height, ink):
    screen.pen = ink
    screen.rectangle(x, y, width, height)


def line(x1, y1, x2, y2, ink):
    screen.pen = ink
    screen.line(x1, y1, x2, y2)


def polygon(points, ink):
    screen.pen = ink
    screen.shape(shape.custom([vec2(x, y) for x, y in points]))


def disk(x, y, radius, ink):
    screen.pen = ink
    screen.circle(vec2(x, y), radius)


def label(text, x, y, face, ink, center=False):
    screen.font = face
    screen.pen = ink
    if center:
        width, _ = screen.measure_text(text)
        x -= width // 2
    screen.text(text, x, y)


def track_edges(depth, curve):
    center = MID + int(curve * (1 - depth) ** 2)
    spread = 10 + int(depth * 96)
    return center - spread, center + spread, HORIZON + int(depth * (H - HORIZON))


def draw_tunnel():
    remaining = ride.next_bend - ride.distance
    curve = ride.direction() * int(72 * max(0, 1 - remaining / 75))
    box(0, 0, W, H, ROCK)
    polygon(((0, 37), (MID, HORIZON), (0, 162)), FACET)
    polygon(((W, 36), (MID, HORIZON), (W, 157)), FACET)
    for x, y, lean in ((16, 117, 1), (48, 86, 1), (W - 25, 117, -1), (W - 61, 93, -1)):
        polygon(((x, y + 16), (x + lean * 2, y - 16), (x + lean * 14, y + 10)), ICE)
        line(x + lean * 2, y - 10, x + lean * 5, y + 10, WHITE)
    left, right, y = track_edges(0, curve)
    polygon(((left, y), (right, y), (MID + 113, H), (MID - 113, H)), TRACK)

    for i in range(10):
        depth = ((i + (ride.distance % 8) / 8) / 10) ** 2
        left, right, y = track_edges(depth, curve)
        box(left - 4, y, right - left + 8, 1 + int(depth * 5), TIE)
    left, right, y = track_edges(0, curve)
    for i in range(1, 11):
        next_left, next_right, next_y = track_edges(i / 10, curve)
        line(left, y, next_left, next_y, STEEL)
        line(right, y, next_right, next_y, STEEL)
        line(left + 1, y, next_left + 1, next_y, WHITE)
        line(right - 1, y, next_right - 1, next_y, WHITE)
        left, right, y = next_left, next_right, next_y


def draw_cart():
    flight = ride.air / JUMP_TIME
    lift = int(45 * math.sin(math.pi * flight))
    x, y = MID + ride.lean * 13, H - 31 - lift
    lean = ride.lean * 5
    if ride.grinding:
        for i in range(3):
            offset = int(ride.distance * 2 + i * 7) % 18
            line(x - 15 - offset, y + 9 + i * 3, x - 19 - offset, y + 12 + i * 3, GOLD)
            line(x + 15 + offset, y + 9 + i * 3, x + 19 + offset, y + 12 + i * 3, GOLD)
    if ride.air and ride.stunt == "SPIN":
        lean = int(12 * math.sin(2 * math.pi * flight))
    head_y = y - 36
    if ride.air and ride.stunt == "FLIP":
        head_y += int(22 * math.sin(math.pi * flight))
    disk(x - 15, y + 8, 6, DARK)
    disk(x + 15, y + 8, 6, DARK)
    disk(x + lean, y - 21, 14, WHITE)
    disk(x + lean, head_y, 12, DARK)
    disk(x + lean - 4, head_y - 1, 3, WHITE)
    disk(x + lean + 4, head_y - 1, 3, WHITE)
    polygon(((x + lean - 4, head_y + 3), (x + lean + 4, head_y + 3),
             (x + lean, head_y + 8)), GOLD)
    box(x + lean - 12, y - 25, 24, 4, ICE)
    polygon(((x - 26, y - 13 + lean), (x + 26, y - 13 - lean),
             (x + 19, y + 7), (x - 19, y + 7)), GOLD)
    line(x - 21, y - 9 + lean, x + 21, y - 9 - lean, WHITE)


def draw_run():
    draw_tunnel()
    draw_cart()
    box(0, 0, W, 28, DARK)
    label("SCORE %05d" % ride.score(), 10, 7, font.nope, WHITE)
    label("CARTS %d" % ride.carts, W - 69, 7, font.nope, GOLD)
    remaining = ride.next_bend - ride.distance
    if remaining < 55:
        box(MID - 59, 37, 118, 24, DARK)
        side = "LEFT" if ride.direction() < 0 else "RIGHT"
        urgent = remaining < 20
        label(("HOLD " if urgent else "BEND ") + side, MID, 42,
              font.nope, GOLD if urgent else ICE, True)
    if ride.flash:
        label(ride.message, MID, H - 16, font.nope, WHITE, True)
    elif ride.grinding:
        label("GRINDING", MID, H - 16, font.nope, ICE, True)


def draw_card():
    box(22, 36, W - 44, H - 70, DARK)
    box(22, 36, W - 44, 3, ICE)
    if page == "title":
        label("ICE RAIL RALLY", MID, 53, font.futile, ICE, True)
        label("Hold LEFT / RIGHT through bends", MID, 92, font.nope, WHITE, True)
        label("SELECT jump   DOWN grind", MID, 113, font.nope, WHITE, True)
        label("In air: UP flip   LEFT / RIGHT spin", MID, 134, font.nope, WHITE, True)
        label("SELECT TO RIDE", MID, 174, font.nope, GOLD, True)
    elif page == "pause":
        label("PAUSED", MID, 69, font.futile, ICE, True)
        label("MENU or SELECT to resume", MID, 121, font.nope, WHITE, True)
        label("BACK to title", MID, 150, font.nope, GOLD, True)
    else:
        label("END OF THE LINE", MID, 65, font.futile, ICE, True)
        label("SCORE %d    BEST %d" % (ride.score(), record["best"]),
              MID, 117, font.nope, WHITE, True)
        label("SELECT TO RIDE AGAIN", MID, 158, font.nope, GOLD, True)


def update():
    global page, ride
    select = badge.pressed(BUTTON_SELECT)
    menu = badge.pressed(BUTTON_MENU)
    if page == "pause":
        if badge.pressed(BUTTON_BACK):
            page = "title"
            ride = Ride()
        elif menu or select:
            page = "ride"
    elif page != "ride":
        if select:
            ride = Ride()
            page = "ride"
    elif menu:
        page = "pause"
    else:
        lean = int(badge.held(BUTTON_RIGHT)) - int(badge.held(BUTTON_LEFT))
        spin = badge.pressed(BUTTON_LEFT) or badge.pressed(BUTTON_RIGHT)
        ride.tick(min(badge.ticks_delta, 50) / 1000, lean, select,
                  badge.pressed(BUTTON_UP), badge.held(BUTTON_DOWN), spin)
        if not ride.carts:
            page = "over"
            if ride.score() > record["best"]:
                record["best"] = ride.score()
                State.save("ice_rail_rally", record)

    draw_run()
    if page != "ride":
        draw_card()


run(update)
