# Class defining room tiles
class Tile():
    def __init__(self, x, y, ttype=None):
        self.x = x
        self.y = y
        self.ttype = ttype

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
    '''
    Class defining rectangular room
     - (x1, y1): upper left corner
     - (x2, y2): lower right corner
    '''
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y

        # Minus 1 since passed coord should be included
        self.w = w - 1
        self.h = h - 1

        self.x2 = x + w
        self.y2 = y + h

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

    def get_tiles(self):
        # Returns list of all coords in room, including walls
        all_tiles = []
        for x in range(self.x1, self.x2 + 1):
            for y in range(self.y1, self.y2 + 1):
                all_tiles.append((x, y))
        return all_tiles
