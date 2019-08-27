import tcod as libtcod
import math
import textwrap

# Params for Console
SCREEN_WIDTH = 90
SCREEN_HEIGHT = 50
LIMIT_FPS = 20

# Map attributes
MAP_WIDTH = 80
MAP_HEIGHT = 43
ROOM_SIZE_MAX = 10
ROOM_SIZE_MIN = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2
HEAL_AMOUNT = 4
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5

# Panel attributes
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

INVENTORY_WIDTH = 50

# FOV attributes
FOV_ALGO = 0  # Algorithm
FOV_LIGHT_WALLS = True  # Change Wall Colors?
TORCH_RADIUS = 10  # Range

color_dark_walls = libtcod.grey
color_dark_ground = libtcod.grey
color_light_walls = libtcod.white
color_light_ground = libtcod.white


# color_dark_walls = libtcod.Color(0,0,100)
# color_dark_ground = libtcod.Color(50,50,150)
# color_light_walls = libtcod.Color(130,110,50)
# color_light_ground = libtcod.Color(200,180,50)


# Class defining room tiles
class Tile:
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked  # If True, disallows passage - default during world gen
        self.explored = (
            False
        )  # If True, tile will be displayed - False during world gen.  Controlled by fov_map in render_all

        if block_sight is None:
            block_sight = (
                blocked
            )  # Defaults block sight to blocked unless otherwise specified (opaque object assumed)
        self.block_sight = block_sight


# Calss defining rectangular room
class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    # Center and Intersect used during world gen
    def center(self):
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)
        return (center_x, center_y)

    def intersect(self, other):
        # Returns true if it overlaps
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )


class Object:
    def __init__(
        self, name, x, y, char, color, blocks=False, fighter=None, ai=None, item=None
    ):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks = blocks
        self.fighter = fighter
        self.ai = ai
        self.item = item

        # Passes Parent level attibutes to Child class
        if self.fighter:
            self.fighter.owner = self
        if self.ai:
            self.ai.owner = self
        if self.item:
            self.item.owner = self

    def move(self, dx, dy):
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
        else:
            return "is_blocked"

    def move_towards(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        # Normalize to 1 (preserving direction)
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        # If Shortest path is blocked, analyze surrounding tiles for shortest unblocked path
        if self.move(dx, dy) == "is_blocked":
            min = ""
            min_coords = ""
            for tile in self.adjacent():
                if is_blocked(tile[0], tile[1]):
                    continue

                new_dx = target_x - tile[0]
                new_dy = target_y - tile[1]
                distance = math.sqrt(new_dx ** 2 + new_dy ** 2)

                if min == "" or distance < min:
                    min = distance
                    min_coords = (tile[0], tile[1])

            self.move(min_coords[0] - self.x, min_coords[1] - self.y)

    def distance_to(self, target):
        dx = target.x - self.x
        dy = target.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def adjacent(self):
        return [
            (self.x - 1, self.y),
            (self.x - 1, self.y + 1),
            (self.x, self.y + 1),
            (self.x + 1, self.y + 1),
            (self.x + 1, self.y),
            (self.x + 1, self.y - 1),
            (self.x, self.y - 1),
            (self.x - 1, self.y - 1),
        ]

    def draw(self):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_set_default_foreground(
                con, self.color
            )  # Sets Font color to be white for main (0) console window
            libtcod.console_put_char(
                con, self.x, self.y, self.char, libtcod.BKGND_NONE
            )  # Prints @ to console (0 == window, 1/1 == coords)

    def send_to_back(self):
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def clear(self):
        libtcod.console_put_char(con, self.x, self.y, " ", libtcod.BKGND_NONE)


class Fighter:
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage

        if self.hp <= 0:
            function = self.death_function
            if function is not None:
                function(self.owner)

    def attack(self, target):
        damage = self.power - target.fighter.defense

        if damage > 0:
            message(
                self.owner.name.capitalize()
                + " attacks "
                + target.name
                + " for "
                + str(damage),
                libtcod.white,
            )
            target.fighter.take_damage(damage)
        else:
            message(
                self.owner.name.capitalize()
                + " attacks "
                + target.name
                + " but it has no effect.",
                libtcod.white,
            )

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp


class BasicMonster:
    def take_turn(self):
        # print 'The ' + owner.name + ' growls!'
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)

            elif player.fighter.hp > 0:
                monster.fighter.attack(player)


