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

    def broadcast(self, message, color):
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
        wear = self.use_func(user)
        self.durability -= wear

    def use_func(self, target):
        self.broadcast(f"{self.name.capitalize} has no use!", "red")


class Vendor(BaseObject):
    def __init__(self, satisfies, stock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.satisfies = satisfies
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
        if user is self.game.player:
            self.game.init_popup(self.name.capitalize(), self.inventory, self.dispense)

    def dispense(self, item, user=None):
        if not user:
            user = self.game.player
        item.owner = user
        user.inventory.append(item)
        user.broadcast(f"{user.name.capitalize()} received {item.name}", "white")


class Mob(BaseObject):
    max_inventory = 4

    def __init__(self, social, hunger, thirst, bladder, bowels, energy, gender, job, work_objs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.social = social
        self.hunger = hunger
        self.thirst = thirst
        self.bladder = bladder
        self.bowels = bowels
        self.energy = energy
        self.work = 50

        self.gender = gender
        self.job = job
        self.work_objs = work_objs
        self.inventory = []

        self.max_social = social
        self.max_hunger = hunger
        self.max_thirst = thirst
        self.max_bladder = bladder
        self.max_bowels = bowels
        self.max_energy = energy
        self.max_work = 100

        self.social_gain = int(self.max_social * 0.2)
        self.social_drain = 1
        self.hunger_drain = -1
        self.thirst_drain = -2
        self.bladder_drain = -2
        self.bowels_drain = -1
        self.energy_drain = -1
        self.work_drain = -1

    def move(self, mod_x, mod_y):
        dest_x = self.x + mod_x
        dest_y = self.y + mod_y
        dest_tile = self.game.get_tile(dest_x, dest_y)
        if not dest_tile.blocked:
            self.game.remove_tile_content(self)
            self.x = dest_tile.x
            self.y = dest_tile.y
            self.game.add_tile_content(self)
        else:
            # Assumes one usable object per tile
            appliances = [c for c in dest_tile.contents if getattr(c, "use", None)]
            if appliances:
                appliances[0].use(self)

    def use_item(self, item):
        item.use(self)
        if not item.durability:
            self.inventory = list(filter(lambda x: x is not item, self.inventory))

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
        if count > 3:
            x = BAR_WIDTH + 1
            y = y - 3
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

    def player_move_or_use(self, x, y):
        self.player.move(x, y)

    def get_tile(self, req_x, req_y):
        return self.game_map.get_tile(req_x, req_y)

    def get_adjacent(self, obj):
        # Routes Adjacent requests of Objects through game_map to get Adjacent Tiles
        return self.game_map.get_adjacent_tiles(obj)

    def add_tile_content(self, obj):
        self.game_map.place_object(obj)
        self.world_objs[obj.type].append(obj)
        if obj.type is ObjType.item:
            print([x.name for x in self.world_objs[obj.type]])

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
            "social": random.randrange(25, 100),
            "hunger": random.randrange(25, 100),
            "thirst": random.randrange(25, 100),
            "bladder": random.randrange(75, 100),
            "bowels": random.randrange(75, 100),
            "energy": random.randrange(25, 100)
        }

        if random.randrange(0, 100) < 61:
            params["gender"] = "female"
            params["name"] = female_names[random.randrange(0, len(female_names))]
        else:
            params["gender"] = "male"
            params["name"] = male_names[random.randrange(0, len(male_names))]

        # Rolling Dice on special jobs
        # TODO: Move special jobs out into Defs
        if not creating_player and random.randrange(0, 100) < 26:
            if random.randrange(0, 100) < 50:
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
