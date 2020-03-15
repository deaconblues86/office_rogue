import json
from collections import defaultdict


REQUIRED_OBJECTS = {"Terminal": 5, "Toilet": 1, "Coffee Maker": 1, "Vending Machine": 1}
LIMITED_ROOMS = ["manager", "patio"]

# TODO: Depending on how big map can get, may have reasses player movement
SCREEN_WIDTH = 105
SCREEN_HEIGHT = 62
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
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2

# Max lines of message history to keep
MAX_HISTORY = 50

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

with open("defs/jobs.json") as job_file:
    game_jobs = json.loads(job_file.read())

with open("defs/requests.json") as req_file:
    work_requests = json.loads(req_file.read())

with open("defs/actions.json") as action_file:
    game_actions = json.loads(action_file.read())
    actions_by_need = defaultdict(list)
    for action in game_actions:
        action_params = game_actions[action]
        for satisfaction in action_params.get("satisfies", []):
            actions_by_need[satisfaction].append(action_params)

with open("defs/states.json") as state_file:
    game_states = json.loads(state_file.read())

with open("defs/emissions.json") as emit_file:
    game_auras = json.loads(emit_file.read())

with open('defs/female_names.txt') as names:
    female_names = [n.strip() for n in names.readlines()]

with open('defs/male_names.txt') as names:
    male_names = [n.strip() for n in names.readlines()]


MAX_INVENTORY = 4
