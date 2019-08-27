import libtcodpy as libtcod
import math
import textwrap
import time
from traits import *


# Class defining room tiles
class Tile():
    def __init__(self, blocked, block_sight=None, ttype=None):
        self.blocked = blocked  # If True, disallows passage - default during world gen
        self.explored = False   # If True, tile will be displayed - False during world gen.  Controlled by fov_map in render_all
        self.ttype = ttype

        # Defaults block sight to blocked unless otherwise specified (opaque object assumed)
        self.block_sight = block_sight or blocked


# Class defining rectangular room
class Rect():
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y

        self.x2 = x + w
        self.y2 = y + h

        self.w = w
        self.h = h

    # Center and Intersect used during world gen
    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        # Returns true if it overlaps
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

    def edges(self):
        edges = []

        for x in range(self.x1, self.x2):
            edges.append((x, self.y1))
            edges.append((x, self.y2-1))
        for y in range(self.y1, self.y2):
            edges.append((self.x1, y))
            edges.append((self.x2-1, y))
        return edges

    def get_tiles(self):
        all_tiles = []
        for x in range(self.x1, self.x2):
            for y in range(self.y1, self.y2):
                all_tiles.append((x, y))
        return all_tiles


def mark_edges(coords):
    for (x, y) in coords:
        obj = Object('marker', x, y, 'X', libtcod.light_red)
        objects.append(obj)


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


def create_room(room, rtype, flip):
    global map

    x_int = 0
    y_int = 0

    rows = []
    for r in room_types[rtype]:
        rows.append(list(r))

    for x in range(room.x1, room.x2 + 1):
        for y in range(room.y1, room.y2 + 1):
            val, rows = room_flip(rows, flip, x_int, y_int)
            if val == '#':
                map[x][y].blocked = True
                map[x][y].block_sight = True
            else:
                if val == 'T':
                    obj = Object('Toilet', x, y, val, libtcod.white, blocks=True, satisfies=['bladder','bowels'], use_func=toilet_func)
                    objects.append(obj)
                elif val == 'U':
                    obj = Object('Urinal', x, y, val, libtcod.white, blocks=True, satisfies=['bladder'], use_func=urinal_func)
                    objects.append(obj)
                elif val == 'H':
                    obj = Object('Sink', x, y, val, libtcod.white, blocks=True)
                    objects.append(obj)
                elif val == 'W' and 'bath' in rtype:
                    obj = Object('tag', x, y, val, libtcod.pink)
                    objects.append(obj)
                elif val == 'M' and 'bath' in rtype:
                    obj = Object('tag', x, y, val, libtcod.light_blue)
                    objects.append(obj)
                elif val == 't':
                    obj = Object('Terminal', x, y, val, libtcod.light_green, satisfies=['work'], blocks=True, use_func=terminal_func)
                    objects.append(obj)
                elif val == 'M' and rtype == 'cafe':
                    obj = Object('Microwave', x, y, val, libtcod.orange, blocks=True)
                    objects.append(obj)
                elif val == 'F':
                    obj = Object('Refrigerator', x, y, val, libtcod.blue, blocks=True)
                    objects.append(obj)
                elif val == 'C':
                    obj = Object('Coffee Maker', x, y, val, libtcod.yellow, satisfies=['energy','thirst'], blocks=True, use_func=coffee_func)
                    objects.append(obj)
                elif val == 'V':
                    obj = Object('Vending Machine', x, y, val, libtcod.yellow, satisfies=['hunger','thirst'], blocks=True, use_func=vend_func)
                    objects.append(obj)
                elif val == '=':
                    obj = Object('Desk', x, y, val, libtcod.yellow, satisfies=['work'], blocks=True, use_func=desk_func)
                    objects.append(obj)
                elif val == 'x':
                    obj = Object('Chair', x, y, val, libtcod.dark_yellow)
                    objects.append(obj)
                elif val == 'S':
                    obj = Object('Supply Closet', x, y, val, libtcod.yellow, blocks=True)
                    objects.append(obj)
                elif val == '~':
                    map[x][y].ttype = 'grass'

                map[x][y].blocked = False
                map[x][y].block_sight = False


def place_doors(room):
    # Placing Doors
    possible_doors = []
    for x in range(room.x1+1, room.x2):
        if not is_blocked(x, room.y1 + 1) and not is_blocked(x, room.y1 - 1) and map[x][room.y1 + 1].ttype != 'grass' and map[x][room.y1-1].ttype != 'grass':
            possible_doors.append((x, room.y1))

        if not is_blocked(x, room.y2 + 1) and not is_blocked(x, room.y2-1) and map[x][room.y2 + 1].ttype != 'grass' and map[x][room.y2-1].ttype != 'grass':
            possible_doors.append((x, room.y2))

    for y in range(room.y1+1, room.y2):
        if not is_blocked(room.x1+1, y) and not is_blocked(room.x1 - 1 , y) and map[room.x1 - 1][y].ttype != 'grass' and map[room.x1+1][y].ttype != 'grass':
            possible_doors.append((room.x1, y))

        if not is_blocked(room.x2+1, y) and not is_blocked(room.x2-1,y) and map[room.x2 - 1][y].ttype != 'grass' and map[room.x2+1][y].ttype != 'grass':
            possible_doors.append((room.x2, y))

    door_index_a = libtcod.random_get_int(0, 0, len(possible_doors)-1)
    door_index_b = libtcod.random_get_int(0, 0, len(possible_doors)-1)
    if possible_doors != []:
        x = possible_doors[door_index_a][0]
        y = possible_doors[door_index_a][1]
        obj = Object('Door', x, y, '+', libtcod.light_sepia)
        objects.append(obj)

        map[x][y].blocked = False
        map[x][y].block_sight = False

        x = possible_doors[door_index_b][0]
        y = possible_doors[door_index_b][1]
        obj = Object('Door', x, y, '+', libtcod.light_sepia)
        objects.append(obj)

        map[x][y].blocked = False
        map[x][y].block_sight = False


def create_hall(hall):
    global map
    for x in range(hall.x1, hall.x2 + 1):
        for y in range(hall.y1,hall.y2 + 1):
            map[x][y].blocked = False
            map[x][y].block_sight = False


