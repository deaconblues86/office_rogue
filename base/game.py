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

key_map = {
    27: "exit",
    32: "space",
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

    # Sets up key_bindings
    def handle_keys(self, event):
        key = event.sym

        # Handle pop up options
        if self.popup_open:
            if key_map.get(key) == "exit" or key == ord("x"):
                self.popup_open = False
                if self.cursor:
                    self.cursor = None
                return False

            if self.cursor:
                if key_map.get(key) in ("up", "num8"):
                    self.cursor.move(0, -1)

                elif key_map.get(key) == "num7":
                    self.cursor.move(-1, -1)

                elif key_map.get(key) == "num9":
                    self.cursor.move(1, -1)

                elif key_map.get(key) == "num1":
                    self.cursor.move(-1, 1)

                elif key_map.get(key) in ("down", "num2"):
                    self.cursor.move(0, 1)

                elif key_map.get(key) == "num3":
                    self.cursor.move(1, 1)

                elif key_map.get(key) in ("right", "num6"):
                    self.cursor.move(1, 0)

                elif key_map.get(key) in ("left", "num4"):
                    self.cursor.move(-1, 0)

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

        # Handle Std game events
        else:
            if key_map.get(key) == "exit":
                raise SystemExit()

            elif key_map.get(key) == "space":
                self.init_popup("Paused")

            elif key_map.get(key) in ("up", "num8"):
                self.player_move_or_use(0, -1)

            elif key_map.get(key) == "num7":
                self.player_move_or_use(-1, -1)

            elif key_map.get(key) == "num9":
                self.player_move_or_use(1, -1)

            elif key_map.get(key) == "num1":
                self.player_move_or_use(-1, 1)

            elif key_map.get(key) in ("down", "num2"):
                self.player_move_or_use(0, 1)

            elif key_map.get(key) == "num3":
                self.player_move_or_use(1, 1)

            elif key_map.get(key) in ("right", "num6"):
                self.player_move_or_use(1, 0)

            elif key_map.get(key) in ("left", "num4"):
                self.player_move_or_use(-1, 0)

            elif key == ord("."):
                pass

            elif key == ord("k"):
                self.cursor = Cursor(self, self.player.x, self.player.y)

            elif key == ord("i"):
                # TODO: Inventory no longer works
                self.init_popup("Inventory", options=self.player.inventory, popup_func=self.player.use_item)

            elif key == ord("g"):
                self.init_popup(
                    "Pick Up Item",
                    options=self.get_tile(self.player.x, self.player.y).contents,
                    popup_func=self.player.pickup_item
                )

            elif key == ord("d"):
                self.init_popup(
                    "Drop Item",
                    options=self.player.inventory,
                    popup_func=self.player.drop_item
                )

            else:
                print(event, event.sym)
