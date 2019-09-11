import json
import tcod
from base.map import Rect

ROOM_SECTOR_X = 22
ROOM_SECTOR_Y = 22
HALL_WIDTH = 3
OUTSIDE_BORDER = 4

TURN_COUNT = 0

MAX_ROOMS = 4
MAP_WIDTH = 0
MAP_HEIGHT = 0

LIMITED_ROOMS = ['manager', 'patio']
COWORKERS = []

# Defining Building Space
interior_x = int(MAX_ROOMS * (ROOM_SECTOR_X + HALL_WIDTH)) - HALL_WIDTH
interior_y = int((MAX_ROOMS / 2) * (ROOM_SECTOR_Y + HALL_WIDTH)) - HALL_WIDTH

interiorRect = Rect(OUTSIDE_BORDER, OUTSIDE_BORDER, interior_x, interior_y)

# Adding Outdoor Space
map_width = interior_x + (OUTSIDE_BORDER * 2)
map_height = interior_y + (OUTSIDE_BORDER * 2)

# Adding Padding to Screen to allow for UI
screen_width = map_width + 10
screen_height = map_height + 7

BAR_WIDTH = 20
STATS = [
    ("work", "green"),
    ("mood", "orange"),
    ("social", "yellow"),
    ("energy", "violet"),
    ("hunger", "red"),
    ("thirst", "blue"),
    ("bladder", "grey"),
    ("bowels", "sepia")
]

MSG_HEIGHT = 6
msg_width = screen_width - BAR_WIDTH - 2

colors = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "light_grey": tcod.light_grey,
    "dark_grey": tcod.dark_grey,
    "light_sepia": tcod.light_sepia,
    "dark_sepia": tcod.dark_sepia,
    "pink": tcod.pink,
    "light_red": tcod.light_red,
    "dark_red": tcod.dark_red,
    "orange": tcod.orange,
    "light_orange": tcod.dark_orange,
    "dark_orange": tcod.dark_orange,
    "yellow": tcod.yellow,
    "light_yellow": tcod.yellow,
    "dark_yellow": tcod.dark_yellow,
    "light_green": tcod.light_green,
    "dark_green": tcod.dark_green,
    "blue": tcod.blue,
    "light_blue": tcod.light_blue,
    "dark_blue": tcod.dark_blue,
    "light_violet": tcod.light_violet,
    "dark_violet": tcod.dark_violet,
}

room_types = {}
with open("defs/rooms.txt") as room_file:
    for line in room_file:
        line = line.strip()
        if not line:
            continue

        if line[:2] == "--":
            r = line
            room_types[r] = []
        else:
            line = list(line)
            room_types[r].append(line)

with open("defs/objects.json") as obj_file:
    game_objects = json.loads(obj_file.read())

with open('defs/female_names.txt') as names:
    female_names = [n.strip() for n in names.readlines()]

with open('defs/male_names.txt') as names:
    male_names = [n.strip() for n in names.readlines()]


MAX_INVENTORY = 4