def room_fill(x, y, max_w):
    possible_rooms = []
    for r in room_types:
        w = len(room_types[r][0]) - 1
        h = len(room_types[r]) - 1

        if w > max_w and h > max_w:
            continue
        elif w > max_w and h <= max_w:
            new_room = Rect(x, y, h, w)
            if new_room.y2 < INSIDE.y2:
                flip = libtcod.random_get_int(0, 0, 49)
                possible_rooms.append((new_room, r, flip, 'man_rotate'))
        elif w <= max_w and h > max_w:
            new_room = Rect(x, y, w, h)
            if new_room.y2 < INSIDE.y2:
                flip = libtcod.random_get_int(0, 51, 100)
                possible_rooms.append((new_room, r, flip, 'man_nat'))
        else:
            flip = libtcod.random_get_int(0, 0, 100)
            if flip <= 50:
                new_room = Rect(x, y, h, w)
                if new_room.y2 < INSIDE.y2:
                    possible_rooms.append((new_room, r, flip, 'auto_rotate'))
            else:
                new_room = Rect(x, y, w, h)
                if new_room.y2 < INSIDE.y2:
                    possible_rooms.append((new_room, r, flip, 'auto_nat'))

    return possible_rooms


def make_map():
    global map, player
    map = [[Tile(False) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]

    inside_tiles = INSIDE.get_tiles()
    inside_edges = INSIDE.edges()
    for x in range(MAP_WIDTH):
        for y in range(MAP_HEIGHT):
            if (x, y) not in inside_tiles:
                map[x][y].ttype = 'grass'

            if (x, y) in inside_edges:
                map[x][y].blocked = True
                map[x][y].block_sight = True

    halls = []
    v_halls = []
    h_halls = []

    rooms = []
    num_rooms = 0

    x = INSIDE.x1
    y = INSIDE.y1

    building = True
    next_row = False
    while building:
        room_index = libtcod.random_get_int(0, 1, len(room_types))
        count = 0
        for r in room_types:
            count += 1

            if count == room_index:
                rtype = r
                break

        # Subtracting 1 as the len includes the starting cell (x & y being passed)
        w = len(room_types[rtype][0]) - 1
        h = len(room_types[rtype]) - 1

        flip = libtcod.random_get_int(0, 0, 100)

        if flip <= 50:
            if num_rooms != 0:
                x += HALL
            new_room = Rect(x, y, h, w)
        else:
            if num_rooms != 0:
                x += HALL
            new_room = Rect(x, y, w, h)

        failed = False
        if new_room.x2 > INSIDE.x2:
            failed = True
            next_row = True

        if not failed:
            create_room(new_room, rtype, flip)
            rooms.append(new_room)
            num_rooms += 1

            if rtype in LIMITED_ROOMS:
                del room_types[rtype]

            hall = Rect(new_room.x1, new_room.y2 + 1, new_room.w, HALL - 1)

            if hall.y2 < INSIDE.y2:
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

                    possible_rooms = room_fill(prev_x, hall.y2+1, diff_x)

                    if possible_rooms != []:
                        picked_index = libtcod.random_get_int(0, 0, len(possible_rooms)-1)
                        picked_room = possible_rooms[picked_index]

                        create_room(picked_room[0], picked_room[1], picked_room[2])
                        rooms.append(picked_room[0])

                        heights.append(picked_room[0].y2)

                        diff_x = max_x - picked_room[0].x2

                    else:
                        break

                if heights != []:
                    max_height = max(heights)
                    new_hall = Rect(hall.x1,max_height + 1,hall.w,HALL - 1)
                    if new_hall.y2 < INSIDE.y2:
                        # create_hall(new_hall)
                        h_halls.append(new_hall)

                building = False

    for room in rooms:
        place_doors(room)

    place_objects()


def is_blocked(x, y):
    if map[x][y].blocked:
        return True

    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False


out = open('coworkers.txt', 'wb')


def coworker_gen(x, y):
    x = int(x)
    y = int(y)

    social = libtcod.random_get_int(0, 25, 100)
    hunger = libtcod.random_get_int(0, 25, 100)
    thirst = libtcod.random_get_int(0, 25, 100)
    bladder = libtcod.random_get_int(0, 75, 100)
    bowels = libtcod.random_get_int(0, 75, 100)
    energy = libtcod.random_get_int(0, 25, 100)

    fighter_component = Fighter(
        social=social,
        hunger=hunger,
        thirst=thirst,
        bladder=bladder,
        bowels=bowels,
        energy=energy,
        traits=None,
        death_function=monster_death
    )

    ai_component = BasicCoworker()
    it_component = BasicCoworker(class_func=request_worker, work_func=request_work, work_objs=['Terminal'])
    maint_component = BasicCoworker(class_func=request_worker, work_func=request_work, work_objs=['Toilet', 'Urinal', 'Sink', 'Coffee Maker', 'Microwave', 'Refrigerator', 'Vending Machine'])

    if libtcod.random_get_int(0,0,100) < 61:
        name_file = open('defs/female_names.txt')
        names = [n.strip() for n in name_file.readlines()]
        # name = names[libtcod.random_get_int(0,0,len(names)-1)]

        # coworker = Object(name,x,y,'@',libtcod.pink,blocks=True,fighter=fighter_component,ai=ai_component,satisfies=['social'])

    else:
        name_file = open('defs/male_names.txt')
        names = [n.strip() for n in name_file.readlines()]
        # name = names[libtcod.random_get_int(0,0,len(names)-1)]

    if libtcod.random_get_int(0,0,100) < 26:
        if libtcod.random_get_int(0,0,100) < 50:
            ai_component = maint_component
            color = libtcod.light_blue
        else:
            ai_component = it_component
            color = libtcod.light_green
    else:
        color = libtcod.light_yellow

    name = names[libtcod.random_get_int(0,0,len(names)-1)]
    coworker = Object(name,x,y,'@',color,blocks=True,fighter=fighter_component,ai=ai_component,satisfies=['social'])
    
    COWORKERS.append(coworker)
    name_file.close()
    return coworker


def place_objects():
    terminals = [x for x in objects if x.name == 'Terminal']
    
    player_terminal = terminals.pop(0)
    
    player_terminal.owner=player
    adj_tiles = [x for x in player_terminal.adjacent() if not is_blocked(x[0],x[1])]
    player.x = adj_tiles[0][0]
    player.y = adj_tiles[0][1]
    
    temp_count = len(terminals) / 2
    for t in terminals:
        if temp_count == 0:
            break

        adj_tiles = [x for x in t.adjacent() if not is_blocked(x[0],x[1])]
        x = adj_tiles[0][0]
        y = adj_tiles[0][1]
        
        coworker = coworker_gen(x,y)
        t.owner = coworker
        objects.append(coworker)

        out.write(coworker.name + '\n')
        out.write(','.join([x.name for x in coworker.fighter.inventory]) + '\n')
        out.write(str(coworker.fighter.social) +'\n')
        out.write(str(coworker.fighter.hunger) +'\n')
        out.write(str(coworker.fighter.thirst) +'\n')
        out.write(str(coworker.fighter.bladder) +'\n')
        out.write(str(coworker.fighter.bowels) +'\n')
        out.write(str(coworker.fighter.energy) +'\n')
        out.write('\n')

        temp_count -= 1



#-----------------------------------------
# Setting up MAP and SCREEN Attributes   |
#-----------------------------------------

# Defining Layout variables for Map Gen
ROOM_SECTOR_X = 22
ROOM_SECTOR_Y = 22
HALL = 3
OUTSIDE_BORDER = 4

TURN_COUNT = 0

MAX_ROOMS = 4
MAP_WIDTH = 0
MAP_HEIGHT = 0

LIMITED_ROOMS = ['manager','patio']
COWORKERS = []

# Defining Building Space
INSIDE_X = (MAX_ROOMS * (ROOM_SECTOR_X + HALL)) - HALL
INSIDE_Y = ((MAX_ROOMS/2) * (ROOM_SECTOR_Y + HALL)) - HALL

INSIDE = Rect(OUTSIDE_BORDER,OUTSIDE_BORDER,INSIDE_X,INSIDE_Y)

# Adding Outdoor Space
MAP_WIDTH += INSIDE_X + (OUTSIDE_BORDER * 2)
MAP_HEIGHT += INSIDE_Y + (OUTSIDE_BORDER * 2)

# Adding Padding to Screen to allow for UI
SCREEN_WIDTH = MAP_WIDTH + 10
SCREEN_HEIGHT = MAP_HEIGHT + 7

# Limiting FPS
LIMIT_FPS = 10

# Setting Wall/Tile Colors
color_dark_walls = libtcod.grey
color_dark_ground = libtcod.grey
color_light_walls = libtcod.white
color_light_ground = libtcod.white

# color_dark_walls = libtcod.Color(0,0,100)
# color_dark_ground = libtcod.Color(50,50,150)
# color_light_walls = libtcod.Color(130,110,50)
# color_light_ground = libtcod.Color(200,180,50)

#------------------------------
# Panel and UI attributes     |
#------------------------------

BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

MSG_X = (BAR_WIDTH * 2) + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

INVENTORY_WIDTH = 50

#------------------------------
# FOV attributes              |
#------------------------------

FOV_ALGO = 0            # Algorithm
FOV_LIGHT_WALLS = True  # Change Wall Colors?
TORCH_RADIUS = 10       # Range


#------------------------------
# Game attributes             |
#------------------------------

# Used for Realtime
GAME_SPEED = 0.25

MAX_INVENTORY = 4

room_types = {}
room_file = open('defs/rooms.txt')
r = ''
for line in room_file:
    line = line.strip().split('\t')

    if len(line) == 1:
        if line == ['']:
            continue
        r = line[0]
        room_types[r] = []
    else:
        room_types[r].append(line)

room_file.close()



class Object:
    
    def __init__(self, name, x, y, char, color, blocks=False, fighter=None, ai=None, item=None, state="", target=None, owner=None, satisfies=None, use_func=None, durability=100):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.orig_color = color
        self.name = name
        self.blocks = blocks
        self.fighter = fighter
        self.ai = ai
        self.state = state
        self.target = target
        self.owner = owner
        self.satisfies = satisfies
        self.use_func = use_func
        self.durability = durability
        self.item = item
        
    
        # Passes Parent level attibutes to Child class
        if self.fighter:
            self.fighter.owner = self
        if self.ai:
            self.ai.owner = self
            if self.ai.class_func:
                self.ai.class_func(self.ai)
    
    # If next tile is passible, set current tile to be passible, move, and new til to be impassible
    def move(self, dx, dy):
        if not is_blocked(self.x + dx,self.y + dy):
            libtcod.map_set_properties(path_map, self.x, self.y, True, True)
            self.x += dx
            self.y += dy
            libtcod.map_set_properties(path_map, self.x, self.y, True, False)

        else:
            return 'is_blocked'
    
    def move_towards(self, target_x, target_y):
        # dx = target_x - self.x
        # dy = target_y - self.y
        # distance = math.sqrt(dx**2 + dy**2)
        
        path = libtcod.path_new_using_map(path_map)

        libtcod.path_compute(path, self.x, self.y, target_x, target_y)
        new_x, new_y = libtcod.path_walk(path,True)
        if not new_x is None:
            dx = new_x - self.x
            dy = new_y - self.y

            self.move(dx, dy)
            return True
        else:
            print self.name + " is stuck"
            return False

        libtcod.path_delete(path)                
    

    def distance_to(self, target):
        dx = target.x - self.x
        dy = target.y - self.y
        return math.sqrt(dx**2 + dy**2)
    
    def adjacent(self):
        return [(self.x-1,self.y),(self.x-1,self.y+1),(self.x,self.y+1),(self.x+1,self.y+1),(self.x+1,self.y),(self.x+1,self.y-1),(self.x,self.y-1),(self.x-1,self.y-1)]


    def satisfy_need(self, state, target):
        self.state = state
        self.criteria = target
        self.target = self.find_closest(self.criteria)
        if not self.target:
            print self.name, 'cant find', self.target

        else:
            if (self.x, self.y) not in  self.target.adjacent():
                possible_targets = [coords for coords in self.target.adjacent() if not is_blocked(coords[0],coords[1])]
                if possible_targets != []:
                    target_x, target_y = possible_targets[0]

                    # If path isn't found to target object, reassess situation by setting state to idle
                    if not self.move_towards(target_x,target_y):
                        self.state = 'idle'

                else:
                    print self.target.name, 'is Occupado!'
                    self.target = self.find_closest(self.criteria)

            else:
                # print self.name, 'is adjacent to ', self.target.name
                if self.target.fighter:
                    self.fighter.give_social(self.target)

                # call repair function if broken -- ai won't do this unless repairing
                elif self.target.state == 'broken':
                    repair_func(self, self.target)

                else:
                    self.use_object(self.target)


    def find_closest(self, target, failed=False):
        min = ''
        closest_obj = False
        for obj in target:

            # Skipping self
            if obj == self:
                continue

            # Skipping object found to be in accessable
            if failed:
                if obj == failed:
                    continue

            # Checking ownership unless repairing
            if obj.owner not in [None,self] and 'repair' not in self.state:
                continue
            
            # Skipping broken objects unless repairing
            if obj.state == 'broken' and 'repair' not in self.state:
                continue

            # Checking if object's in use  ASSUMPTION: no free tiles around object means it's in use
            possible_targets = [coords for coords in obj.adjacent() if not is_blocked(coords[0],coords[1]) or coords == (self.x, self.y)]
            if possible_targets == []:
                continue

            dx = obj.x - self.x
            dy = obj.y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if min == '' or distance < min:
                min = distance
                closest_obj = obj

        return closest_obj

    def use_object(self, target):
        if target.use_func != None and target.durability > 0:
            target.durability -= target.use_func(self)

            if target.durability <= 0:
                target.color = libtcod.light_violet
                target.state = 'broken'

        else:
            if self == player:
                message('The ' + target.name + ' is broken!', libtcod.light_violet)


    def use_item(self, target):
        if target.use_func != None:
            target.durability -= target.use_func(self)
            print self.name, "is using", target.name, [x.name for x in self.fighter.inventory]

            if target.durability <= 0:
                self.fighter.inventory.remove(target)

                if self == player:
                    message('The ' + target.name + ' has been consumed!', libtcod.light_violet)

                del target

        else:
            message('The ' + target.name + ' can not be used!', libtcod.light_violet)

    def wander(self):
        self.state = 'idle'
        self.target = self
        dir = libtcod.random_get_int(0,0,9)
            
        if dir == 8:
            self.move(0,-1)
        elif dir == 7:
            self.move(-1,-1) 
        elif dir == 9: 
            self.move(1,-1)
        elif dir == 1:
            self.move(-1,1)            
        elif dir == 2:
            self.move(0,1)
        elif dir == 3:
            self.move(1,1)  
        elif dir == 6:
            self.move(1,0)
        elif dir == 4:
            self.move(-1,0)
        else:
            self.move(0,0)

    def draw(self):
        # if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_set_default_foreground(con,self.color)  # Sets Font color to be white for main (0) console window
            libtcod.console_put_char(con,self.x,self.y,self.char, libtcod.BKGND_NONE) # Prints @ to console (0 == window, 1/1 == coords)
            
    def send_to_back(self):
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def clear(self):
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)


