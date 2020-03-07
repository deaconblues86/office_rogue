import random
from collections import defaultdict

from tcod.event import EventDispatch
from base.enums import ObjType
from base.items import BaseObject, Item, Appliance, Vendor
from base.coworker import Mob
from utils import search_by_obj, search_by_tag
from constants import (
    female_names,
    male_names,
    game_objects,
    game_jobs,
    colors,
    MAX_HISTORY
)

# Maps key strokes to game orders
key_map = {
    27: "exit",
    32: "space",
    1073741906: "up",
    1073741905: "down",
    1073741904: "left",
    1073741903: "right",
    1073741919: "up_left",
    1073741920: "up",
    1073741921: "up_right",
    1073741916: "left",
    1073741918: "right",
    1073741913: "down_left",
    1073741914: "down",
    1073741915: "down_right",
    ord("k"): "open_cursor",
    ord("i"): "open_inventory",
    ord("g"): "open_pickup_item",
    ord("d"): "open_drop_item",
    ord("x"): "exit",
}


class Dispatcher(EventDispatch):
    def __init__(self, game):
        self.game = game

    def ev_quit(self, event):
        raise SystemExit()

    def ev_keydown(self, event):
        self.game.handle_keys(event)

    def ev_mousebuttondown(self, event):
        print(f"X: {event.tile.x}, Y: {event.tile.y}")
        try:
            clicked_tile = self.game.get_tile(event.tile.x, event.tile.y)
            msg = []
            for x in clicked_tile.contents:
                msg.append(x.dump())
            self.game.init_popup("Tile Contents", msg="\n".join(msg))

        except IndexError:
            pass

    def ev_mousemotion(self, event):
        pass


class Cursor():
    def __init__(self, game, x, y):
        self.game = game
        self.char = "X"
        self.color = colors["white"]
        self.x = x
        self.y = y

        self.fetch_tile_contents()
        self.display_available_options()

    def fetch_tile_contents(self):
        self.highlighted = self.game.get_tile(self.x, self.y).contents

    def display_available_options(self):
        self.game.init_popup("Tile Contents", options=self.highlighted, popup_func=self.request_selected_options)

    def request_selected_options(self, selected_obj):
        options = self.game.player.action_center.available_actions(selected_obj)
        self.game.player.target = selected_obj
        self.game.init_popup(
            f"{selected_obj.name} options", options=options, popup_func=self.game.player.perform_action
        )

    def move(self, mod_x, mod_y):
        self.x += mod_x
        self.y += mod_y
        self.fetch_tile_contents()
        self.display_available_options()


