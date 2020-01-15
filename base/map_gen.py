import random
import tcod
from math import ceil
from numpy import array
from constants import (
    room_types,
    game_objects,
    game_jobs,
    interiorRect,
    HALL_WIDTH,
    LIMITED_ROOMS,
    map_width,
    map_height
)
from base.enums import ObjType
from base.map import Rect, Tile


def room_flip(rows, flip):
    # will be called while iterating over columns for each row
    # If less than or equal to 50, rotate 90 or 270
    # rooms are list or rows for each column
    # 90
    if flip < 25:
        if not rows[-1]:
            rows.pop(-1)
        row = rows[-1]
        val = row.pop(0)

    # -90
    elif flip < 50:
        if not rows[0]:
            rows.pop(0)
        row = rows[0]
        val = row.pop(-1)

    # 360
    elif flip < 75:
        row = rows.pop(-1)
        val = row.pop(-1)
        rows.insert(0, row)

    # As written (doesn't work)
    else:
        row = rows.pop(0)
        val = row.pop(0)
        rows.append(row)

    return val.strip(), rows


class MapGenerator():
    """
    Class Handling Map Generation and currently
    serves as the middleman between the GameInstance and the
    tiles themselves.
     - TODO: Besides housing the path_map, which could be moved, doesn't really
       make sense to have this class in use once the map's been generated
     - TODO: May make sense if multiple maps need to exist simultaneously.  Each
       could maintain their own tiles and reduce churn over expanding list of tiles
    """
    def __init__(self, game):
        self.game = game
        self.game.game_map = self
        self.tiles = []
        self.fov_map = None
        self.path_map = None
        self.interior = interiorRect

    def place_object(self, obj):
        # Places object in tile and updates path_map
        self.tiles[obj.x][obj.y].add_content(obj)
        if self.path_map:
            if self.tiles[obj.x][obj.y].blocked:
                self.path_map.cost[obj.x, obj.y] = 0
            else:
                self.path_map.cost[obj.x, obj.y] = 1

    def remove_object(self, obj):
        # Removes object in tile and updates path_map
        self.tiles[obj.x][obj.y].remove_content(obj)
        if self.path_map:
            if self.tiles[obj.x][obj.y].blocked:
                self.path_map.cost[obj.x, obj.y] = 0
            else:
                self.path_map.cost[obj.x, obj.y] = 1

    def get_tile(self, x, y):
        return self.tiles[x][y]

    def get_obj_tile(self, obj):
        return self.tiles[obj.x][obj.y]

    def get_adjacent_tiles(self, obj):
        adj_coords = self.tiles[obj.x][obj.y].adjacent()
        return [self.tiles[x[0]][x[1]] for x in adj_coords]

    def find_path(self, seeker, target):
        """
        Pathing to first empty adjacent tile of target. If none exist, None will be turned and the
        Coworker can try again next time around.
        """
        empty_tiles = list(filter(lambda x: not x.blocked, self.get_adjacent_tiles(target)))
        if not empty_tiles:
            return None

        path = self.path_map.get_path(seeker.x, seeker.y, empty_tiles[0].x, empty_tiles[0].y)
        return path

    def generate_map(self):
        self.tiles = [
            [Tile(x, y) for y in range(map_height)]
            for x in range(map_width)
        ]

        inside_tiles = self.interior.get_tiles()
        for x in range(map_width):
            for y in range(map_height):
                if (x, y) not in inside_tiles:
                    self.tiles[x][y].ttype = "grass"
                    obj = game_objects["~"]
                    self.game.create_object(x, y, obj)

        for coord in self.interior.edges():
            obj = game_objects["#"]
            self.game.create_object(coord[0], coord[1], obj)

        h_halls = []
        rooms = []
        num_rooms = 0

        x = self.interior.x1
        y = self.interior.y1

        building = True
        next_row = False
        while building:
            room_index = random.randrange(0, len(room_types))
            rtype = list(room_types)[room_index]

            w = len(room_types[rtype][0])
            h = len(room_types[rtype])

            flip = random.randint(0, 100)

            if flip < 50:
                if num_rooms != 0:
                    x += HALL_WIDTH
                new_room = Rect(x, y, h, w)
            else:
                if num_rooms != 0:
                    x += HALL_WIDTH
                new_room = Rect(x, y, w, h)

            failed = False
            if new_room.x2 > self.interior.x2:
                failed = True
                next_row = True

            if not failed:
                self.create_room(new_room, rtype, flip)
                rooms.append(new_room)
                num_rooms += 1

                if rtype in LIMITED_ROOMS:
                    del room_types[rtype]

                hall = Rect(new_room.x1, new_room.y2, new_room.w, HALL_WIDTH)

                if hall.y2 < self.interior.y2:
                    # create_hall(hall)
                    h_halls.append(hall)

                x = new_room.x2

            # Running through subsequent rows
            if next_row:
                next_row = False

                for hall in h_halls:
                    heights = []

                    diff_x = hall.w

                    while diff_x > 0:
                        max_x = hall.x2
                        if heights == []:
                            prev_x = hall.x1
                            diff_x = hall.w
                        else:
                            prev_x = rooms[-1].x2  # + 1

                        possible_rooms = self.room_fill(prev_x, hall.y2 + 1, diff_x)

                        if possible_rooms != []:
                            picked_index = random.randrange(0, len(possible_rooms))
                            picked_room = possible_rooms[picked_index]

                            self.create_room(picked_room[0], picked_room[1], picked_room[2])
                            rooms.append(picked_room[0])

                            heights.append(picked_room[0].y2)

                            diff_x = max_x - picked_room[0].x2

                        else:
                            break

                    if heights != []:
                        max_height = max(heights)
                        new_hall = Rect(hall.x1, max_height + 1, hall.w, HALL_WIDTH - 1)
                        if new_hall.y2 < self.interior.y2:
                            # create_hall(new_hall)
                            h_halls.append(new_hall)

                    building = False

        for room in rooms:
            self.place_doors(room)

        self.generate_coworkers()

    def generate_path_map(self):
        passable = []
        for x in range(len(self.tiles)):
            passable_y = []
            for y in range(len(self.tiles[x])):
                if self.tiles[x][y].blocked:
                    passable_y.append(0)
                else:
                    passable_y.append(1)
            passable.append(passable_y)
        passable = array(passable)
        self.path_map = tcod.path.AStar(passable)

    def generate_coworkers(self):
        # Generates Player and Coworks and assigned Terminals
        terminals = [x for x in self.game.world_objs[ObjType["appliance"]] if x.name == 'Terminal']

        player_terminal = terminals.pop(0)
        adj_tiles = [x for x in player_terminal.adjacent() if not x.blocked]

        player = self.game.create_coworker(adj_tiles[0].x, adj_tiles[0].y, creating_player=True)
        print("Creating Player")
        player_terminal.owner = self.game.player = player

        temp_count = min(len(terminals) / 2, 10)
        req_job_counts = {
            game_jobs[x]["name"]: ceil(temp_count * game_jobs[x].get("pop_percentage", 0))
            for x in game_jobs
        }
        if sum(req_job_counts.values()) > len(terminals):
            print(f"Too many jobs for {len(terminals)} terminals")

        for job in req_job_counts:
            for worker in range(req_job_counts[job]):
                try:
                    t = terminals.pop(0)
                except IndexError:
                    pass
                else:
                    adj_tiles = [x for x in t.adjacent() if not x.blocked]
                    x = adj_tiles[0].x
                    y = adj_tiles[0].y

                    coworker = self.game.create_coworker(x, y, job=job)
                    t.owner = coworker

    def create_room(self, room, rtype, flip):

        rows = [list(r) for r in room_types[rtype]]
        print(rtype, flip)
        print([x for x in range(room.x1, room.x2 + 1)])
        print([x for x in range(room.y1, room.y2 + 1)])
        for x in range(room.x1, room.x2 + 1):
            for y in range(room.y1, room.y2 + 1):
                try:
                    val, rows = room_flip(rows, flip)
                except IndexError:
                    val = None

                if not val:
                    continue

                elif val == "~":
                    self.get_tile(x, y).ttype = "grass"
                    obj = game_objects[val]
                    self.game.create_object(x, y, obj)
                elif val == "M" and "bath" in rtype:
                    obj = game_objects["Mens"]
                    self.game.create_object(x, y, obj)
                elif val == "W" and "bath" in rtype:
                    obj = game_objects["Womens"]
                    self.game.create_object(x, y, obj)
                else:
                    obj = game_objects[val]
                    self.game.create_object(x, y, obj)
        print(f"Created Room => x: {room.x1} y: {room.y1} w: {room.w} h: {room.h} x2: {room.x2} y2: {room.y2}")

    def place_doors(self, room):
        # Placing Doors
        possible_doors = []
        # TODO:  Redo this business and drop ttype altogether
        for x in range(room.x1 + 1, room.x2):
            if (
                not self.tiles[x][room.y1 + 1].blocked
                and not self.tiles[x][room.y1 - 1].blocked
                and self.tiles[x][room.y1 + 1].ttype != "grass"
                and self.tiles[x][room.y1 - 1].ttype != "grass"
            ):
                possible_doors.append((x, room.y1))

            if (
                not self.tiles[x][room.y2 + 1].blocked
                and not self.tiles[x][room.y2 - 1].blocked
                and self.tiles[x][room.y2 + 1].ttype != "grass"
                and self.tiles[x][room.y2 - 1].ttype != "grass"
            ):
                possible_doors.append((x, room.y2))

        for y in range(room.y1 + 1, room.y2):
            if (
                not self.tiles[room.x1 + 1][y].blocked
                and not self.tiles[room.x1 - 1][y].blocked
                and self.tiles[room.x1 - 1][y].ttype != "grass"
                and self.tiles[room.x1 + 1][y].ttype != "grass"
            ):
                possible_doors.append((room.x1, y))

            if (
                not self.tiles[room.x2 + 1][y].blocked
                and not self.tiles[room.x2 - 1][y].blocked
                and self.tiles[room.x2 - 1][y].ttype != "grass"
                and self.tiles[room.x2 + 1][y].ttype != "grass"
            ):
                possible_doors.append((room.x2, y))

        if not possible_doors:
            print("Room with No doors...")
            return None

        door_index_a = random.randrange(0, len(possible_doors))
        door_index_b = random.randrange(0, len(possible_doors))
        if possible_doors != []:
            x = possible_doors[door_index_a][0]
            y = possible_doors[door_index_a][1]
            obj = game_objects["+"]

            # Removing wall prior to door placement
            door_tile = self.game.get_tile(x, y)
            walls = [x for x in door_tile.contents if x.name == "Wall"]
            if walls:
                self.game.delete_object(walls[0])
            self.game.create_object(x, y, obj)

            x = possible_doors[door_index_b][0]
            y = possible_doors[door_index_b][1]
            door_tile = self.game.get_tile(x, y)
            walls = [x for x in door_tile.contents if x.name == "Wall"]
            if walls:
                self.game.delete_object(walls[0])
            self.game.create_object(x, y, obj)

    def create_hall(self, hall):
        for x in range(hall.x1, hall.x2 + 1):
            for y in range(hall.y1, hall.y2 + 1):
                self.tiles[x][y].blocked = False
                self.tiles[x][y].block_sight = False

    def room_fill(self, x, y, max_w):
        possible_rooms = []
        for r in room_types:
            w = len(room_types[r][0])
            h = len(room_types[r])

            if w > max_w and h > max_w:
                continue
            elif w > max_w and h <= max_w:
                new_room = Rect(x, y, h, w)
                if new_room.y2 < self.interior.y2:
                    flip = random.randint(0, 50)
                    possible_rooms.append((new_room, r, flip, "man_rotate"))
            elif w <= max_w and h > max_w:
                new_room = Rect(x, y, w, h)
                if new_room.y2 < self.interior.y2:
                    flip = random.randint(50, 100)
                    possible_rooms.append((new_room, r, flip, "man_nat"))
            else:
                flip = random.randint(0, 100)
                if flip < 50:
                    new_room = Rect(x, y, h, w)
                    if new_room.y2 < self.interior.y2:
                        possible_rooms.append((new_room, r, flip, "auto_rotate"))
                else:
                    new_room = Rect(x, y, w, h)
                    if new_room.y2 < self.interior.y2:
                        possible_rooms.append((new_room, r, flip, "auto_nat"))

        return possible_rooms