class Fighter:
    
    def __init__(self, social, hunger, thirst, bladder, bowels, energy, traits=None, specialty=None, death_function=None):
        self.max_social = float(social)
        self.social = float(social)
        self.social_gain = self.max_social * .2
        self.social_drain = -.5
        
        self.max_hunger = float(hunger)
        self.hunger = float(hunger)
        self.hunger_gain = 0.0
        self.hunger_drain = -.25
        
        self.max_thirst = float(thirst)
        self.thirst = float(thirst)
        self.thirst_gain = 0.0
        self.thirst_drain = -.5
        
        self.max_bladder = float(bladder)
        self.bladder = float(bladder)
        self.bladder_gain = 0.0
        self.bladder_drain = -.5
        
        self.max_bowels = float(bowels)
        self.bowels = float(bowels)
        self.bowels_gain = 0.0
        self.bowels_drain = -.25
        
        self.max_energy = float(energy)
        self.energy = float(energy)
        self.energy_gain = 0.0
        self.energy_drain = -.5
        
        self.max_work = 100.0
        self.work = 50.0
        self.work_drain = -.5

        self.specialty = specialty
        
        self.greeted = False
        self.death_function = death_function
        self.inventory = list()
    
        if traits:
            if type(traits) == list():
                for trait_func in traits:
                    trait_func(self.owner)
            else:
                trait_func(self.owner)
        
    def take_social(self,social_gain):
        if social_gain > 0:
            self.social = min(self.social + social_gain, self.max_social)
    
    def give_social(self, target):
        if target.fighter.social > self.social:
            self.take_social(self.social_gain)
            message(self.owner.name.capitalize() + ' chats with ' + target.name + ' for ' + str(self.social_gain))
            target.fighter.take_social(self.social_gain)
        
        elif target.fighter.social <= self.social:
            gain = max([self.social_gain,target.fighter.social_gain])
            self.take_social(gain)
            message(self.owner.name.capitalize() + ' engages in conversation with ' + target.name + ' for ' + str(gain))
            target.fighter.take_social(target.fighter.social_gain)

        self.owner.state = 'success: ' + self.owner.state

    def check_needs(self):
        if self.work <= 0:
            function = self.death_function
            if function is not None:
                function(self.owner)
    
        if self.bladder <= 0:
            urine = Object('Urine',self.owner.x,self.owner.y,'%',libtcod.light_yellow)
            objects.append(urine)
            urine.send_to_back()
            self.bladder = self.max_bladder

        if self.bowels <= 0:
            poo = Object('Poo',self.owner.x,self.owner.y,'%',libtcod.light_sepia)
            objects.append(poo)
            poo.send_to_back()
            self.bowels = self.max_bowels

    def tick_needs(self):
        self.social = max(self.social_drain + self.social, 0)
        self.hunger = max(self.hunger_drain + self.hunger, 0)
        self.thirst = max(self.thirst_drain + self.thirst, 0)
        # self.bladder = max(self.bladder_drain + self.bladder, 0)
        # self.bowels = max(self.bowels_drain + self.bowels, 0)
        # self.energy = max(self.energy_drain + self.energy, 0)
        self.work = max(self.work_drain + self.work, 0)


