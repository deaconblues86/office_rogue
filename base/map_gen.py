import random
import tcod

from constants import (
    room_types,
    game_objects,
    interiorRect,
    HALL_WIDTH,
    LIMITED_ROOMS,
    map_width,
    map_height
)
from base.map import Rect, Tile


def room_flip(rows, flip, x_int, y_int):
    if flip > 75:
        r = rows.pop(0)
        val = r.pop(0)
        rows.append(r)
        return val, rows

    elif flip > 50:
        r = rows.pop(-1)
        val = r.pop(-1)
        rows.insert(0, r)
        return val, rows

    elif flip > 25:
        if rows[0] == []:
            rows.pop(0)
        val = rows[0].pop(0)
        return val, rows

    else:
        if rows[-1] == []:
            rows.pop(-1)
        val = rows[-1].pop(-1)
        return val, rows


class MapGenerator():
    def __init__(self, game):
        self.game = game
        self.game.game_map = self
        self.tiles = []
        self.fov_map = None
        self.path_map = None
        self.interior = interiorRect

    def place_object(self, obj):
        self.tiles[obj.x][obj.y].add_content(obj)

    def remove_object(self, obj):
        self.tiles[obj.x][obj.y].remove_content(obj)

    def get_tile(self, x, y):
        return self.tiles[x][y]

    def get_obj_tile(self, obj):
        return self.tiles[obj.x][obj.y]

    def get_adjacent_tiles(self, obj):
        adj_coords = self.tiles[obj.x][obj.y].adjacent()
        return [self.tiles[x[0]][x[1]] for x in adj_coords]

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

            # Subtracting 1 as the len includes the starting cell (x & y being passed)
            w = len(room_types[rtype][0]) - 1
            h = len(room_types[rtype]) - 1

            flip = random.randrange(0, 100)

            if flip <= 50:
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

                hall = Rect(new_room.x1, new_room.y2 + 1, new_room.w, HALL_WIDTH - 1)

                if hall.y2 < self.interior.y2:
                    # create_hall(hall)
                    h_halls.append(hall)

                x = new_room.x2 + 1

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
                            picked_index = random.randrange(
                                0, len(possible_rooms)
                            )
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

    def generate_fov_path_map(self):
        self.fov_map = tcod.map.Map(map_width, map_height)
        for y in range(map_height):
            for x in range(map_width):
                self.fov_map.transparent[y, x] = self.tiles.blocked_sight

        self.path_map = tcod.map.Map(map_width, map_height)
        for y in range(map_height):
            for x in range(map_width):
                self.fov_map.transparent[y, x] = self.tiles.blocked

    def generate_coworkers(self):
        terminals = [x for x in self.game.appliances if x.name == 'Terminal']

        # Marking Player Owned Terminal
        player_terminal = terminals.pop(0)
        player_terminal.owner = self.game.player
        adj_tiles = [x for x in player_terminal.adjacent() if not x.blocked]
        self.game.player.x = adj_tiles[0].x
        self.game.player.y = adj_tiles[0].y

        temp_count = len(terminals) / 2
        for t in terminals:
            if temp_count == 0:
                break

            adj_tiles = [x for x in player_terminal.adjacent() if not x.blocked]
            x = adj_tiles[0].x
            y = adj_tiles[0].y

            coworker = self.game.create_coworker(x, y)
            t.owner = coworker

            temp_count -= 1

    def create_room(self, room, rtype, flip):
        x_int = 0
        y_int = 0

        rows = []
        for r in room_types[rtype]:
            rows.append(list(r))

        for x in range(room.x1, room.x2 + 1):
            for y in range(room.y1, room.y2 + 1):
                val, rows = room_flip(rows, flip, x_int, y_int)
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

    def place_doors(self, room):
        # Placing Doors
        possible_doors = []
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

        door_index_a = random.randrange(0, len(possible_doors))
        door_index_b = random.randrange(0, len(possible_doors))
        if possible_doors != []:
            x = possible_doors[door_index_a][0]
            y = possible_doors[door_index_a][1]
            obj = game_objects["+"]
            self.game.create_object(x, y, obj)

            x = possible_doors[door_index_b][0]
            y = possible_doors[door_index_b][1]
            self.game.create_object(x, y, obj)

    def create_hall(self, hall):
        for x in range(hall.x1, hall.x2 + 1):
            for y in range(hall.y1, hall.y2 + 1):
                self.tiles[x][y].blocked = False
                self.tiles[x][y].block_sight = False

    def room_fill(self, x, y, max_w):
        possible_rooms = []
        for r in room_types:
            w = len(room_types[r][0]) - 1
            h = len(room_types[r]) - 1

            if w > max_w and h > max_w:
                continue
            elif w > max_w and h <= max_w:
                new_room = Rect(x, y, h, w)
                if new_room.y2 < self.interior.y2:
                    flip = random.randrange(0, 50)
                    possible_rooms.append((new_room, r, flip, "man_rotate"))
            elif w <= max_w and h > max_w:
                new_room = Rect(x, y, w, h)
                if new_room.y2 < self.interior.y2:
                    flip = random.randrange(50, 100)
                    possible_rooms.append((new_room, r, flip, "man_nat"))
            else:
                flip = random.randrange(0, 100)
                if flip <= 50:
                    new_room = Rect(x, y, h, w)
                    if new_room.y2 < self.interior.y2:
                        possible_rooms.append((new_room, r, flip, "auto_rotate"))
                else:
                    new_room = Rect(x, y, w, h)
                    if new_room.y2 < self.interior.y2:
                        possible_rooms.append((new_room, r, flip, "auto_nat"))

        return possible_rooms
