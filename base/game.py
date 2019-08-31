from tcod.console import Console
from tcod.event import EventDispatch
from constants import colors
from utils import object_funcs
import textwrap

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
        print(event)

    def ev_mousemotion(self, event):
        pass


class BaseObject():
    def __init__(self, game, name, x, y, char, color, blocks=False, durability=100, **kwargs):
        self.game = game
        self.name = name
        self.x = x
        self.y = y
        self.char = char
        self.color = colors[color]
        self.blocks = blocks
        self.blocks_sight = blocks
        if kwargs.get("blocks_sight"):
            self.blocks_sight = kwargs.get("blocks_sight")

        self.state = ""

    def adjacent(self):
        # Asks GameInstance "What's Next to Me?"
        return self.game.get_adjacent(self)


class Item(BaseObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_func = None
        self.owner = None

        if kwargs.get("use_func"):
            self.use_func = getattr(object_funcs, kwargs.get("use_func"))


class Mob(BaseObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def move(self, mod_x, mod_y):
        dest_x = self.x + mod_x
        dest_y = self.y + mod_y
        dest_tile = self.game.get_tile(dest_x, dest_y)
        if not dest_tile.blocked:
            self.game.remove_tile_content(self)
            self.game.add_tile_content(self)
            self.x = dest_tile.x
            self.y = dest_tile.y
            print(self.x, self.y)


class GameInstance():
    def __init__(self, root_console):
        self.root_console = root_console

        # Creating off screen console for UI - allows for alpha transparency
        self.panel = Console(root_console.width, 20)

        # Creating off screen console for UI - allows for alpha transparency
        self.inventory = Console(50, root_console.height)

        self.player = Mob(self, name="Player", x=20, y=20, char="@", color="white", blocks=True)

        self.mobs = [self.player]
        self.items = []
        self.appliances = []
        self.static = []
        self.game_msgs = []

    def render_all(self):
        for obj_types in [self.static, self.appliances, self.items, self.mobs]:
            for obj in obj_types:
                self.render(obj)

    def render(self, obj):
        self.root_console.print(x=obj.x, y=obj.y, string=obj.char, fg=obj.color, bg=colors["black"])

    def player_move_or_use(self, x, y):
        self.player.move(x, y)

    def get_tile(self, req_x, req_y):
        return self.game_map.get_tile(req_x, req_y)

    def get_adjacent(self, obj):
        # Routes Adjacent requests of Objects through game_map to get Adjacent Tiles
        return self.game_map.get_adjacent_tiles(obj)

    def add_tile_content(self, obj):
        self.game_map.place_object(obj)

    def remove_tile_content(self, obj):
        self.game_map.remove_object(obj)

    def create_object(self, x, y, obj_params):
        print(obj_params)
        obj_params.update({"game": self, "x": x, "y": y})

        if obj_params["type"] == "base":
            obj = BaseObject(**obj_params)
            self.static.append(obj)
        elif obj_params["type"] == "item":
            obj = Item(**obj_params)
            self.items.append(obj)
        elif obj_params["type"] == "appliance":
            obj = Item(**obj_params)
            self.appliances.append(obj)
        elif obj_params["type"] == "mob":
            obj = Mob(**obj_params)
            self.mobs.append(obj)

        self.add_tile_content(obj)

    def create_coworker(self, x, y):
        pass

    # Sets up key_bindings
    def handle_keys(self, event):
        key = event.sym
        print(event)

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
            print("inventory")
            # chosen_item = inventory_menu(
            #     "Press the specified key to use an item or any other to cancel.\n"
            # )
            # if chosen_item is not None:
            #     print("using:", chosen_item.name)
            #     player.use_item(chosen_item)
            #     print(
            #         "used:",
            #         chosen_item.name,
            #         [x.name for x in player.fighter.inventory],
            #     )
            # else:
            # return "didnt-take-turn"

        elif key == ord("g"):
            print("pick up")
            # found = []
            # options = []
            # for obj in objects:
            #     if (obj.x, obj.y) == (player.x, player.y) and obj.item:
            #         found.append(obj)
            #         options.append(obj.name)

            # if found == []:
            #     options.append("No items to pick up...")

            # chosen_item = menu(
            #     "Press the specified key to pick up an item or any other to cancel",
            #     options,
            #     INVENTORY_WIDTH,
            # )
            # if chosen_item is not None and found != []:
            #     if len(player.fighter.inventory) < MAX_INVENTORY:
            #         print("picking:", found[chosen_item].name)
            #         player.fighter.inventory.append(found[chosen_item])
            #         objects.remove(found[chosen_item])
            #         message(
            #             "Picked up " + found[chosen_item].name, libtcod.light_violet
            #         )
            #         print(
            #             "picked:",
            #             found[chosen_item].name,
            #             [x.name for x in player.fighter.inventory],
            #         )
            #     else:
            #         message("Your Inventory is full", libtcod.dark_red)
            #         return "didnt-take-turn"

            # else:
            #     return "didnt-take-turn"

        elif key == ord("d"):
            print("drop")
            # chosen_item = inventory_menu(
            #     "Press the specified key to drop an item or any other to cancel.\n"
            # )
            # if chosen_item is not None:
            #     print(
            #         "dropping:",
            #         chosen_item.name,
            #         [x.name for x in player.fighter.inventory],
            #     )
            #     player.fighter.inventory.remove(chosen_item)
            #     chosen_item.owner = None
            #     chosen_item.x = player.x
            #     chosen_item.y = player.y
            #     objects.append(chosen_item)
            #     message("You dropped the " + chosen_item.name, libtcod.light_violet)
            #     print(
            #         "dropped:",
            #         chosen_item.name,
            #         [x.name for x in player.fighter.inventory],
            #     )

            # else:
            #     return "didnt-take-turn"