class BasicCoworker():
    def __init__(self, class_func=False, work_func=False, work_objs=False):
        self.class_func = class_func
        self.work_func = work_func
        self.work_objs = work_objs

    def take_turn(self):
        global TURN_COUNT, out

        coworker = self.owner

        # BS that's hanging around
        if libtcod.map_is_in_fov(fov_map, coworker.x, coworker.y) and coworker.fighter.greeted == False:
            coworker.fighter.greeted = True
            message(coworker.name + " says hi!")


        needs = [(coworker.fighter.social,coworker.fighter.max_social,'social'),
                (coworker.fighter.hunger,coworker.fighter.max_hunger,'hunger'),
                (coworker.fighter.thirst,coworker.fighter.max_thirst,'thirst'),
                (coworker.fighter.bladder,coworker.fighter.max_bladder,'bladder'),
                (coworker.fighter.bowels,coworker.fighter.max_bowels,'bowels'),
                (coworker.fighter.energy,coworker.fighter.max_energy,'energy'),
                (coworker.fighter.work,coworker.fighter.max_work,'work')
                ]

        # Checking if AI has finished current task.  If so, determines most pressing need
        if not coworker.state or coworker.state == 'idle':
            lowest_need = ''
            lowest_perc = 100
            for need in needs:
                perc = need[0]/need[1]

                if perc < lowest_perc:
                    lowest_perc = perc
                    lowest_need = need[2]

            coworker.state = 'satisfying ' + lowest_need

            # First, checking inventory for an item to satisfy need
            useful_items = [obj for obj in coworker.fighter.inventory if lowest_need in obj.satisfies]
            if useful_items != []:
                coworker.use_item(useful_items[0])

            # Then, Checking world for satisfaction
            else:
                if lowest_need == 'work' and self.work_func:
                    wanted_objs = self.work_func(self, self.work_objs)

                else:
                    wanted_objs = []
                    for obj in objects:
                        if obj.satisfies:
                            if lowest_need in obj.satisfies:
                                wanted_objs.append(obj)

                coworker.satisfy_need(coworker.state, wanted_objs)

        # If in the process of satisfaction, continue doing it
        else:
            coworker.satisfy_need(coworker.state,coworker.criteria)


        # print coworker.name, coworker.state, coworker.target.name


        # Writing Log of AI turns for Debug
        out.write(str(TURN_COUNT)+'\n')
        out.write(coworker.name + '\n')
        out.write(str(coworker.fighter.specialty) + '\n')
        out.write(','.join([x.name for x in coworker.fighter.inventory]) + '\n')
        out.write(coworker.state + '\n')

        if coworker.target == False:
            out.write('object not found\n')
        else:
            out.write(str(coworker.target.name) + '\n')

        out.write('work:\t' + str(coworker.fighter.work) + '/' + str(coworker.fighter.max_work) + '\n')
        out.write('social:\t' + str(coworker.fighter.social) + '/' + str(coworker.fighter.max_social) + '\n')
        out.write('hunger:\t' + str(coworker.fighter.hunger) + '/' +  str(coworker.fighter.max_hunger) + '\n')
        out.write('thirst:\t' + str(coworker.fighter.thirst) + '/' + str(coworker.fighter.max_thirst) + '\n')
        out.write('bladder:\t' + str(coworker.fighter.bladder) + '/' + str(coworker.fighter.max_bladder) + '\n')
        out.write('bowels:\t' + str(coworker.fighter.bowels) + '/' + str(coworker.fighter.max_bowels) + '\n')
        out.write('energy:\t' + str(coworker.fighter.energy) + '/' + str(coworker.fighter.max_energy) + '\n')
        out.write('\n')


