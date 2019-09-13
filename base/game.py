import math
import random
import textwrap

from tcod.console import Console
from tcod.event import EventDispatch
from base.enums import ObjType
from constants import (
    map_width,
    map_height,
    BAR_WIDTH,
    STATS,
    MSG_HEIGHT,
    msg_width,
    colors,
    female_names,
    male_names,
    game_objects
)
from utils import object_funcs

key_map = {
    27: "exit",
    1073741906: "up",
    1073741905: "down",
    1073741904: "left",
    1073741903: "right",
    1073741919: "num7",
    1073741920: "num8",
    1073741921: "num9",
    1073741916: "num4",
    1073741917: "num5",
    1073741918: "num6",
    1073741913: "num1",
    1073741914: "num2",
    1073741915: "num3",
    1073741923: "numPeriod"
}


class Dispatcher(EventDispatch):
    def __init__(self, app):
        self.app = app

    def ev_quit(self, event):
        raise SystemExit()

    def ev_keydown(self, event):
        self.app.handle_keys(event)

    def ev_mousebuttondown(self, event):
        print(f"X: {event.tile.x}, Y: {event.tile.y}")
        try:
            clicked_tile = self.app.get_tile(event.tile.x, event.tile.y)
            self.app.log_message(f"Items in tile: {', '.join([x.name for x in clicked_tile.contents])}")
        except IndexError:
            pass

    def ev_mousemotion(self, event):
        pass


class BaseObject():
    def __init__(self, game, name, x, y, char, color, obj_type, blocks=False, durability=100, **kwargs):
        self.game = game
        self.name = name
        self.x = x
        self.y = y
        self.char = char
        self.color = colors[color]
        self.type = ObjType[obj_type]
        self.blocks = blocks
        self.blocks_sight = blocks
        if kwargs.get("blocks_sight"):
            self.blocks_sight = kwargs.get("blocks_sight")

        self.durability = durability
        self.state = ""

    def adjacent(self):
        # Asks GameInstance "What's Next to Me?"
        return self.game.get_adjacent(self)

    def broadcast(self, message, color="white"):
        self.game.log_message(message, color)


