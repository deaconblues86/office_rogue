from functools import reduce


class Tile():
    """
    Class defining game tiles
     - Tiles control their contents and blocked/blocked sight status
    """
    def __init__(self, x, y, ttype=None):
        self.x = x
        self.y = y

        self.contents = []
        self.explored = False

    @property
    def blocked(self):
        return any([c.blocks is True for c in self.contents])

    @property
    def blocked_sight(self):
        return any([c.blocks_sight is True for c in self.contents])

    def add_content(self, obj):
        self.contents.append(obj)

    def remove_content(self, obj):
        self.contents = list(filter(lambda x: x is not obj, self.contents))

    def adjacent(self):
        return [
            (self.x - 1, self.y),       # Left
            (self.x - 1, self.y + 1),   # Lower Left
            (self.x, self.y + 1),       # Below
            (self.x + 1, self.y + 1),   # Lower Right
            (self.x + 1, self.y),       # Right
            (self.x + 1, self.y - 1),   # Upper Right
            (self.x, self.y - 1),       # Above
            (self.x - 1, self.y - 1)    # Upper Left
        ]


class Rect():
    """
    Class defining rectangular room
     - (x1, y1): upper left corner
     - (x2, y2): lower right corner
    """
    def __init__(self, game_map, x, y, w, h, name="", flip=0):
        self.game_map = game_map
        self.x1 = x
        self.y1 = y

        self.w = w
        self.h = h

        # Minus 1 since passed coord should be included
        self.x2 = x + w - 1
        self.y2 = y + h - 1

        self.name = name
        self.flip = flip

    def __str__(self):
        return f"{self.name}: upper_left=({self.x1},{self.y1}, lower_right=({self.x2}, {self.y2})"

    # Center and Intersect used during world gen
    def center(self):
        center_x = int(self.w / 2)
        center_y = int(self.h / 2)
        return (center_x, center_y)

    def intersect(self, other):
        # Returns true if it overlaps
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )

    def edges(self):
        # Returns list of four walls
        edges = []

        for x in range(self.x1, self.x2 + 1):
            edges.append((x, self.y1))
            edges.append((x, self.y2))
        for y in range(self.y1, self.y2 + 1):
            edges.append((self.x1, y))
            edges.append((self.x2, y))
        return edges

    def get_tile_coords(self):
        # Returns list of all coords in room, including walls
        all_tiles = []
        for x in range(self.x1, self.x2 + 1):
            for y in range(self.y1, self.y2 + 1):
                all_tiles.append((x, y))
        return all_tiles

    def get_tiles(self):
        for coord in self.get_tile_coords():
            yield self.game_map.get_tile(*coord)

    def get_contents(self):
        return reduce(lambda x, y: x + y, [x.contents for x in self.get_tiles()], [])
