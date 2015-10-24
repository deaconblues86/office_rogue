import libtcodpy as libtcod
import math
import textwrap
from traits import *


# Class defining room tiles
class Tile:
    
    def __init__(self, blocked, block_sight = None, ttype = None):
        self.blocked = blocked  # If True, disallows passage - default during world gen
        self.explored = False   # If True, tile will be displayed - False during world gen.  Controlled by fov_map in render_all
        self.ttype = ttype
        
        if block_sight is None: block_sight = blocked  # Defaults block sight to blocked unless otherwise specified (opaque object assumed)
        self.block_sight = block_sight


# Calss defining rectangular room
class Rect:
    
    def __init__(self,x,y,w,h):
        self.x1 = x
        self.y1 = y
        
        self.x2 = x+w
        self.y2 = y+h
        
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
        
        for x in range(self.x1,self.x2):
            edges.append((x,self.y1))
            edges.append((x,self.y2))
        for y in range(self.y1,self.y2):
            edges.append((self.x1,y))
            edges.append((self.x2,y))
        return edges
    
    def get_tiles(self):
        all_tiles = []
        for x in range(self.x1,self.x2):
            for y in range(self.y1,self.y2):
                all_tiles.append((x,y))
        
        return all_tiles


def mark_edges(coords):
    for (x,y) in coords:
        obj = Object('marker',x, y, 'X',libtcod.light_red)
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
        rows.insert(0,r)
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
            val, rows = room_flip(rows,flip, x_int, y_int)
            if val == '#': 
                map[x][y].blocked = True
                map[x][y].block_sight = True
            else:
                if val == 'T':
                    obj = Object('Toilet', x, y, val, libtcod.white)
                    objects.append(obj)
                elif val == 'U':
                    obj = Object('Urinal', x, y, val, libtcod.white)
                    objects.append(obj)
                elif val == '+':
                    obj = Object('Door', x, y, val, libtcod.light_grey)
                    objects.append(obj)
                elif val == 'H':
                    obj = Object('Sink', x, y, val, libtcod.white, blocks=True)
                    objects.append(obj)
                elif val == 'W' and rtype == 'bath':
                    obj = Object('tag', x, y, val, libtcod.pink)
                    objects.append(obj)
                elif val == 'M' and rtype == 'bath':
                    obj = Object('tag', x, y, val, libtcod.light_blue)
                    objects.append(obj)
                elif val == 't':
                    obj = Object('Terminal', x, y, val, libtcod.light_green, blocks=True)
                    objects.append(obj)
                elif val == 'M' and rtype == 'cafe':
                    obj = Object('Microwave', x, y, val, libtcod.orange, blocks=True)
                    objects.append(obj)
                elif val == 'F':
                    obj = Object('Refrigerator', x, y, val, libtcod.blue, blocks=True)
                    objects.append(obj)
                elif val == 'C':
                    obj = Object('Coffee Maker', x, y, val, libtcod.yellow, blocks=True)
                    objects.append(obj)
                elif val == 'V':
                    obj = Object('Vending Machine', x, y, val, libtcod.yellow, blocks=True)
                    objects.append(obj)
                elif val == '=':
                    obj = Object('Desk', x, y, val, libtcod.yellow, blocks=True)
                    objects.append(obj)
                elif val == 'x':
                    obj = Object('Chair', x, y, val, libtcod.dark_yellow, blocks=True)
                    objects.append(obj)
                elif val == 'S':
                    obj = Object('Supply Closet', x, y, val, libtcod.yellow, blocks=True)
                    objects.append(obj)
                elif val == '~':
                    map[x][y].ttype = 'grass'
                
                map[x][y].blocked = False
                map[x][y].block_sight = False

def create_hall(hall):
    global map
    print range(hall.x1, hall.x2 + 1)
    for x in range(hall.x1, hall.x2 + 1):
        for y in range(hall.y1,hall.y2 + 1):
            map[x][y].blocked = False
            map[x][y].block_sight = False


def room_fill(x,y,max_w):
    possible_rooms = []
    for r in room_types:
        w = len(room_types[r][0]) - 1
        h = len(room_types[r]) - 1
        
        if w > max_w and h > max_w:
            continue
        elif w > max_w and h <= max_w: 
            new_room = Rect(x,y,h,w)
            if new_room.y2 < INSIDE.y2:
                flip = libtcod.random_get_int(0, 0, 49)
                possible_rooms.append((new_room,r,flip,'man_rotate'))
        elif w <= max_w and h > max_w:
            new_room = Rect(x,y,w,h)
            if new_room.y2 < INSIDE.y2:
                flip = libtcod.random_get_int(0, 51, 100)
                possible_rooms.append((new_room,r,flip,'man_nat'))
        else:
            flip = libtcod.random_get_int(0, 0, 100)
            if flip < 50:
                new_room = Rect(x,y,h,w)
                if new_room.y2 < INSIDE.y2:
                    possible_rooms.append((new_room,r,flip,'auto_rotate'))
            else:
                new_room = Rect(x,y,w,h)
                if new_room.y2 < INSIDE.y2:
                    possible_rooms.append((new_room,r,flip,'auto_nat'))

    return possible_rooms