class Item:
    def __init__(self, use_function=None):
        self.use_function = use_function

    # Instead of accessing use_function directly when needed, a method is set up to call said function
    def use(self):
        if self.use_function == None:
            message("The" + self.owner.name + " cannot be used.")

        else:
            if self.use_function() != "cancelled":
                inventory.remove(self.owner)

    def pick_up(self):
        if len(inventory) >= 26:
            message(
                "Your inventory is full, cannot pick up " + self.owner.name + ".",
                libtcod.red,
            )
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message("You picked up a " + self.owner.name + "!", libtcod.green)


def make_map():
    global map, player, npc

    map = [[Tile(True) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]

    # map[30][22].blocked = True
    # map[30][22].block_sight = True
    # map[50][22].blocked = True
    # map[50][22].block_sight = True

    # room1 = Rect(20,15,10,15)
    # room2 = Rect(50,15,10,15)
    # create_room(room1)
    # create_room(room2)
    # create_h_tunnel(25,55,23)

    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        w = libtcod.random_get_int(0, ROOM_SIZE_MIN, ROOM_SIZE_MAX)
        h = libtcod.random_get_int(0, ROOM_SIZE_MIN, ROOM_SIZE_MAX)

        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        new_room = Rect(x, y, w, h)

        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
            if new_room.x2 > MAP_WIDTH or new_room.y2 > MAP_HEIGHT:
                failed = True
                break

        if not failed:
            create_room(new_room)

            place_objects(new_room)

            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                player.x = new_x
                player.y = new_y
            else:
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                if libtcod.random_get_int(0, 0, 1) == 1:
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

                npc.x = new_x
                npc.y = new_y

                room_no = Object(
                    "room_num", new_x, new_y, chr(65 + num_rooms), libtcod.white
                )
                objects.insert(
                    0, room_no
                )  # Inserting into objects early so others drawn on top

            rooms.append(new_room)
            num_rooms += 1


def create_room(room):
    global map
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False


def create_h_tunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False


def create_v_tunnel(y1, y2, x):
    global map
    print(type(y1))
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False


def is_blocked(x, y):
    if map[x][y].blocked:
        return True

    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False


def place_objects(room):
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)
    num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)

    for i in range(num_monsters):
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        if not is_blocked(x, y):
            if libtcod.random_get_int(0, 0, 100) < 80:
                fighter_component = Fighter(
                    hp=10, defense=0, power=3, death_function=monster_death
                )
                ai_component = BasicMonster()

                monster = Object(
                    "orc",
                    x,
                    y,
                    "O",
                    libtcod.desaturated_green,
                    blocks=True,
                    fighter=fighter_component,
                    ai=ai_component,
                )
            else:
                fighter_component = Fighter(
                    hp=16, defense=3, power=4, death_function=monster_death
                )
                ai_component = BasicMonster()

                monster = Object(
                    "troll",
                    x,
                    y,
                    "T",
                    libtcod.darker_green,
                    blocks=True,
                    fighter=fighter_component,
                    ai=ai_component,
                )

            objects.append(monster)

    for i in range(num_items):
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        if not is_blocked(x, y):

            dice = libtcod.random_get_int(0, 0, 100)
            if dice < 70:
                item_component = Item(use_function=cast_heal)
                item = Object(
                    "healing potion", x, y, "!", libtcod.violet, item=item_component
                )

            else:
                item_component = Item(use_function=cast_lightning)
                item = Object(
                    "scroll of lightning bolt",
                    x,
                    y,
                    "#",
                    libtcod.light_yellow,
                    item=item_component,
                )

            objects.append(item)
            item.send_to_back()


def player_move_or_attack(dx, dy):
    global fov_recompute
    x = player.x + dx
    y = player.y + dy

    target = None
    for object in objects:
        if object.x == x and object.y == y and object.fighter:
            target = object
            break

    if target is not None:
        player.fighter.attack(target)

    else:
        player.move(dx, dy)
        fov_recompute = True


def player_death(player):
    global game_state
    message("You Died!", libtcod.red)
    game_state = "dead"

    player.char = "%"
    player.color = libtcod.dark_red


def monster_death(monster):
    message(monster.name.capitalize() + " is dead!", libtcod.orange)
    monster.char = "%"
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = "remains of " + monster.name
    monster.send_to_back()