# class ITCoworker:

#     def class_func(self):

#         coworker = self.owner

#         # Zeroing out work drain  & Maxing out Work for IT
#         coworker.fighter.work_drain = 0
#         coworker.fighter.work = coworker.fighter.max_work

    
#     def take_turn(self):
#         global TURN_COUNT, out
        
#         coworker = self.owner

#         ### IT Specific ###

#         # Creating list of requests to handle requests for terminal service
#         self.requests = [x for x in objects if x.name == 'Terminal' and x.state == 'broken']

#         ### Shouldn't be needed any longer ###
#         # Verifying objects in requests are still broken
#         # for obj in self.requests:
#         #     if obj.state != 'broken':
#         #         self.requests.remove(obj)

#         # Setting work drain to be 1 times the number of broken machines
#         if len(self.requests) != 0:
#             coworker.fighter.work_drain = 1 * len(self.requests)

#         ### ----------- ###

#         # BS that's hanging around
#         if libtcod.map_is_in_fov(fov_map, coworker.x, coworker.y) and coworker.fighter.greeted == False:
#             coworker.fighter.greeted = True
#             message(coworker.name + " says hi!")


#         needs = [(coworker.fighter.social,coworker.fighter.max_social,'social'),
#                 (coworker.fighter.hunger,coworker.fighter.max_hunger,'hunger'),
#                 (coworker.fighter.thirst,coworker.fighter.max_thirst,'thirst'),
#                 (coworker.fighter.bladder,coworker.fighter.max_bladder,'bladder'),
#                 (coworker.fighter.bowels,coworker.fighter.max_bowels,'bowels'),
#                 (coworker.fighter.energy,coworker.fighter.max_energy,'energy'),
#                 (coworker.fighter.work,coworker.fighter.max_work,'work')
#                 ]

#         # Checking if AI has finished current task.  If so, determines most pressing need
#         if not coworker.state or coworker.state == 'idle':
#             lowest_need = ''
#             lowest_perc = 100
#             for need in needs:
#                 perc = need[0]/need[1]

#                 if perc < lowest_perc:
#                     lowest_perc = perc
#                     lowest_need = need[2]

#             ### Modified BasicWorker Logic to use requests when satisfying Wokr
#             if lowest_need == 'work':
#                 state = 'satisfying ' + lowest_need
#                 cowker.satisfy_need(state, self.requests)

#             else:
#                 # First, checking inventory for an item to satisfy need
#                 useful_items = [obj for obj in coworker.fighter.inventory if lowest_need in obj.satisfies]
#                 if useful_items != []:
#                     coworker.use_item(useful_items[0])

#                 # Then, Checking world for satisfaction
#                 else:
#                     wanted_objs = []
#                     for obj in objects:
#                         if obj.satisfies:
#                             if lowest_need in obj.satisfies:
#                                 wanted_objs.append(obj)

#                     state = 'satisfying ' + lowest_need 
#                     coworker.satisfy_need(state, wanted_objs)

#         # If in the process of satisfaction, continue doing it
#         else:
#             coworker.satisfy_need(coworker.state,coworker.criteria)


#         # print coworker.name, coworker.state, coworker.target.name


#         # Writing Log of AI turns for Debug
#         out.write(str(TURN_COUNT)+'\n')
#         out.write(coworker.name + '\n')
#         out.write(','.join([x for x in coworker.fighter.inventory]) + '\n')
#         out.write(coworker.state + '\n')
#         out.write(str(coworker.target.name) + '\n')

#         out.write('work:\t' + str(coworker.fighter.work) + '/' + str(coworker.fighter.max_work) + '\n')
#         out.write('social:\t' + str(coworker.fighter.social) + '/' + str(coworker.fighter.max_social) + '\n')
#         out.write('hunger:\t' + str(coworker.fighter.hunger) + '/' +  str(coworker.fighter.max_hunger) + '\n')
#         out.write('thirst:\t' + str(coworker.fighter.thirst) + '/' + str(coworker.fighter.max_thirst) + '\n')
#         out.write('bladder:\t' + str(coworker.fighter.bladder) + '/' + str(coworker.fighter.max_bladder) + '\n')
#         out.write('bowels:\t' + str(coworker.fighter.bowels) + '/' + str(coworker.fighter.max_bowels) + '\n')
#         out.write('energy:\t' + str(coworker.fighter.energy) + '/' + str(coworker.fighter.max_energy) + '\n')
#         out.write('\n')