def make_map():
    global map, player
    
    map = [[Tile(True) for y in range(MAP_HEIGHT) ] for x in range(MAP_WIDTH)]
   
    inside_tiles = INSIDE.get_tiles()
    for x in range(MAP_WIDTH):
        for y in range(MAP_HEIGHT):
            if (x,y) not in inside_tiles:
                map[x][y].blocked = False
                map[x][y].block_sight = False
                map[x][y].ttype = 'grass'
    
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
        
        if flip < 50:
            if num_rooms != 0:
                # Going back two to skip horizontal hall
                prev_h = rooms[-2].h
                hall_height = max([prev_h,w])
                hall = Rect(x,y,HALL - 1,hall_height)
                
                if hall.x2 < INSIDE.x2:
                    create_hall(hall)
                    rooms.append(hall)
                    x += HALL
                
            new_room = Rect(x,y,h,w)
        else:
            if num_rooms != 0:
                prev_h = rooms[-2].h
                hall_height = max([prev_h,h])
                hall = Rect(x,y,HALL - 1,hall_height)
                
                if hall.x2 < INSIDE.x2:
                    create_hall(hall)
                    rooms.append(hall)
                    x += HALL
                
            new_room = Rect(x, y, w, h)
        
        print new_room.x1,new_room.x2,new_room.y1,new_room.y2
        
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                print 'intersect'
                break
        
        if new_room.x2 > INSIDE.x2:
            failed = True
            print 'outside - starting next_row'
            next_row = True
            
            
        if not failed:
            create_room(new_room,rtype,flip)
            rooms.append(new_room)
            num_rooms += 1
            
            hall = Rect(new_room.x1,new_room.y2 + 1,new_room.w ,HALL - 1)
            
            if hall.y2 < INSIDE.y2:
                create_hall(hall)
                h_halls.append(hall)
                rooms.append(hall)
        
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
                        prev_x = rooms[-1].x2 #+ 1
                    
                    possible_rooms = room_fill(prev_x,hall.y2+1,diff_x)
                    
                    print possible_rooms
                    if possible_rooms != []:
                        picked_index = libtcod.random_get_int(0, 0, len(possible_rooms)-1)
                        picked_room = possible_rooms[picked_index]
                    
                        create_room(picked_room[0],picked_room[1],picked_room[2])
                        rooms.append(picked_room[0])
                        
                        heights.append(picked_room[0].y2)
                        
                        diff_x = max_x - picked_room[0].x2
                    
                    else:
                        break
                
                if heights != []:
                    max_height = max(heights)
                    new_hall = Rect(hall.x1,max_height + 1,hall.w,HALL - 1)
                    if new_hall.y2 < INSIDE.y2:
                        create_hall(new_hall)
                        h_halls.append(new_hall)
                
                
                
                building = False


def is_blocked(x, y):
    if map[x][y].blocked:
        return True
    
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
    
    return False



def coworker_gen(x,y):
    x = int(x)
    y = int(y)
    
    fighter_component = Fighter(social=30, hunger=30, thirst=30, bladder=30, bowels=30, energy=30, traits=None, death_function=player_death)
    ai_component = BasicCoworker()
                
    for stat in ('social', 'hunger', 'thirst', 'bladder', 'bowels', 'energy'):
        fighter_component.stat = libtcod.random_get_int(0,15,30)
    
    if libtcod.random_get_int(0,0,100) < 61:
        name_file = open('defs/female_names.txt')
        names = [n.strip() for n in name_file.readlines()]
        name = names[libtcod.random_get_int(0,0,len(names)-1)]
        
        coworker = Object(name,x,y,'@',libtcod.pink,blocks=True,fighter=fighter_component,ai=ai_component)
    
    else:
        name_file = open('defs/male_names.txt')
        names = [n.strip() for n in name_file.readlines()]
        name = names[libtcod.random_get_int(0,0,len(names)-1)]
        
        coworker = Object(name,x,y,'@',libtcod.light_blue,blocks=True,fighter=fighter_component,ai=ai_component)
    
    name_file.close()
    return coworker