def cast_heal():
    if player.fighter.hp == player.fighter.max_hp:
        message("You are already at full health", libtcod.red)
        return "cancelled"
    else:
        message("Your wounds start to feel better", libtcod.light_violet)
        player.fighter.heal(HEAL_AMOUNT)


def cast_lightning():
    monster = closest_monster(LIGHTNING_RANGE)

    if monster is None:
        message("No enemey in range", libtcod.red)
        return "cancelled"

    message(
        "A lightning bolt strikes the "
        + monster.name
        + " with a loud crack for "
        + str(LIGHTNING_DAMAGE)
        + "!",
        libtcod.light_blue,
    )
    monster.fighter.take_damage(LIGHTNING_DAMAGE)


def closest_monster(max_range):
    closest_enemey = None
    closest_distance = (
        max_range + 1
    )  # Starting further out to grab only those monsters within range (since they'd be one less than this and so at max)

    for object in objects:
        if (
            object.fighter
            and not object == player
            and libtcod.map_is_in_fov(fov_map, object.x, object.y)
        ):
            dist = player.distance_to(object)
            if dist < closest_distance:
                closest_enemey = object
                closest_distance = dist

    return closest_enemey


def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    bar_width = int(float(value) / maximum * total_width)
    bar_width = min(bar_width, total_width)

    # Sets up background of bar
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    # Sets up filled value of bar
    libtcod.console_set_default_background(panel, bar_color)
    libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    # Text of actual values
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(
        panel,
        x + total_width / 2,
        y,
        libtcod.BKGND_NONE,
        libtcod.CENTER,
        name + ": " + str(value) + "/" + str(maximum),
    )


def get_names_under_mouse():
    global mouse

    # return a string with the names of all objects under the mouse
    (x, y) = (mouse.cx, mouse.cy)

    # create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [
        obj.name
        for obj in objects
        if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)
    ]

    names = ", ".join(names)  # join the names, separated by commas
    return names.capitalize()


def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute

    if fov_recompute:
        # recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(
            fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO
        )

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            visible = libtcod.map_is_in_fov(fov_map, x, y)
            wall = map[x][y].block_sight
            if not visible:
                if map[x][y].explored:
                    if wall:
                        # libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET )
                        libtcod.console_set_default_foreground(con, color_dark_walls)
                        libtcod.console_put_char(con, x, y, "#", libtcod.BKGND_NONE)
                    else:
                        # libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET )
                        libtcod.console_set_default_foreground(con, color_dark_ground)
                        libtcod.console_put_char(con, x, y, ".", libtcod.BKGND_NONE)

            else:
                map[x][y].explored = True
                if wall:
                    # libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET )
                    libtcod.console_set_default_foreground(con, color_light_walls)
                    libtcod.console_put_char(con, x, y, "#", libtcod.BKGND_NONE)
                else:
                    # libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET )
                    libtcod.console_set_default_foreground(con, color_light_ground)
                    libtcod.console_put_char(con, x, y, ".", libtcod.BKGND_NONE)

    for object in objects:
        if object != player:
            object.draw()

    player.draw()

    libtcod.console_blit(
        con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0
    )  # Writing offscreen console to main console

    # show the player's stats
    libtcod.console_clear(panel)
    render_bar(
        1,
        1,
        BAR_WIDTH,
        "HP",
        player.fighter.hp,
        player.fighter.max_hp,
        libtcod.light_red,
        libtcod.darker_red,
    )
    libtcod.console_set_default_background(panel, libtcod.black)

    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(
            panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line
        )
        y += 1

    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(
        panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse()
    )

    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)


def message(new_msg, color=libtcod.white):
    # split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        # if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        # add the new line as a tuple, with the text and the color
        game_msgs.append((line, color))


