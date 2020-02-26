import json
import tcod
from collections import defaultdict
from base.map import Rect

ROOM_SECTOR_X = 18
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
screen_width = map_width + 16
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

with open("defs/colors.json") as colors_file:
    colors = json.loads(colors_file.read())

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

with open("defs/jobs.json") as obj_file:
    game_jobs = json.loads(obj_file.read())

with open("defs/requests.json") as req_file:
    work_requests = json.loads(req_file.read())

with open("defs/actions.json") as obj_file:
    game_actions = json.loads(obj_file.read())
    actions_by_need = defaultdict(list)
    for action in game_actions:
        actions_by_need[action["satisfies"]].append(action)

with open("defs/emissions.json") as emit_file:
    game_auras = json.loads(emit_file.read())

with open('defs/female_names.txt') as names:
    female_names = [n.strip() for n in names.readlines()]

with open('defs/male_names.txt') as names:
    male_names = [n.strip() for n in names.readlines()]


MAX_INVENTORY = 4