def place_objects(room):
    num_monsters = libtcod.random_get_int(0,0,MAX_ROOM_MONSTERS)
    
    for i in range(num_monsters):
        x = libtcod.random_get_int(0,room.x1,room.x2)
        y = libtcod.random_get_int(0,room.y1,room.y2)
        
        if not is_blocked(x,y):
            objects.append(coworker_gen(x,y))


#-----------------------------------------
# Setting up MAP and SCREEN Attributes   |
#-----------------------------------------

# Defining Layout variables for Map Gen
ROOM_SECTOR_X = 22
ROOM_SECTOR_Y = 22
HALL = 3
OUTSIDE_BORDER = 3

MAX_ROOMS = 4
MAP_WIDTH = 0
MAP_HEIGHT = 0

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

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

#------------------------------
# FOV attributes              |
#------------------------------

FOV_ALGO = 0            # Algorithm
FOV_LIGHT_WALLS = True  # Change Wall Colors?
TORCH_RADIUS = 10       # Range

\

#------------------------------
# Game attributes             |
#------------------------------

MAX_ROOM_MONSTERS = 3


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
    
    def __init__(self, name, x, y, char, color, blocks=False, fighter=None, ai=None, state="idle"):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks = blocks
        self.fighter = fighter
        self.ai = ai
        self.state = state
        
    
        # Passes Parent level attibutes to Child class
        if self.fighter:
            self.fighter.owner = self
        if self.ai:
            self.ai.owner = self
    
    def move(self, dx, dy):
        if not is_blocked(self.x + dx,self.y + dy):
            self.x += dx
            self.y += dy
        else:
            return 'is_blocked'
    
    def move_towards(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        # path = libtcod.path_new_using_function(MAP_WIDTH,MAP_HEIGHT,path_func)
        # libtcod.path_compute(path, self.x, self.y, target_x, target_y)
        # new_x, new_y = libtcod.path_get(path,0)
        # self.move(new_x, new_y)
        
        # Normalize to 1 (preserving direction)
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        
        # If Shortest path is blocked, analyze surrounding tiles for shortest unblocked path
        if self.move(dx,dy) == 'is_blocked':
            min = ''
            min_coords = ''
            for tile in self.adjacent():
                if is_blocked(tile[0],tile[1]):
                    continue
                
                new_dx = target_x - tile[0]
                new_dy = target_y - tile[1]
                distance = math.sqrt(new_dx**2 + new_dy**2)
                    
                if min == '' or distance < min:
                    min = distance
                    min_coords = (tile[0],tile[1])
            
            self.move(min_coords[0]-self.x,min_coords[1]-self.y)
                
        
    def distance_to(self, target):
        dx = target.x - self.x
        dy = target.y - self.y
        return math.sqrt(dx**2 + dy**2)
    
    def adjacent(self):
        return [(self.x-1,self.y),(self.x-1,self.y+1),(self.x,self.y+1),(self.x+1,self.y+1),(self.x+1,self.y),(self.x+1,self.y-1),(self.x,self.y-1),(self.x-1,self.y-1)]
        
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
    
    def __init__(self, social, hunger, thirst, bladder, bowels, energy, traits=None, death_function=None):
        self.max_social = social
        self.social = social
        self.social_gain = 5
        self.social_drain = -1
        
        self.max_hunger = hunger
        self.hunger = hunger
        self.hunger_gain = 0
        self.hunger_drain = -1
        
        self.max_thirst = thirst
        self.thirst = thirst
        self.thirst_gain = 0
        self.thirst_drain = -1
        
        self.max_bladder = bladder
        self.bladder = 0
        self.bladder_gain = 1
        self.bladder_drain = 0
        
        self.max_bowels = bowels
        self.bowels = 0
        self.bowels_gain = 1
        self.bowels_drain = 0
        
        self.max_energy = energy
        self.energy = energy
        self.energy_gain = 0
        self.energy_drain = -1
        
        self.max_work = 100
        self.work = 50
        
        self.needs = [self.social,
                 self.hunger,
                 self.thirst,
                 self.bladder,
                 self.bowels,
                 self.energy,
                 self.work,
                ]
        
        self.greeted = False
        self.death_function = death_function
    
        if traits:
            if type(traits) == list():
                for trait_func in traits:
                    trait_func(self.owner)
            else:
                trait_func(self.owner)
        
    def take_social(self,social_gain):
        if social_gain > 0:
            self.social += social_gain
        
    def check_work(self,work):
        if self.work == 0:
            function = self.death_function
            if function is not None:
                function(self.owner)
    
    def give_social(self, target):
        
        if target.fighter.social > self.social:
            self.social += self.social_gain
            message(self.owner.name.capitalize() + ' chats with ' + target.name + ' for ' + str(self.social_gain))
            target.fighter.take_social(self.social_gain)
        
        elif target.fighter.social <= self.social:
            gain = max([self.social_gain,target.fighter.social_gain])
            self.social += gain
            message(self.owner.name.capitalize() + ' engages in conversation with ' + target.name + ' for ' + str(gain))
            target.fighter.take_social(target.fighter.social_gain)
    
    def tick_needs(self):
        self.social += self.social_drain
        self.hunger += self.hunger_drain
        self.thirst += self.thirst_drain
        self.bladder += self.bladder_gain
        self.bowels += self.bowels_gain
        self.energy += self.energy_drain
        
class BasicCoworker:
    
    def take_turn(self):
        
        coworker = self.owner
        
        if libtcod.map_is_in_fov(fov_map, coworker.x, coworker.y) and coworker.fighter.greeted == False:
            coworker.fighter.greeted = True
            message(coworker.name + " says hi!")
        
        if coworker.fighter.social < (coworker.fighter.social / 2):
            coworker.state = 'chatting'
            min = ''
            closest_obj = ''
            for obj in objects:
                if not obj.fighter:
                    continue
                
                if obj == coworker:
                    continue
                
                dx = obj.x - coworker.x
                dy = obj.y - coworker.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if min == '' or distance < min:
                    min = distance
                    closest_obj = obj
          
            if coworker.distance_to(closest_obj) >= 2:
                coworker.move_towards(closest_obj.x, closest_obj.y)
    
            elif coworker.fighter.social < 0:
                coworker.fighter.give_social(closest_obj)
        else:
            coworker.state = 'idle'
            dir = libtcod.random_get_int(0,0,9)
                
            if dir == 8:
                coworker.move(0,-1)
            elif dir == 7:
                coworker.move(-1,-1) 
            elif dir == 9: 
                coworker.move(1,-1)
            elif dir == 1:
                coworker.move(-1,1)            
            elif dir == 2:
                coworker.move(0,1)
            elif dir == 3:
                coworker.move(1,1)  
            elif dir == 6:
                coworker.move(1,0)
            elif dir == 4:
                coworker.move(-1,0)
            else:
                coworker.move(0,0)
  


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
    render_bar(1, 1, BAR_WIDTH, 'Social: ', player.fighter.social, player.fighter.max_social, libtcod.black, libtcod.light_yellow, libtcod.darker_yellow)
    libtcod.console_set_default_background(panel, libtcod.black)
    
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_set_default_background(panel, libtcod.black)
    
    libtcod.console_set_default_foreground(panel, libtcod.light_grey)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
    
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0,0,PANEL_Y)