def player_move_or_attack(dx,dy):
    global fov_recompute
    x = player.x + dx
    y = player.y + dy
    
    target = None
    for object in objects:
        if object.x == x and object.y == y:
            target = object
            break
    
    if target:
        if target.blocks:
            if target.fighter:
                player.fighter.give_social(target)
            else:
                player.use_object(target)
        else:
            player.move(dx,dy)
            fov_recompute = True          
    else:
        player.move(dx,dy)
        fov_recompute = True

def player_death(player):
    global game_state
    message("You're Fired!",libtcod.red)
    game_state = 'dead'
    
    player.char = '%'
    player.color = libtcod.dark_red


def request_worker(ai):

    coworker = ai.owner

    # Maxing out Work for IT -- Need to tick work to check for broken objects
    # coworker.fighter.work_drain = 0
    coworker.fighter.work = coworker.fighter.max_work
    coworker.fighter.specialty = 'repair'

def request_work(ai, obj_names):

    # Creating list of requests to handle requests for terminal service
    requests = [x for x in objects if x.name in obj_names and x.state == 'broken']

    # Setting work drain at plus 10% forc each broken machine
    if len(requests) != 0:
        ai.owner.fighter.work_drain += ai.owner.fighter.work_drain * 0.1
        ai.owner.state += '-brepairing'
        print [x.name for x in requests], ai.owner.fighter.work_drain

    else:
        ai.owner.fighter.work = ai.owner.fighter.max_work
        ai.owner.state = "success: " + ai.owner.state
        print 'nothing broken found'

    return requests


