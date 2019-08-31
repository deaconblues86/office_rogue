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

colors = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "yellow": tcod.yellow,
    "dark_yellow": tcod.dark_yellow,
    "orange": tcod.orange,
    "pink": tcod.pink,
    "light_sepia": tcod.light_sepia,
    "blue": tcod.blue,
    "light_blue": tcod.light_blue,
    "light_green": tcod.light_green,
}

room_types = {}
with open("defs/rooms.txt") as room_file:
    for line in room_file:
        line = line.strip().split("\t")

        if len(line) == 1:
            if line == [""]:
                continue
            r = line[0]
            room_types[r] = []
        else:
            room_types[r].append(line)

with open("defs/objects.json") as obj_file:
    game_objects = json.loads(obj_file.read())

with open('defs/female_names.txt') as names:
    female_names = [n.strip() for n in names.readlines()]

with open('defs/male_names.txt') as names:
    male_names = [n.strip() for n in names.readlines()]


MAX_INVENTORY = 4