class Item(BaseObject):
    def __init__(self, satisfies, use_func, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.satisfies = satisfies
        self.use_func_lookup = use_func
        self.owner = owner

        # Get actual function from string repr
        if self.use_func:
            self.use_func = getattr(object_funcs, self.use_func_lookup, self.use_func)

    def use(self, user):
        if self.owner and self.owner is not user:
            self.broadcast(f"{self.name} doesn't belong to {user.name}")
        else:
            wear = self.use_func(user)
            self.durability -= wear

    def use_func(self, target):
        self.broadcast(f"{self.name.capitalize} has no use!", "red")


class Vendor(BaseObject):
    '''
    Vendor's dispense items from a limited pool
    Player may choose from menu while AI will choose first to satisfy
    Vendor no longer loses durability like other items
    Instead stocks are drained
    '''
    def __init__(self, satisfies, stock, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.satisfies = satisfies
        self.owner = owner
        self.stock = stock
        self.inventory = []
        self.restock_items()

    def restock_items(self):
        for item in self.stock:
            curr_stock = len(list(filter(lambda x: x.name == item["name"], self.inventory)))
            obj_params = game_objects[item["name"]]
            obj_params.update({"game": self, "x": 0, "y": 0})
            while curr_stock < item["max_stock"]:
                curr_stock += 1
                obj = Item(**obj_params)
                self.inventory.append(obj)

    def use(self, user):
        # Render Menu if player
        if user is self.game.player:
            self.game.init_popup(self.name.capitalize(), self.inventory, self.dispense)
        else:
            # AI will choose first item to satisfy their needs
            desired = filter(lambda x: user.satisfying in x.satisfies, self.inventory)
            for item in desired:
                self.dispense(item, user)
                break

    def dispense(self, item, user=None):
        if not user:
            user = self.game.player
        # TODO: Ensure AI will always use items in inventory first
        # -- don't need them spinning their wheels with full inventories
        if user.inventory_full():
            user.broadcast(f"{user.name.capitalize()}'s inventory is full", "dark_red")
            return None
        self.inventory = list(filter(lambda x: x is not item, self.inventory))
        item.owner = user
        user.inventory.append(item)
        user.broadcast(f"{user.name.capitalize()} received {item.name}", "white")


class Mob(BaseObject):
    max_inventory = 4
    needs = ["social", "hunger", "thirst", "bladder", "bowels", "energy", "work", "mood"]

    def __init__(self, social, hunger, thirst, bladder, bowels, energy, gender, job, work_objs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.social = social
        self.hunger = hunger
        self.thirst = thirst
        self.bladder = bladder
        self.bowels = bowels
        self.energy = energy
        self.work = 50
        self.mood = 100

        self.gender = gender
        self.job = job
        self.work_objs = work_objs
        self.inventory = []
        self.path = []

        # AI Controls
        # - target: That which the AI moves towards and plans to use
        # - satisfying: The goal to be fulfilled upon usage
        self.target = None
        self.satisfying = None
        self.fired = False
        self.occupied = 0

        self.max_social = 100
        self.max_hunger = 100
        self.max_thirst = 100
        self.max_bladder = 100
        self.max_bowels = 100
        self.max_energy = 100

        self.max_mood = 100
        self.max_work = 100

        self.social_gain = int(self.max_social * 0.2)
        self.social_drain = -1
        self.hunger_drain = -1
        self.thirst_drain = -2
        self.bladder_drain = -2
        self.bowels_drain = -1
        self.energy_drain = -1

        self.mood_drain = 0
        self.work_drain = -1

    def determine_closest(self, targets):
        min_distance = None
        closest = None
        targets = filter(lambda x: not x.owner or x.owner is self, targets)
        for target in targets:
            # If no empty tiles, occupado
            empty_tiles = list(filter(lambda x: not x.blocked, self.game.get_adjacent(target)))
            if not empty_tiles:
                continue

            dx = target.x - self.x
            dy = target.y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            if min_distance is None or distance < min_distance:
                min_distance = distance
                closest = target

        return closest

    def check_needs(self):
        if not self.target:
            lowest_status = 1
            for need in self.needs:
                if need == "social":
                    continue
                perc = getattr(self, need) / getattr(self, f"max_{need}")
                if perc < lowest_status:
                    lowest_status = perc
                    self.satisfying = need

            # First check inventory
            in_inv = list(filter(lambda x: self.satisfying in x.satisfies, self.inventory))
            if in_inv:
                self.use_item(in_inv[0])
                return None

            targets = self.game.find_need(self.satisfying)
            self.target = self.determine_closest(targets)
            if not self.target:
                self.broadcast(f"{self.name} can't satisfy {self.satisfying}")
            else:
                self.state = f"satisfying {self.satisfying}"
                self.path = self.game.find_path(self, self.target)
                if not self.path:
                    self.broadcast(f"{self.name} can't path to {self.target.name} {self.target.x}, {self.target.y}")
                    self.target = None
                    self.state = ""

    def tick_needs(self):
        self.make_occupied(-1)
        if not self.game.turns % 4:
            self.mood_drain = 0
            for need in self.needs:
                # Mood is ticked last - dependent on others
                if need == "mood":
                    continue
                setattr(self, need, max(getattr(self, f"{need}_drain") + getattr(self, need), 0))
                if getattr(self, need) == 0:
                    self.mood_drain -= 1

            # Draining mood based on unfufilled needs
            self.mood += self.mood_drain
            if self.work <= 0:
                object_funcs.mob_fired(self)

            if self.mood <= 0:
                object_funcs.mob_quits(self)

            if self.bladder <= 0:
                urine = game_objects["Urine"]
                self.game.create_object(self.x, self.y, urine)
                self.bladder = self.max_bladder

            if self.bowels <= 0:
                poo = game_objects["Poo"]
                self.game.create_object(self.x, self.y, poo)
                self.bowels = self.max_bowels

    def take_turn(self):
        if self.fired:
            return None

        self.tick_needs()
        # If not preoccupied, check needs and do stuff
        if not self.occupied:
            self.check_needs()
            self.move_to_target()

    def make_occupied(self, duration):
        self.occupied = max(self.occupied + duration, 0)
        if self.occupied:
            self.char = '?'
        else:
            self.char = '@'

    def move_to_target(self):
        if not self.target:
            return None

        # Dest. has been reached -> use target
        if not self.path:
            next_tile = self.game.get_tile(self.target.x, self.target.y)
            self.move(next_tile)
            self.target = None
            self.state = ""
            return None

        next_tile = self.game.get_tile(*self.path[0])
        if not next_tile.blocked:
            self.move(next_tile)
            self.path.pop(0)
        else:
            self.broadcast(f"{self.name} is waiting...")

    def move(self, dest_tile):
        if not dest_tile.blocked:
            self.game.remove_tile_content(self)
            self.game.update_pathmap(self.x, self.y)
            self.x = dest_tile.x
            self.y = dest_tile.y
            self.game.add_tile_content(self)
            self.game.update_pathmap(self.x, self.y)
        else:
            # Assumes one usable object per tile
            appliances = [c for c in dest_tile.contents if getattr(c, "use", None)]
            if appliances:
                appliances[0].use(self)

    def use_item(self, item):
        item.use(self)
        if not item.durability:
            self.inventory = list(filter(lambda x: x is not item, self.inventory))
            del item

    def pickup_item(self, item):
        self.game.remove_tile_content(item)
        self.inventory.append(item)

    def drop_item(self, item):
        self.inventory = list(filter(lambda x: x is not item, self.inventory))
        item.x, item.y = self.x, self.y
        self.game.add_tile_content(item)

    def inventory_full(self):
        return len(self.inventory) == self.max_inventory


class PopUpMenu():
    popup_width = map_width // 2
    popup_height = map_height // 2
    popup = Console(popup_width, popup_height)

    title = "Offscreen Console"
    text = ""

    @classmethod
    def render_content(cls):
        cls.popup.clear()
        cls.popup.draw_frame(
            0,
            0,
            cls.popup_width,
            cls.popup_height,
            cls.title,
            False,
            fg=colors["white"],
            bg=colors["black"],
        )

        cls.popup.print_box(
            1,
            2,
            cls.popup_width - 2,
            cls.popup_height,
            cls.text,
            fg=colors["white"],
            bg=None,
            # alignment=tcod.CENTER,
        )

    @classmethod
    def load_options(cls, title, options):
        cls.title = title
        cls.text = ""
        letter_index = ord('a')
        for option_text in options:
            cls.text += f"{chr(letter_index)}: {option_text}\n"
            letter_index += 1
        cls.text += "x: Exit"

    @classmethod
    def draw_popup(cls, root):
        cls.render_content()
        cls.popup.blit(
            root,
            10,
            10,
            0,
            0,
            cls.popup_width,
            cls.popup_height,
            1.0,
            0.9,
        )


class GameInstance():
    def __init__(self, root_console):
        self.root_console = root_console

        # Creating off screen console for UI - allows for alpha transparency
        self.popup = PopUpMenu
        self.popup_open = False

        self.world_objs = {
            ObjType.static: [],
            ObjType.appliance: [],
            ObjType.vendor: [],
            ObjType.item: [],
            ObjType.mob: []
        }

        self.game_msgs = []
        self.turns = 0

    def run_coworkers(self):
        self.turns += 1
        for worker in self.world_objs[ObjType.mob]:
            if worker is self.player:
                worker.tick_needs()
                continue
            worker.take_turn()

    def render_all(self):
        for obj_type in self.world_objs:
            for obj in self.world_objs[obj_type]:
                self.render(obj)

        if self.popup_open:
            self.render_popup()

    def render(self, obj):
        self.root_console.print(x=obj.x, y=obj.y, string=obj.char, fg=obj.color, bg=colors["black"])

    def render_bars(self):
        for i, stat in enumerate(STATS):
            self.render_bar(i+1, *stat)

    def render_bar(self, count, stat, color):
        x = 1
        y = map_height + count
        val = getattr(self.player, stat)
        top = getattr(self.player, f"max_{stat}")
        ratio = val / top
        filled = int(BAR_WIDTH * ratio)
        if count > 4:
            x = BAR_WIDTH + 1
            y = y - 4
        self.root_console.draw_rect(
            x=x, y=y,
            width=BAR_WIDTH,
            height=1,
            ch=0,
            fg=colors["black"],
            bg=colors[f"dark_{color}"]
        )
        self.root_console.draw_rect(
            x=x, y=y,
            width=filled,
            height=1,
            ch=0,
            fg=colors["black"],
            bg=colors[f"light_{color}"]
        )
        self.root_console.print(x=x + 1, y=y, string=f"{stat.capitalize()}: {val} / {top}")

    def render_messages(self):
        x = int(BAR_WIDTH * 2) + 1
        y = map_height
        for msg in self.game_msgs:
            y += 1
            self.root_console.print(x=x + 1, y=y, string=msg[0], fg=colors[msg[1]])

    def log_message(self, new_msg, color="white"):
        new_msg_lines = textwrap.wrap(new_msg, msg_width)
        for line in new_msg_lines:
            if len(self.game_msgs) == MSG_HEIGHT:
                self.game_msgs.pop(0)
            self.game_msgs.append((line, color))

    def render_popup(self):
        self.popup.draw_popup(self.root_console)

    def init_popup(self, title, options, popup_func):
        self.popup_open = True
        self.popup_options = options
        self.popup_func = popup_func
        self.popup.load_options(title, [x.name for x in self.popup_options])

    def find_need(self, need):
        satisfies = []
        for obj_type in [ObjType.appliance, ObjType.vendor, ObjType.item]:
            for obj in self.world_objs[obj_type]:
                if need in obj.satisfies:
                    satisfies.append(obj)

        return satisfies

    def find_path(self, seeker, target):
        # Pathing to first empty adjacent tile of target
        empty_tiles = list(filter(lambda x: not x.blocked, self.get_adjacent(target)))
        path = self.game_map.path_map.get_path(seeker.x, seeker.y, empty_tiles[0].x, empty_tiles[0].y)
        return path

    def update_pathmap(self, x, y):
        # Flips pathmap flags
        if self.game_map.path_map.cost[x, y]:
            self.game_map.path_map.cost[x, y] = 0
        else:
            self.game_map.path_map.cost[x, y] = 1

    def player_move_or_use(self, mod_x, mod_y):
        if self.player.occupied:
            return None

        dest_x = self.player.x + mod_x
        dest_y = self.player.y + mod_y
        dest_tile = self.get_tile(dest_x, dest_y)
        self.player.move(dest_tile)

    def get_tile(self, req_x, req_y):
        return self.game_map.get_tile(req_x, req_y)

    def get_adjacent(self, obj):
        # Routes Adjacent requests of Objects through game_map to get Adjacent Tiles
        return self.game_map.get_adjacent_tiles(obj)

    def add_tile_content(self, obj):
        self.game_map.place_object(obj)
        self.world_objs[obj.type].append(obj)

    def remove_tile_content(self, obj):
        self.game_map.remove_object(obj)
        self.world_objs[obj.type] = list(filter(lambda x: x is not obj, self.world_objs[obj.type]))

    def delete_object(self, obj):
        self.remove_tile_content(obj)
        del obj

    def create_object(self, x, y, obj_params):
        obj_params.update({"game": self, "x": x, "y": y})

        if obj_params["obj_type"] == "static":
            obj = BaseObject(**obj_params)
        elif obj_params["obj_type"] == "item":
            obj = Item(**obj_params)
        elif obj_params["obj_type"] == "appliance":
            obj = Item(**obj_params)
        elif obj_params["obj_type"] == "vendor":
            obj = Vendor(**obj_params)
        elif obj_params["obj_type"] == "mob":
            obj = Mob(**obj_params)

        self.add_tile_content(obj)

        return obj

    def create_coworker(self, x, y, creating_player=False):
        params = {
            "char": "@",
            "satisfies": ['social'],
            "blocks": True,
            "obj_type": "mob",
            "social": random.randint(25, 100),
            "hunger": random.randint(25, 100),
            "thirst": random.randint(25, 100),
            "bladder": random.randint(75, 100),
            "bowels": random.randint(75, 100),
            "energy": random.randint(25, 100)
        }

        if random.randint(0, 100) < 61:
            params["gender"] = "female"
            params["name"] = female_names[random.randrange(0, len(female_names))]
        else:
            params["gender"] = "male"
            params["name"] = male_names[random.randrange(0, len(male_names))]

        # Rolling Dice on special jobs
        # TODO: Move special jobs out into Defs
        if not creating_player and random.randint(0, 100) < 26:
            if random.randint(0, 100) < 50:
                params["job"] = "maintenance"
                params["color"] = "light_blue"
                params["work_objs"] = [
                    'Toilet', 'Urinal', 'Sink', 'Coffee Maker', 'Microwave', 'Refrigerator', 'Vending Machine'
                ]

            else:
                params["job"] = "it"
                params["color"] = "light_green"
                params["work_objs"] = ['Terminal']

        # Player will always have standard job for now
        else:
            params["job"] = "standard"
            params["color"] = "light_yellow"
            params["work_objs"] = ['Terminal', 'Desk']

        if creating_player:
            params["color"] = "white"

        coworker = self.create_object(x, y, params)
        return coworker

    # Sets up key_bindings
    def handle_keys(self, event):
        key = event.sym
        print(event)

        # Handle pop up options
        if self.popup_open:
            if key_map.get(key) == "exit" or key == ord("x"):
                self.popup_open = False
                return False

            opt_index = key - ord('a')
            choice = self.popup_options[opt_index]
            self.popup_func(choice)
            self.popup_open = False

        # Handle Std game events
        else:
            if key_map.get(key) == "exit":
                raise SystemExit()

            if key_map.get(key) in ("up", "num8"):
                self.player_move_or_use(0, -1)

            elif key_map.get(key) == "num7":
                self.player_move_or_use(-1, -1)

            elif key_map.get(key) == "num9":
                self.player_move_or_use(1, -1)

            elif key_map.get(key) == "num1":
                self.player_move_or_use(-1, 1)

            if key_map.get(key) in ("down", "num2"):
                self.player_move_or_use(0, 1)

            elif key_map.get(key) == "num3":
                self.player_move_or_use(1, 1)

            if key_map.get(key) in ("right", "num6"):
                self.player_move_or_use(1, 0)

            if key_map.get(key) in ("left", "num4"):
                self.player_move_or_use(-1, 0)

            elif key == ord("."):
                pass

            elif key == ord("i"):
                self.init_popup("Inventory", self.player.inventory, self.player.use_item)

            elif key == ord("g"):
                self.init_popup(
                    "Pick Up Item",
                    self.get_tile(self.player.x, self.player.y).contents,
                    self.player.pickup_item
                )

            elif key == ord("d"):
                self.init_popup(
                    "Drop Item",
                    self.player.inventory,
                    self.player.drop_item
                )