# Sets up key_bindings
def handle_keys():
    global fov_recompute, game_state, key

    # Using console_check_for_keypress() to set up delay of check
    # key = libtcod.console_check_for_keypress()

    # Replace above line with this to force hold on console till key is pressed (turn-based)
    # key = libtcod.console_wait_for_keypress(True)

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return "exit"  # Exit

    if game_state == "playing":
        # Movement keys -- using console_is_key_pressed() for realtime check of key status
        if key.vk in [libtcod.KEY_KP8, libtcod.KEY_UP]:
            player_move_or_attack(0, -1)

        elif key.vk in [libtcod.KEY_KP7]:
            player_move_or_attack(-1, -1)

        elif key.vk in [libtcod.KEY_KP9]:
            player_move_or_attack(1, -1)

        elif key.vk in [libtcod.KEY_KP1]:
            player_move_or_attack(-1, 1)

        elif key.vk in [libtcod.KEY_KP2, libtcod.KEY_DOWN]:
            player_move_or_attack(0, 1)

        elif key.vk in [libtcod.KEY_KP3]:
            player_move_or_attack(1, 1)

        elif key.vk in [libtcod.KEY_KP6, libtcod.KEY_RIGHT]:
            player_move_or_attack(1, 0)

        elif key.vk in [libtcod.KEY_KP4, libtcod.KEY_LEFT]:
            player_move_or_attack(-1, 0)

        elif key.c == ord("."):
            return "wait"

        elif key.c == ord("g"):
            for object in objects:
                if (object.x, object.y) == (player.x, player.y) and object.item:
                    object.item.pick_up()
                    break

        elif key.c == ord("i"):
            chosen_item = inventory_menu(
                "Press the specified key to use an item or any other to cancel.\n"
            )
            if chosen_item is not None:
                chosen_item.use()
            else:
                return "didnt-take-turn"

        else:
            return "didnt-take-turn"


def menu(header, options, width):
    if len(options) > 26:
        raise ValueError("Cannot have more than 26 options in a menu")

    header_height = libtcod.console_get_height_rect(
        con, 0, 0, width, SCREEN_HEIGHT, header
    )
    height = len(options) + header_height

    window = libtcod.console.Console(width, height)
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(
        window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header
    )

    y = header_height
    letter_index = ord("a")
    for option_text in options:
        text = chr(letter_index) + ": " + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    x = SCREEN_WIDTH / 2 - width / 2
    y = SCREEN_HEIGHT / 2 - height / 2
    # libtcod.console_blit(window,0,0, width, height, 0, x, y, 1.0, 0.7)
    libtcod.console_blit(window, 0, 0, width, height, 0, x, 0, 1.0, 0.7)

    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

    # Converts ASCII to index vale
    index = key.c - ord("a")
    if index >= 0 and index < len(options):
        return index
    return None


def inventory_menu(header):
    if len(inventory) == 0:
        options = ["Inventory is empty"]
    else:
        options = [item.name for item in inventory]

    index = menu(header, options, INVENTORY_WIDTH)

    if index is None or len(inventory) == 0:
        return None
    return inventory[index].item


# Sets up font for Console
libtcod.console_set_custom_font(
    "arial8x8.png", libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD
)

# Init Console Window
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, "CIS", False, renderer=libtcod.RENDERER_SDL2)

# Creating off-screen console for main scree
con = libtcod.console.Console(MAP_WIDTH, MAP_HEIGHT)

# Creating off screen console for UI
panel = libtcod.console.Console(SCREEN_WIDTH, PANEL_HEIGHT)

# Sets FPS limit (only affects realtime)
libtcod.sys_set_fps(LIMIT_FPS)

# Sets player & NPC
fighter_component = Fighter(
    hp=30, defense=3, power=5, death_function=player_death
)  # Using keyword arguments for clarity

player = Object(
    "player",
    SCREEN_WIDTH / 2,
    SCREEN_HEIGHT / 2,
    "@",
    libtcod.white,
    blocks=True,
    fighter=fighter_component,
)
npc = Object(
    "npc", SCREEN_WIDTH / 2 - 5, SCREEN_HEIGHT / 2, "@", libtcod.yellow, blocks=True
)
objects = [npc, player]

# Generates Map
make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(
            fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked
        )

fov_recompute = True


game_state = "playing"
player_action = None

# create the list of game messages and their colors, starts empty
game_msgs = []

inventory = []

# a warm welcoming message!
message(
    "Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.",
    libtcod.red,
)

mouse = libtcod.Mouse()
key = libtcod.Key()

# Sets up main loop (each pass == turn/frame) --> runs until window is closed
while not libtcod.console_is_window_closed():

    libtcod.sys_check_for_event(
        libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse
    )
    render_all()

    libtcod.console_flush()  # Flushes console window (always at end of loop to refresh screen)

    for object in objects:
        object.clear()

    # Calls key function.  Only returns True is exit is hit
    player_action = handle_keys()

    if game_state == "playing" and player_action != "didnt-take-turn":
        if player_action == "wait":
            message("Player Waits...", libtcod.light_grey)
        for object in objects:
            if object.ai:
                object.ai.take_turn()

    if player_action == "exit":
        break