def monster_death(monster):
    message(monster.name.capitalize() + ' is fired!',libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.state = 'fired'
    monster.satisfies = None
    libtcod.map_set_properties(path_map, monster.x, monster.y, True, True)
    monster.send_to_back()


def toilet_func(target):
    target.fighter.bladder = target.fighter.max_bladder
    target.fighter.bowels = target.fighter.max_bowels
    message(target.name.capitalize() + ' uses the toilet')
    target.state = 'success: ' + target.state
    return libtcod.random_get_int(0,5,10)  # Wearing out object

def urinal_func(target):
    target.fighter.bladder = target.fighter.max_bladder
    message(target.name.capitalize() + ' uses the urinal')
    target.state = 'success: ' + target.state
    return libtcod.random_get_int(0,5,10)  # Wearing out object

def terminal_func(target):
    energy_ratio = float(target.fighter.energy) / float(target.fighter.max_energy)
    work_gain = target.fighter.max_work * (energy_ratio * .3)
    target.fighter.work = min(target.fighter.work + work_gain, target.fighter.max_work)
    target.fighter.energy = max(target.fighter.energy - (work_gain * 0.25), 0)
    message(target.name.capitalize() + ' uses their terminal')
    target.state = 'success: ' + target.state
    return libtcod.random_get_int(0,5,10)  # Wearing out object

def desk_func(target):
    energy_ratio = float(target.fighter.energy) / float(target.fighter.max_energy)
    work_gain = target.fighter.max_work * (energy_ratio * .15)
    target.fighter.work = min(target.fighter.work + work_gain, target.fighter.max_work)
    target.fighter.energy = max(target.fighter.energy - (work_gain * 0.5), 0)
    message(target.name.capitalize() + ' uses their desk')
    target.state = 'success: ' + target.state
    return libtcod.random_get_int(0,5,10)  # Wearing out object

def repair_func(worker, target):
    energy_ratio = float(worker.fighter.energy) / float(worker.fighter.max_energy)
    work_gain = worker.fighter.max_work * (energy_ratio * .3)
    worker.fighter.work = min(worker.fighter.work + work_gain, worker.fighter.max_work)
    worker.fighter.energy = max(worker.fighter.energy - (work_gain * 0.25), 0)
    message(worker.name.capitalize() + ' repairs the ' + target.name.capitalize())
    worker.state = 'success: ' + worker.state
    
    # Currently setting up repair to add durability to target equal to work put it
    target.durability += work_gain
    target.state = ""
    target.color = target.orig_color

def coffee_func(target):
    target.fighter.energy = target.fighter.max_energy
    target.fighter.thirst = min(target.fighter.thirst + (target.fighter.max_thirst * 0.25), target.fighter.max_thirst)
    target.fighter.bladder = max(target.fighter.bladder - (target.fighter.max_bladder *0.1), 0)
    target.fighter.bowels = max(target.fighter.bowels - (target.fighter.max_bowels *0.1), 0)
    message(target.name.capitalize() + ' gets some coffee')
    target.state = 'success: ' + target.state
    return libtcod.random_get_int(0,5,10)  # Wearing out object


def water_func(target):
    target.fighter.thirst = min(target.fighter.thirst + (target.fighter.max_thirst * 0.75), target.fighter.max_thirst)
    target.fighter.bladder = max(target.fighter.bladder - (target.fighter.max_bladder *0.1), 0)
    message(target.name.capitalize() + ' drinks some water')
    target.state = 'success: ' + target.state
    return 50

def snack_func(target):
    target.fighter.hunger = min(target.fighter.hunger + (target.fighter.max_hunger * 0.5), target.fighter.max_hunger)
    target.fighter.bowels = max(target.fighter.bowels - (target.fighter.max_bowels *0.1), 0)
    message(target.name.capitalize() + ' eats a snack')
    target.state = 'success: ' + target.state
    return 25

def vend_func(target):
    chosen_index = None
    vend_item = False
    if target == player:
        if len(target.fighter.inventory) == MAX_INVENTORY:
            message("Your Inventory is full", libtcod.dark_red)

        else:
            chosen_index = menu('Vending Machine:',['Water','Snack'],INVENTORY_WIDTH)


    ### Inconsistent:  AI can use vend objects regardless of inventory -- Shouldn't be a problem for now since they'll preferencially use their inventory first
    if chosen_index == 0 or target.state == 'satisfying thirst':
        vend_item = Object('Water Bottle', target.x, target.y, '!', libtcod.light_blue, owner=target, satisfies=['thirst'], item=True, use_func=water_func)
        message(target.name.capitalize() + ' gets a bottle of water')

    elif chosen_index == 1 or target.state == 'satisfying hunger':
        vend_item = Object('Snack', target.x, target.y, '^', libtcod.light_green, owner=target, satisfies=['hunger'], item=True, use_func=snack_func)
        message(target.name.capitalize() + ' gets a snack')

    if vend_item:
        target.fighter.inventory.append(vend_item)
        print target.name, "vending:", chosen_index, vend_item.name,[x.name for x in target.fighter.inventory]
        target.state = 'success: vend ' + target.state

        return libtcod.random_get_int(0,5,10)  # Wearing out object

    # Returning zero to not damage vending machine if nothing is selected
    return 0





#---------------------------------------------------------------|
#---------------------------------------------------------------|
#                           RENDER FUNCTIONS                    |
#---------------------------------------------------------------|
#---------------------------------------------------------------|

def menu(header, options, width):
    if len(options) > 26: raise ValueError("Cannot have more than 26 options in a menu")
    
    header_height = libtcod.console_get_height_rect(con, 0,0, width, SCREEN_HEIGHT, header)
    height = len(options) + header_height
    
    window = libtcod.console_new(width, height)
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0,0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
    
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = chr(letter_index) + ": " + option_text
        libtcod.console_print_ex(window,0,y,libtcod.BKGND_NONE,libtcod.LEFT, text)
        y += 1
        letter_index += 1
    
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    # libtcod.console_blit(window,0,0, width, height, 0, x, y, 1.0, 0.7)
    libtcod.console_blit(window,0,0, width, height, 0, x, 0, 1.0, 0.7)
    
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
    
    # Converts ASCII to index val
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None


def inventory_menu(header):
    if len(player.fighter.inventory) == 0:
        options = ["Inventory is empty"]
    else:
        options = [item.name for item in player.fighter.inventory]
    
    index = menu(header, options, INVENTORY_WIDTH)
    
    if index is None or len(player.fighter.inventory) == 0: return None
    return player.fighter.inventory[index]

def message(new_msg, color = libtcod.white):
    
    # Wrap Lines appropriately
    new_msg_lines = textwrap.wrap(new_msg,MSG_WIDTH)
    
    for line in new_msg_lines:
        if len(game_msgs) == MSG_HEIGHT:
            game_msgs.pop(0)
        
        game_msgs.append((line,color))

def get_names_under_mouse():
    global mouse
    
    (x,y) = (mouse.cx, mouse.cy)
    # names = [obj.name for obj in objects if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x,obj.y)]
    names = [obj.name + ' ' + obj.state for obj in objects if obj.x == x and obj.y == y]
    names = ', '.join(names)
    return names.capitalize()

def render_bar(x, y, total_width, name, value, maximum, text_color, bar_color, back_color):
    bar_width = int(float(value) / maximum * total_width)
    bar_width = min([bar_width,total_width])
    
    # Sets up background of bar
    libtcod.console_set_default_background(panel,back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
    
    # Sets up filled value of bar
    libtcod.console_set_default_background(panel, bar_color)
    libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    # Text of actual values
    libtcod.console_set_default_foreground(panel, text_color)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ": " + str(value) + '/' + str(maximum))

def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute
    
    if fov_recompute:
        #recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
            
    
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            visible = libtcod.map_is_in_fov(fov_map, x, y)
            wall = map[x][y].block_sight
            ttype = map[x][y].ttype
            # if not visible:
                # if map[x][y].explored:
                    # if wall:
                        ##libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET )
                        # libtcod.console_set_default_foreground(con,color_dark_walls)
                        # libtcod.console_put_char(con, x, y, '#', libtcod.BKGND_NONE)
                    # else:
                        ##libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET )
                        # libtcod.console_set_default_foreground(con,color_dark_ground)
                        # libtcod.console_put_char(con, x, y, '.', libtcod.BKGND_NONE)
                    
            # else:
                # map[x][y].explored = True
            if wall:
                    # libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET )
                    libtcod.console_set_default_foreground(con,color_light_walls)
                    libtcod.console_put_char(con, x, y, '#', libtcod.BKGND_NONE)
            else:
                    if ttype == 'grass':
                        libtcod.console_set_default_foreground(con,libtcod.light_green)
                        libtcod.console_put_char(con, x, y, '~', libtcod.BKGND_NONE)
                    
                    else:
                        # libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET )
                        libtcod.console_set_default_foreground(con,color_light_ground)
                        libtcod.console_put_char(con, x, y, '.', libtcod.BKGND_NONE)
                
    
    for object in objects:
        if object != player:
            object.draw()
        
    player.draw()
    
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH,SCREEN_HEIGHT, 0,0,0) # Writing offscreen console to main console
    
    libtcod.console_clear(panel)
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_set_default_background(panel, libtcod.black)
    
    y = 1
    for (line,color) in game_msgs:
        libtcod.console_set_default_foreground(panel,color)
        libtcod.console_print_ex(panel,MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1
    
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_set_default_background(panel, libtcod.black)
    
    #show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'Social: ', int(player.fighter.social), int(player.fighter.max_social), libtcod.black, libtcod.light_yellow, libtcod.darker_yellow)
    libtcod.console_set_default_background(panel, libtcod.black)

    render_bar(1, 2, BAR_WIDTH, 'Work: ', int(player.fighter.work), int(player.fighter.max_work), libtcod.black, libtcod.light_green, libtcod.darker_green)
    libtcod.console_set_default_background(panel, libtcod.black)

    render_bar(1, 3, BAR_WIDTH, 'Energy: ', int(player.fighter.energy), int(player.fighter.max_energy), libtcod.black, libtcod.light_violet, libtcod.darker_violet)
    libtcod.console_set_default_background(panel, libtcod.black)

    render_bar(BAR_WIDTH+1, 1, BAR_WIDTH, 'Hunger: ', int(player.fighter.hunger), int(player.fighter.max_hunger), libtcod.black, libtcod.light_red, libtcod.darker_red)
    libtcod.console_set_default_background(panel, libtcod.black)

    render_bar(BAR_WIDTH+1, 2, BAR_WIDTH, 'Thirst: ', int(player.fighter.thirst), int(player.fighter.max_thirst), libtcod.black, libtcod.light_blue, libtcod.darker_blue)
    libtcod.console_set_default_background(panel, libtcod.black)

    render_bar(BAR_WIDTH+1, 3, BAR_WIDTH, 'Bladder: ', int(player.fighter.bladder), int(player.fighter.max_bladder), libtcod.black, libtcod.light_grey, libtcod.darker_grey)
    libtcod.console_set_default_background(panel, libtcod.black)

    render_bar(BAR_WIDTH+1, 4, BAR_WIDTH, 'Bowels: ', int(player.fighter.bowels), int(player.fighter.max_bowels), libtcod.black, libtcod.sepia, libtcod.darker_sepia)
    libtcod.console_set_default_background(panel, libtcod.black)
    
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_set_default_background(panel, libtcod.black)
    
    libtcod.console_set_default_foreground(panel, libtcod.light_grey)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
    
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0,0,PANEL_Y)

    