class GameInstance():
    def __init__(self):
        self.debugging = False

        self.world_objs = {
            ObjType.static: [],
            ObjType.appliance: [],
            ObjType.vendor: [],
            ObjType.item: [],
            ObjType.mob: []
        }
        self.actions = []
        self.emitters = []
        self.work_requests = defaultdict(list)

        self.game_msgs = []
        self.game_debug_msgs = []
        self.turns = 0

        self.popup_open = False
        self.popup_func = None
        self.popup_options = []

        self.cursor = None

        # Store method calls and args for various player orders
        self.order_map = {
            "exit": {"func": self.exit_order, "args": []},
            "space": {"func": self.init_popup, "args": ["Paused"]},
            "up": {"func": self.move_order, "args": [0, -1]},
            "down": {"func": self.move_order, "args": [0, 1]},
            "left": {"func": self.move_order, "args": [-1, 0]},
            "right": {"func": self.move_order, "args": [1, 0]},
            "up_left": {"func": self.move_order, "args": [-1, -1]},
            "up_right": {"func": self.move_order, "args": [1, -1]},
            "down_left": {"func": self.move_order, "args": [-1, 1]},
            "down_right": {"func": self.move_order, "args": [1, 1]},
            "open_cursor": {"func": self.init_cursor, "args": []},
            "open_inventory": {"func": self.open_inventory, "args": []},
            "open_pickup_item": {"func": self.open_pickup_item, "args": []},
            "open_drop_item": {"func": self.open_drop_item, "args": []},
        }

    def run_coworkers(self):
        if not self.popup_open:
            self.turns += 1
            for action in self.actions:
                action.tick_action()

            for worker in self.world_objs[ObjType.mob]:
                if worker is self.player:
                    if not self.player.fired:
                        worker.tick_needs()
                    continue
                worker.take_turn()

    def find_tasks(self, action_name):
        return self.work_requests[action_name]

    def find_objs(self, obj_name, obj_state=None):
        requested = []
        for obj_type in [ObjType.appliance, ObjType.vendor, ObjType.item]:
            requested += search_by_obj(self.world_objs[obj_type], obj_name, obj_state)
        return requested

    def find_tags(self, obj_tag, obj_state=None):
        requested = []
        for obj_type in [ObjType.appliance, ObjType.vendor, ObjType.item]:
            requested += search_by_tag(self.world_objs[obj_type], obj_tag, obj_state)
        return requested

    def find_path(self, seeker, target):
        # Routes path requests of Workers to MapGenerator
        return self.game_map.find_path(seeker, target)

    def get_tile(self, req_x, req_y):
        return self.game_map.get_tile(req_x, req_y)

    def get_adjacent(self, obj):
        # Routes Adjacent requests of Objects through game_map to get Adjacent Tiles
        return self.game_map.get_adjacent_tiles(obj)

    def add_tile_content(self, obj):
        # Communicates tile content change to MapGenerator which then updates path_map
        self.game_map.place_object(obj)
        self.world_objs[obj.type].append(obj)

    def remove_tile_content(self, obj):
        # Communicates tile content change to MapGenerator which then updates path_map
        self.game_map.remove_object(obj)
        self.world_objs[obj.type] = list(filter(lambda x: x is not obj, self.world_objs[obj.type]))

    def create_object(self, x, y, obj_params, holder=None):
        obj_params.update({"game": self, "x": x, "y": y})

        try:
            if obj_params["obj_type"] == "static":
                obj = BaseObject(**obj_params)
            elif obj_params["obj_type"] == "item":
                obj = Item(**obj_params)
            elif obj_params["obj_type"] == "appliance":
                obj = Appliance(**obj_params)
            elif obj_params["obj_type"] == "vendor":
                obj = Vendor(**obj_params)
            elif obj_params["obj_type"] == "mob":
                obj = Mob(**obj_params)
        except TypeError as e:
            print(f" --- {obj_params.get('name', '__missing_name__')} is missing required attribute --- ")
            raise e

        if holder:
            obj.owner = holder
            holder.pickup_item(obj)

        else:
            self.add_tile_content(obj)

        return obj

    def transform_object(self, obj, new):
        new = game_objects.get(new)
        if new:
            # TODO: Pretty sure delete_object still leaves the object in the game's list of objects...
            self.create_object(obj.x, obj.y, new, holder=obj.holder)
            self.delete_object(obj, holder=obj.holder)
        else:
            print(f"New object not found: {new}")

    def delete_object(self, obj, holder=None):
        if holder:
            holder.drop_item(obj)

        self.remove_tile_content(obj)
        del obj

    def log_action(self, action):
        self.actions.append(action)

    def complete_action(self, action):
        self.actions = [x for x in self.actions if x is not action]
        del self.renderer.action_cache[action]

    def log_request(self, obj, request_action):
        '''
        Logs unique requests (based on obj & request type) to be performed
        '''
        if obj not in self.work_requests[request_action]:
            self.work_requests[request_action].append(obj)

    def complete_request(self, job, target):
        if job in self.work_requests:
            self.work_requests[job] = [x for x in self.work_requests[job] if x is not target]

    def log_emitter(self, obj, thought):
        # TODO: Implement emitted auras
        # Auras passed as thoughts to workers when adjacent on emitter
        # Need to handle auras on init but, more importantly, temporary
        # state-based auras (i.e. on_dirty) - need to know when temps end
        pass

    def log_message(self, new_msg, color="white", debug=False):
        """ Appends message to list of game messages w/ color and trims history """
        if debug and self.debugging:
            print(new_msg)
            self.game_debug_msgs.append(new_msg)

        self.game_msgs.append((new_msg, color))
        self.game_msgs = self.game_msgs[-1 * MAX_HISTORY:]

    def init_popup(self, *args, **kwargs):
        self.renderer.init_popup(*args, **kwargs)

    def create_coworker(self, x, y, job="analyst", creating_player=False):
        # Pulling base coworker params & randomizing starting stats
        params = game_objects["Coworker"]
        params.update({
            "social": random.randint(25, 100),
            "hunger": random.randint(25, 100),
            "thirst": random.randint(25, 100),
            "bladder": random.randint(75, 100),
            "bowels": random.randint(75, 100),
            "energy": random.randint(25, 100)
        })

        # Determining name at random
        if random.randint(0, 100) < 61:
            params["gender"] = "female"
            params["name"] = female_names[random.randrange(0, len(female_names))]
        else:
            params["gender"] = "male"
            params["name"] = male_names[random.randrange(0, len(male_names))]

        # TODO: Move special jobs out into Defs
        if not creating_player:
            params["job"] = game_jobs[job]["name"]
            params["color"] = game_jobs[job]["color"]

        else:
            params["job"] = game_jobs[job]["name"]

        coworker = self.create_object(x, y, params)
        return coworker

    def player_move_or_use(self, mod_x, mod_y):
        if self.player.occupied:
            return None

        dest_x = self.player.x + mod_x
        dest_y = self.player.y + mod_y
        dest_tile = self.get_tile(dest_x, dest_y)
        self.player.move(dest_tile)

    def move_order(self, mod_x, mod_y):
        if self.cursor:
            self.cursor.move(mod_x, mod_y)
        else:
            self.player_move_or_use(mod_x, mod_y)

    def init_cursor(self):
        if not self.popup_open:
            self.cursor = Cursor(self, self.player.x, self.player.y)

    def open_inventory(self):
        if not self.popup_open:
            # TODO: Inventory no longer works
            self.init_popup("Inventory", options=self.player.inventory, popup_func=self.player.use_item)

    def open_pickup_item(self):
        if not self.popup_open:
            self.init_popup(
                "Pick Up Item",
                options=[
                    x
                    for x in self.get_tile(self.player.x, self.player.y).contents
                    if isinstance(x, Item)
                ],
                popup_func=self.player.pickup_item
            )

    def open_drop_item(self):
        if not self.popup_open:
            self.init_popup(
                "Drop Item",
                options=self.player.inventory,
                popup_func=self.player.drop_item
            )

    def handle_popup_options(self, key):
        if self.popup_open:
            try:
                opt_index = key - ord('a')
                choice = self.popup_options[opt_index]

                # Handles cursor based interations
                # cursor provides target to GameInstance
                # cursor never closes popup on it's own (due to that return)
                if self.cursor:
                    self.popup_func(choice)
                    return

                # Handles standard callback functions provided by object that
                # called the popup
                else:
                    self.popup_func(choice)

                self.popup_open = False
                self.cursor = None

            except IndexError:
                pass

    def exit_order(self):
        if self.popup_open:
            self.popup_open = False
            self.cursor = None
        else:
            raise SystemExit()

    # Sets up key_bindings
    def handle_keys(self, event):
        key = event.sym

        # If the key maps to a game order, we'll call the required method
        # We'll still always try to interpret it has a popup option since check on popup built
        # into methods being called (keystroke of d could be an option of drop order)
        if key in key_map:
            order_issued = key_map[key]
            order_func = self.order_map[order_issued]["func"]
            order_args = self.order_map[order_issued]["args"]
            order_func(*order_args)

        self.handle_popup_options(key)