def message(new_msg, color = libtcod.white):
    
    # Wrap Lines appropriately
    new_msg_lines = textwrap.wrap(new_msg,MSG_WIDTH)
    
    for line in new_msg_lines:
        if len(game_msgs) == MSG_HEIGHT:
            game_msgs.pop(0)
        
        game_msgs.append((line,color))
    


def player_move_or_attack(dx,dy):
    global fov_recompute
    x = player.x + dx
    y = player.y + dy
    
    target = None
    for object in objects:
        if object.x == x and object.y == y and object.fighter:
            target = object
            break
    
    if target is not None:
        player.fighter.give_social(target)
    
    else:
        player.move(dx,dy)
        fov_recompute = True

def player_death(player):
    global game_state
    message("You're Fired!",libtcod.red)
    game_state = 'dead'
    
    player.char = '%'
    player.color = libtcod.dark_red

def monster_death(monster):
    message(monster.name.capitalize() + ' is fired!',libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()

def get_names_under_mouse():
    global mouse
    
    (x,y) = (mouse.cx, mouse.cy)
    names = [obj.name for obj in objects if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x,obj.y)]
    names = ', '.join(names)
    return names.capitalize()

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
fighter_component = Fighter(social=30, hunger=30, thirst=30, bladder=30, bowels=30, energy=30, traits=None, death_function=player_death)
player = Object('player',SCREEN_WIDTH/2,SCREEN_HEIGHT/2,'@',libtcod.white, blocks = True, fighter=fighter_component)

objects = [player]
game_msgs = []

# Generates Map
make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

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
    libtcod.console_flush() # Flushes console window (always at end of loop to refresh screen)
    
    for object in objects:
        object.clear()
    
    # Calls key function.  Only returns True is exit is hit
    player_action = handle_keys()
    
    # Need to remove didn't take turn check for realtime & fix key response
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        if player_action == 'wait':
            message("Player Waits...")
        for object in objects:
            if object.ai:
                object.ai.take_turn()
                object.fighter.tick_needs()
        
        player.fighter.tick_needs()
    
    if player_action == 'exit':
        break
    