# Sets up key_bindings
def handle_keys():
    global key
    
    # Using console_check_for_keypress() to set up delay of check
    # key = libtcod.console_check_for_keypress()
    
    # Replace above line with this to force hold on console till key is pressed (turn-based)
    # key = libtcod.console_wait_for_keypress(True)
    
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
    
    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit' # Exit
    
    if game_state == 'playing':
        # Movement keys -- using console_is_key_pressed() for realtime check of key status
        if key.vk in [libtcod.KEY_KP8, libtcod.KEY_UP]:
            player_move_or_attack(0,-1)

        elif key.vk in [libtcod.KEY_KP7]:
            player_move_or_attack(-1,-1) 
            
        elif key.vk in [libtcod.KEY_KP9]:
            player_move_or_attack(1,-1)

        elif key.vk in [libtcod.KEY_KP1]:
            player_move_or_attack(-1,1)            
    
        elif key.vk in [libtcod.KEY_KP2, libtcod.KEY_DOWN]:
            player_move_or_attack(0,1)
            
        elif key.vk in [libtcod.KEY_KP3]:
            player_move_or_attack(1,1)  
    
        elif key.vk in [libtcod.KEY_KP6, libtcod.KEY_RIGHT]:
            player_move_or_attack(1,0)
        
        elif key.vk in [libtcod.KEY_KP4, libtcod.KEY_LEFT]:
            player_move_or_attack(-1,0)
        
        elif key.c == ord('.'):
            return 'wait'

        elif key.c == ord('i'):
            chosen_item = inventory_menu("Press the specified key to use an item or any other to cancel.\n")
            if chosen_item is not None:
                print "using:", chosen_item.name
                player.use_item(chosen_item)
                print "used:", chosen_item.name,[x.name for x in player.fighter.inventory]
            else:
                return 'didnt-take-turn'

        elif key.c == ord('g'):
            found = []
            options = []
            for obj in objects:
                if (obj.x, obj.y) == (player.x, player.y) and obj.item:
                    found.append(obj)
                    options.append(obj.name)

            if found == []:
                options.append('No items to pick up...')

            chosen_item = menu("Press the specified key to pick up an item or any other to cancel", options, INVENTORY_WIDTH)
            if chosen_item is not None and found != []:
                if len(player.fighter.inventory) < MAX_INVENTORY:
                    print "picking:", found[chosen_item].name
                    player.fighter.inventory.append(found[chosen_item])
                    objects.remove(found[chosen_item])
                    message("Picked up " + found[chosen_item].name, libtcod.light_violet)
                    print "picked:", found[chosen_item].name,[x.name for x in player.fighter.inventory]
                else:
                    message("Your Inventory is full", libtcod.dark_red)
                    return 'didnt-take-turn'

            else:
                return 'didnt-take-turn'



        elif key.c == ord('d'):
            chosen_item = inventory_menu("Press the specified key to drop an item or any other to cancel.\n")
            if chosen_item is not None:
                print "dropping:", chosen_item.name,[x.name for x in player.fighter.inventory]
                player.fighter.inventory.remove(chosen_item)
                chosen_item.owner = None
                chosen_item.x = player.x
                chosen_item.y = player.y
                objects.append(chosen_item)
                message("You dropped the " + chosen_item.name, libtcod.light_violet)
                print "dropped:", chosen_item.name,[x.name for x in player.fighter.inventory]

            else:
                return 'didnt-take-turn'
            
        else:
            return 'didnt-take-turn'


# Sets up font for Console
libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

# Init Console Window
libtcod.console_init_root(SCREEN_WIDTH,SCREEN_HEIGHT, 'CIS', False)

# Creating off-screen console for main scree
con = libtcod.console_new(MAP_WIDTH,MAP_HEIGHT)

# Creating off screen console for UI
panel = libtcod.console_new(SCREEN_WIDTH,PANEL_HEIGHT)

# Sets FPS limit (only affects realtime)
libtcod.sys_set_fps(LIMIT_FPS)

# Sets player
social = libtcod.random_get_int(0,25,100)
hunger = libtcod.random_get_int(0,25,100)
thirst = libtcod.random_get_int(0,25,100)
bladder = libtcod.random_get_int(0,75,100)
bowels = libtcod.random_get_int(0,75,100)
energy = libtcod.random_get_int(0,25,100)

fighter_component = Fighter(social=social, hunger=hunger, thirst=thirst, bladder=bladder, bowels=bowels, energy=energy, traits=None, death_function=player_death)
player = Object('player',SCREEN_WIDTH/2,SCREEN_HEIGHT/2,'@',libtcod.white, blocks = True, fighter=fighter_component, satisfies=['social'], state='idle')

COWORKERS.append(player)

objects = [player]
game_msgs = []

# Generates Map
make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

path_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(path_map, x, y, not map[x][y].block_sight, not is_blocked(x,y))

fov_recompute = True
game_state = 'playing'
player_action = None
mouse = libtcod.Mouse()
key = libtcod.Key()

#a warm welcoming message!
message('Welcome to your new job...', libtcod.red)

# Sets up main loop (each pass == turn/frame) --> runs until window is closed
while not libtcod.console_is_window_closed():
    
    libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
    
    render_all()
    
    libtcod.console_blit(con, 0,0, SCREEN_WIDTH,SCREEN_HEIGHT, 0,0,0) # Writing offscreen console to main console
    
    # Calls key function.  Only returns True is exit is hit
    player_action = handle_keys()
    
    # Need to remove didn't take turn check for realtime & fix key response
    # if game_state == 'playing' and player_action != 'didnt-take-turn':
        # if player_action == 'wait':
        #     message("Player Waits...")
    if game_state == 'playing':
        if player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.fighter.tick_needs()
                    object.ai.take_turn()
                    object.fighter.check_needs()
            
            ### Inconsistent: AI ticks needs, then performs actions
            player.fighter.tick_needs()
            player.fighter.check_needs()
        
            TURN_COUNT += 1
            out.write('\n------------------------------------------------------------------\n')

    for object in objects:
        object.clear()

    for coworker in COWORKERS:
        if 'success' in coworker.state:
            coworker.state = 'idle'

    libtcod.console_flush() # Flushes console window (always at end of loop to refresh screen)

    # time.sleep(GAME_SPEED)
    if player_action == 'exit':
        break


out.close()