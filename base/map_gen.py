import random
import tcod
from math import ceil
from numpy import array
from functools import reduce
from constants import (
    room_types,
    game_objects,
    game_jobs,
    LIMITED_ROOMS,
    REQUIRED_OBJECTS,
)
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
    outside_border = 4
    hall_width = 3
    interior_x = 81
    interior_y = 47

    # Adding Outdoor Space
    map_width = interior_x + (outside_border * 2)
    map_height = interior_y + (outside_border * 2)

    def __init__(self, game):
        self.game = game
        self.game.game_map = self
        self.tiles = []
        self.rooms = []
        self.fov_map = None
        self.path_map = None
        self.interior = Rect(self, self.outside_border, self.outside_border, self.interior_x, self.interior_y)

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
            [Tile(x, y) for y in range(self.map_height)]
            for x in range(self.map_width)
        ]

        inside_tiles = self.interior.get_tile_coords()
        for x in range(self.map_width):
            for y in range(self.map_height):
                if (x, y) not in inside_tiles:
                    obj = game_objects["~"]
                    self.game.create_object(x, y, obj)

        success = False
        while not success:
            self.delete_rooms()
            success = self.generate_rooms(room_types)

        # Fill in any holes in exterior walls after creating rooms:
        for coord in filter(
            lambda x: "Wall" not in [x.name for x in self.get_tile(*x).contents], self.interior.edges()
        ):
            obj = game_objects["#"]
            self.game.create_object(coord[0], coord[1], obj)

        for room in self.rooms:
            self.place_doors(room)

        # Generating path_map prior to coworkers (since they'll be moving)
        self.generate_path_map()
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
        terminals = self.game.find_objs("Terminal")

        player_terminal = terminals.pop(0)
        adj_tiles = [x for x in self.get_adjacent_tiles(player_terminal) if not x.blocked]

        player = self.game.create_coworker(adj_tiles[0].x, adj_tiles[0].y, creating_player=True)
        player_terminal.owner = self.game.player = player

        temp_count = min(len(terminals) / 2, 10)
        req_job_counts = {
            game_jobs[x]["name"]: ceil(temp_count * game_jobs[x].get("pop_percentage", 0))
            for x in game_jobs
        }
        print(req_job_counts)
        for job in req_job_counts:
            for worker in range(req_job_counts[job]):
                try:
                    t = terminals.pop(0)
                except IndexError:
                    print(f"Ran out of terminals for {job}")

                adj_tiles = [x for x in self.get_adjacent_tiles(t) if not x.blocked]
                x = adj_tiles[0].x
                y = adj_tiles[0].y

                coworker = self.game.create_coworker(x, y, job=job)
                t.owner = coworker

    def delete_rooms(self):
        for x in self.rooms:
            for obj in x.get_contents():
                self.game.remove_tile_content(obj)

        self.rooms = []

    def generate_rooms(self, room_types):
        room_names = list(room_types)
        x = self.interior.x1
        y = self.interior.y1
        max_row_height = 0

        while True:
            # If we've moved beyond the interior space or have exhausted all rooms trying to fit more in
            # time to break out
            if y > self.interior.y2 or not room_names:
                break

            room_index = random.randrange(0, len(room_names))
            rtype = room_names[room_index]

            w = len(room_types[rtype][0])
            h = len(room_types[rtype])

            flip = random.randint(0, 100)

            if flip < 50:
                new_room = Rect(self, x, y, h, w, name=rtype)
            else:
                new_room = Rect(self, x, y, w, h, name=rtype)

            # If the rooms have moved beyond the interior space, go to next row
            # Reset X coord and reposition Y
            if new_room.x2 > self.interior.x2:
                x = self.interior.x1
                y += max_row_height + self.hall_width
                max_row_height = 0
                continue

            # If Y's too great, pop it from list cause it'll never fit again
            # and try again
            elif new_room.y2 > self.interior.y2:
                room_names.pop(room_index)
                continue

            max_row_height = max(max_row_height, new_room.h)
            self.rooms.append(new_room)
            self.create_room(new_room, rtype, flip)

            if rtype in LIMITED_ROOMS:
                room_names.pop(room_index)

            x = new_room.x2 + self.hall_width + 1

        # Verify that generated rooms are playable based on min number of required objects
        contents = reduce(lambda x, y: x + y, [x.get_contents() for x in self.rooms], [])
        contents_by_name = [c.name for c in contents if c.name not in ("Wall", "Grass")]
        if any(count > contents_by_name.count(name) for name, count in REQUIRED_OBJECTS.items()):
            return False

        return True

    def create_room(self, room, rtype, flip):

        rows = [list(r) for r in room_types[rtype]]
        for x in range(room.x1, room.x2 + 1):
            for y in range(room.y1, room.y2 + 1):
                try:
                    val, rows = room_flip(rows, flip)
                except IndexError:
                    val = None

                if not val:
                    continue

                elif val == "M" and "bath" in rtype:
                    obj = game_objects["Mens"]
                    self.game.create_object(x, y, obj)
                elif val == "W" and "bath" in rtype:
                    obj = game_objects["Womens"]
                    self.game.create_object(x, y, obj)
                else:
                    obj = game_objects[val]
                    self.game.create_object(x, y, obj)

        # print(f"Creating Room => {room}")

    def place_doors(self, room):
        # Placing Doors
        possible_doors = []
        exterior_wall_coords = self.interior.edges()
        for x in range(room.x1, room.x2 + 1):
            for y_coord in (room.y1, room.y2):
                if (
                    not self.tiles[x][y_coord + 1].blocked
                    and not self.tiles[x][y_coord - 1].blocked
                ):
                    possible_doors.append((x, y_coord))

        for y in range(room.y1, room.y2 + 1):
            for x_coord in (room.x1, room.x2):
                if (
                    not self.tiles[x_coord + 1][y].blocked
                    and not self.tiles[x_coord - 1][y].blocked
                ):
                    possible_doors.append((x_coord, y))

        possible_doors = list(filter(lambda x: x not in exterior_wall_coords, possible_doors))
        door_a = random.randrange(0, len(possible_doors))
        door_a = possible_doors.pop(door_a)
        door_b = random.randrange(0, len(possible_doors))
        door_b = possible_doors.pop(door_b)

        for door in (door_a, door_b):
            x, y = door
            obj = game_objects["+"]

            # Removing wall prior to door placement
            door_tile = self.game.get_tile(x, y)
            for wall in filter(lambda x: x.name == "Wall", door_tile.contents):
                self.game.delete_object(wall)
            self.game.create_object(x, y, obj)

    def create_hall(self, hall):
        for x in range(hall.x1, hall.x2 + 1):
            for y in range(hall.y1, hall.y2 + 1):
                self.tiles[x][y].blocked = False
                self.tiles[x][y].block_sight = False

    def room_fill(self, x, y, max_w):
        # TODO: No longer used at present, but the idea of
        # Squeezing rooms into open places may be useful
        # leaving here for now.
        possible_rooms = []
        for r in room_types:
            w = len(room_types[r][0])
            h = len(room_types[r])

            if w > max_w and h > max_w:
                continue
            elif h <= max_w:
                new_room = Rect(self, x, y, h, w, name=r)
                if new_room.y2 < self.interior.y2:
                    flip = random.randint(0, 50)
                    possible_rooms.append((new_room, r, flip))
            elif w <= max_w and h > max_w:
                new_room = Rect(self, x, y, w, h, name=r)
                if new_room.y2 < self.interior.y2:
                    flip = random.randint(50, 100)
                    possible_rooms.append((new_room, r, flip))

        return possible_rooms
