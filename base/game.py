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
    game_objects,
    game_auras,
    work_requests,
)
from utils import object_funcs

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


def attrFormatter(attrs, obj, override={}, base=False):
    '''
    Formats Object's attributes for rendering when viewing
    - attrs: Attributes for display
    - obj: The object itself
    - override: dictionary of special preformatted items to include
    - base: When True includes object name as header
    '''
    details = ""
    if base:
        details += f"{getattr(obj, 'name')}\n"
    for attr in attrs:
        val = getattr(obj, attr, '')
        if isinstance(val, list):
            val = ','.join(val)
        elif isinstance(val, BaseObject):
            val = val.name
        details += f" - {attr}: {val}\n"

    for attr in override:
        val = override.get(attr)
        if isinstance(val, list):
            val = ','.join(val)
        elif isinstance(val, BaseObject):
            val = val.name
        details += f" - {attr}: {val}\n"

    return details


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
            msg = []
            for x in clicked_tile.contents:
                msg.append(x.dump())
            self.app.init_popup("Tile Contents", msg="\n".join(msg))

        except IndexError:
            pass

    def ev_mousemotion(self, event):
        pass


class WorkRequest():
    def __init__(self, name, job, target, target_stat=None, target_func=None, modifier=None, new_value=None):
        self.name = name
        self.job = job
        self.target = target
        self.target_stat = target
        self.target_func = target
        self.modifier = target
        self.new_value = target

        self.assignee = None

    def resolve_request(self):
        if self.target_func:
            req_method = getattr(self.target, self.target_func)
            req_method()
        elif self.target_stat and self.modifier:
            if self.modifier < 0:
                setattr(
                    self.target,
                    self.target_stat,
                    max(getattr(self.target, self.target_stat) + self.modifier, 0)
                )
            else:
                setattr(
                    self.target,
                    self.target_stat,
                    min(
                        getattr(self.target, self.target_stat) + self.modifier,
                        getattr(self.target, f"max_{self.target_stat}")
                    )
                )
        elif self.target_stat and self.new_value:
            setattr(self.target, self.target_stat, self.new_value)


class Thought():
    def __init__(self, name, description, duration, target_stat, modifier):
        self.name = name
        self.description = description
        self.duration = duration
        self.target_stat = target_stat
        self.modifier = modifier

    def apply_modifier(self, target):
        attr = getattr(target, self.target_stat)
        attr += self.modifier
        setattr(target, self.target_stat, attr)


class Memories():
    def __init__(self, mob):
        self.mob = mob
        self.broken_items = []
        self.work_tasks = []
        self.thoughts = []
        self.relationships = []
        self.iters = 0

    def tick_memories(self):
        '''
        Every 20 turns, remove oldest item found to be broken,
        tick thought lifetimes, apply modifiers, and remove timed out thoughts
        '''
        self.iters += 1
        if not self.iters % 20:
            if self.broken_items:
                self.broken_items.pop(0)
            for thought in self.thoughts:
                thought.apply_modifier(self.mob)
                thought.duration -= 1
            self.thoughts = [t for t in self.thoughts if t.duration <= 0]

    def add_broken(self, obj):
        '''
        Try to pop already found broken obj from list if present
        Add broken object to end of list
        '''
        try:
            i = self.broken_items.index(obj)
            self.broken_items.pop(i)
        except ValueError:
            print(f"newly found broken object: {obj.name}")
        finally:
            self.broken_items.append(obj)


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
        self.cleanliness = 100
        self.state = ""
        self.emits = kwargs.get("emits")
        self.on_create = kwargs.get("on_create")
        self.on_destroy = kwargs.get("on_destroy")

    def adjacent(self):
        """ Asks GameInstance 'What's Next to Me?'' """
        return self.game.get_adjacent(self)

    @property
    def broken(self):
        return self.durability <= 0

    def destroy(self):
        self.game.delete_object(self)

    def broadcast(self, message, color="white"):
        """ Publishes call backs from objects to game """
        self.game.log_message(message, color)

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        return attrFormatter(["durability", "state"], self, base=True)


class Item(BaseObject):
    def __init__(self, satisfies, use_func, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.satisfies = satisfies
        self.use_func_repr = use_func
        self.owner = owner
        self.in_inventory = None

        self.on_broken = kwargs.get("on_broken")
        self.on_dirty = kwargs.get("on_dirty")

        # Get actual function from string repr
        if self.use_func_repr:
            self.use_func = getattr(object_funcs, self.use_func_repr, self._use_func)

    def use(self, user):
        if self.owner and self.owner is not user:
            self.broadcast(f"{self.name} doesn't belong to {user.name}")
        elif self.broken:
            self.broadcast(f"{self.name} is broken")
            user.broken_target(self)
        else:
            wear, dirt = self.use_func(user)
            self.durability -= wear
            self.cleanliness -= dirt
            self.eval_events()

    def _use_func(self, target):
        self.broadcast(f"{self.name.capitalize} has no use!", "red")
        return 0, 0

    def move_to_inventory(self, holder):
        holder.inventory.append(self)
        self.in_inventory = holder
        self.game.remove_tile_content(self)

    def drop_from_inventory(self, holder):
        holder.inventory = list(filter(lambda x: x is not self, holder.inventory))
        self.x, self. y = holder.x, holder.y
        self.game.add_tile_content(self)
        self.in_inventory = None

    def eval_events(self):
        if self.durability <= 0:
            self.game.submit_event(self, self.on_broken)
        if self.cleanliness <= 0:
            self.game.submit_event(self, self.on_dirty)

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        details = super().dump()
        return details + attrFormatter(["owner", "satisfies"], self)


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
        self.on_no_stock = kwargs.get("on_no_stock")
        self.restock_items()

    def restock_items(self):
        for item in self.stock:
            curr_stock = len(list(filter(lambda x: x.name == item["name"], self.inventory)))
            obj_params = game_objects[item["name"]]
            obj_params.update({"game": self.game, "x": 0, "y": 0})
            while curr_stock < item["max_stock"]:
                curr_stock += 1
                obj = Item(**obj_params)
                obj.move_to_inventory(self)

    def use(self, user):
        """
        Calls dispense function based on player choice or Coworker's Need
        - Will render Menu popup if Player
        - AI will get first item that satisfies need. If none exist, will be marked as broken
        """
        # Render Menu if player
        if user is self.game.player:
            self.game.init_popup(self.name.capitalize(), options=self.inventory, popup_func=self.dispense)
        else:
            # AI will choose first item to satisfy their needs
            desired = filter(lambda x: user.satisfying in x.satisfies, self.inventory)
            for item in desired:
                self.dispense(item, user)
                break
            else:
                user.broken_target(self)

    def dispense(self, item, user=None):
        """
        Places requested Item in users inventory if not full
        - Coworkers should use items in inventory first so full inventory shouldn't matter
        - Log request for restock if vendor is empty
        """
        if not user:
            user = self.game.player
        if user.inventory_full():
            user.broadcast(f"{user.name.capitalize()}'s inventory is full", "dark_red")
            return None

        self.inventory = list(filter(lambda x: x is not item, self.inventory))
        item.owner = user
        item.move_to_inventory(user)
        user.broadcast(f"{user.name.capitalize()} received {item.name}", "white")

        if not self.inventory:
            self.game.submit_event(self, self.on_no_stock)

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        inv = [x.name for x in self.inventory]
        grouped_inv = set([f"{x}: {inv.count(x)}" for x in inv])
        details = super().dump()
        return details + attrFormatter(["owner", "satisfies"], self, override={'stock': grouped_inv})


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
        # - waiting: Allows coworker to wait, for a time, while their path clears
        # - memories: Stores experiances of the coworker
        self.target = None
        self.satisfying = None
        self.waiting = 0
        self.memories = Memories(self)

        self.fired = False
        self._occupied = 0

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

        phone_params = game_objects["Cellphone"]
        phone_params.update({"game": self, "x": 0, "y": 0})
        phone = Item(**phone_params)
        self.inventory.append(phone)

    @property
    def occupied(self):
        return self._occupied

    @occupied.setter
    def occupied(self, value):
        self._occupied = max(value, 0)
        if self._occupied:
            self.char = '?'
        else:
            self.char = '@'

    def get_tasks(self):
        return self.memories.work_tasks

    def add_task(self, job):
        job.assignee = self
        self.memories.work_tasks.append(job)

    def remove_task(self, job):
        self.memories.work_tasks = [x for x in self.memories.work_tasks if x is not job]
        self.game.complete_request(job)

    def broken_target(self, obj):
        ''' Marks target as broken in memory and clears target '''
        self.memories.add_broken(obj)
        self.target = None

    def determine_closest(self, targets):
        """
        Determines closest target from list that could satisfy needs and isn't occupied.
        - Pathing in GameInstance can reject occupied targets as well if the situation changes
        - determine_closest only called when no target is held or when it was bad
        """
        min_distance = None
        closest = None
        targets = filter(lambda x: not x.owner or x.owner is self, targets)
        for target in targets:
            # If no empty tiles, occupado
            empty_tiles = list(filter(lambda x: not x.blocked, self.game.get_adjacent(target)))
            if not empty_tiles:
                continue

            # If target has been held but is bad, skip it
            if target is self.target:
                continue

            # If target is known to be broken, skip it
            if target in self.memories.broken_items:
                continue

            dx = target.x - self.x
            dy = target.y - self.y
            distance = math.sqrt(dx**2 + dy**2)
            if min_distance is None or distance < min_distance:
                min_distance = distance
                closest = target

        return closest

    def calculate_target_path(self):
        """
        Asks GameInstance for path to target. If target now occupied, nothing will be returned.
        If its a bum target, keep for now, but know to exclude on next pass
        """
        self.path = self.game.find_path(self, self.target)
        if not self.path:
            self.broadcast(f"{self.name} can't path to {self.target.name} {self.target.x}, {self.target.y}")
            self.state = "bum_target"

    def check_needs(self):
        """
        Called every turn by take_turn. If not currently satsifying a need with a valid target in mind,
        determine lowest need and find something to fix it.
        - Inventory will be evaluated first to see if they have something for it
        - If looking for work and a task has been assiged, that will be pursued.  Otherwise, the closest
          unoccupied thing that satisfies will be picked and a path returned
        - If a bad target was previously acquired (bum_target) that'll be dropped from evaluation
          - bad targets: Unable to path
        """
        if not self.target or self.state == "bum_target":
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

            if self.satisfying == "work" and self.get_tasks():
                task = self.get_tasks()[0]
                self.target = task.target
            else:
                targets = self.game.find_need(self.satisfying)
                self.target = self.determine_closest(targets)

            if not self.target:
                self.broadcast(f"{self.name} can't satisfy {self.satisfying}")
            else:
                self.state = f"satisfying {self.satisfying}"
                self.calculate_target_path()

    def tick_needs(self):
        """
        Controls Mob state throught time
        - Ticks Mob needs every four turns
        - Frees up Mob as it's occupying action is performed
        - Processes Special events as certain stats tank
        """
        self.occupied -= 1
        self.memories.tick_memories()
        if not self.game.turns % 4:
            self.mood_drain = 0
            for need in self.needs:
                # Mood is ticked last - dependent on others
                if need == "mood":
                    continue
                setattr(self, need, max(getattr(self, f"{need}_drain") + getattr(self, need), 0))
                if getattr(self, need) == 0:
                    self.mood_drain -= 1
            else:
                # If mood's not currently draining, increase mood equal to stats 75% filled
                if not self.mood_drain:
                    positives = [x for x in self.needs if getattr(self, need) > 75]
                    self.mood = min(len(positives) + self.mood, 100)

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
        """ Main AI Method called by GameInstance for each turn """
        if self.fired:
            return None

        self.tick_needs()
        # If not preoccupied, check needs and do stuff
        if not self.occupied:
            self.check_needs()
            self.move_to_target()

    def move_to_target(self):
        if not self.target:
            return None

        # Dest. has been reached -> use target, clear target, clear state
        if not self.path:
            next_tile = self.game.get_tile(self.target.x, self.target.y)
            self.move(next_tile)
            self.target = None
            self.state = ""
            return None

        # Will be standard Move
        next_tile = self.game.get_tile(*self.path[0])
        if not next_tile.blocked:
            self.move(next_tile)

        # Will wait or try to swap places with blocking coworker
        else:
            blockers = [x for x in next_tile.contents if x.blocks]
            if len(blockers) == 1 and isinstance(blockers[0], Mob):
                coworker = blockers[0]
                if coworker.path and coworker.path[0] == (self.x, self.y):
                    self.broadcast(f"{self.name} swapped with {coworker.name}...")
                    coworker.move(self.game.get_tile(*coworker.path[0]), swapping=True)
                    self.move(next_tile, swapping=True)

            self.waiting += 1
            if self.waiting == 4:
                self.broadcast(f"{self.name} is recalcing...")
                self.calculate_target_path()
            else:
                self.broadcast(f"{self.name} is waiting...")

    def move(self, dest_tile, swapping=False):
        """
        Handles Player and Coworker Move actions.  If player 'moves' into tile of appliance,
        appliance will be used instead.  Likewise, Coworkers will be directed to do the same
        - dest_tile: Tile to be moved to/use
        - swapping: When True, overrides typical blocked check to allow to coworkers to exchange
          positions if they both want to be in each others' spots
        """
        # Standard Move action
        if not dest_tile.blocked or swapping:
            self.game.remove_tile_content(self)
            self.game.update_pathmap(self.x, self.y)
            self.x = dest_tile.x
            self.y = dest_tile.y
            self.game.add_tile_content(self)
            self.game.update_pathmap(self.x, self.y)

            # Wrapped pop in a try as player won't have a path
            try:
                self.path.pop(0)
            except IndexError:
                pass

        # Reached end of path or was player directed.
        # Will now use target object
        else:
            # Assumes one usable object per tile
            appliances = [c for c in dest_tile.contents if getattr(c, "use", None)]
            if appliances:
                appliances[0].use(self)

    def use_item(self, item):
        ''' Called by AI when satisfying need & based on player choice as the popup callback function '''
        item.use(self)

    def pickup_item(self, item):
        item.move_to_inventory(self)

    def drop_item(self, item):
        item.drop_from_inventory(self)

    def inventory_full(self):
        return len(self.inventory) == self.max_inventory

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        details = super().dump()
        attrs = list(self.needs)
        attrs += ["target", "satisfying"]
        broken = [x.name for x in self.memories.broken_items]
        tasks = [f"{x.name}: {x.target.name}" for x in self.get_tasks()]
        return details + attrFormatter(attrs, self, override={"broken": broken, "tasks": tasks})


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
    def load_options(cls, title, msg, options):
        cls.title = title
        cls.text = ""
        if msg:
            cls.text += f"{msg}\n\n"

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
        self.emitters = []
        self.work_requests = []

        self.game_msgs = []
        self.turns = 0

    def run_coworkers(self):
        if not self.popup_open:
            self.turns += 1
            for worker in self.world_objs[ObjType.mob]:
                if worker is self.player:
                    if not self.player.fired:
                        worker.tick_needs()
                    continue
                worker.take_turn()

    def assign_requests(self):
        unassigned = filter(lambda x: x.assignee is None, self.work_requests)
        for job in unassigned:
            candidates = filter(lambda x: x.job == job.job and not x.get_tasks(), self.world_objs[ObjType.mob])
            for c in candidates:
                c.add_task(job)
                print(f"{c.name} assigned to {job.name}: {job.target.name}")
                break

    def complete_request(self, job):
        self.work_requests = [x for x in self.work_requests if x is not job]
        del job

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

    def init_popup(self, title, msg=None, options=[], popup_func=None):
        self.popup_open = True
        self.popup_options = options
        self.popup_func = popup_func
        self.popup.load_options(title, msg, [x.name for x in self.popup_options])

    def find_need(self, need):
        satisfies = []
        for obj_type in [ObjType.appliance, ObjType.vendor, ObjType.item]:
            for obj in self.world_objs[obj_type]:
                if need in obj.satisfies:
                    satisfies.append(obj)

        return satisfies

    def find_path(self, seeker, target):
        """
        Pathing to first empty adjacent tile of target. If none exist, None will be turned and the
        Coworker can try again next time around.
        """
        empty_tiles = list(filter(lambda x: not x.blocked, self.get_adjacent(target)))
        if not empty_tiles:
            return None

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

    def delete_object(self, obj, in_inventory=None):
        if in_inventory:
            obj.drop_from_inventory(in_inventory)

        self.remove_tile_content(obj)
        self.submit_event(obj, getattr(obj, "on_destroy", {}))
        del obj

    def create_object(self, x, y, obj_params, in_inventory=None):
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

        self.submit_event(obj, getattr(obj, "on_create", {}))

        if in_inventory:
            obj.in_inventory = in_inventory
        else:
            self.add_tile_content(obj)

        return obj

    def transform_object(self, obj, new):
        # TODO: This doesn't exactly work for items in inventory
        new = game_objects.get(new)
        if new:
            self.create_object(obj.x, obj.y, new, in_inventory=obj.in_inventory)
            self.delete_object(obj, in_inventory=obj.in_inventory)

    def submit_event(self, obj, event):
        if not event:
            return None

        if event.get("request"):
            self.log_request(obj, event["request"])
        if event.get("become"):
            self.transform_object(obj, event["become"])
        if event.get("emits"):
            self.log_emitter(obj, event["emits"])

    def log_emitter(self, obj, thought):
        # TODO: Implement emitted auras
        # Auras passed as thoughts to workers when adjacent on emitter
        # Need to handle auras on init but, more importantly, temporary
        # state-based auras (i.e. on_dirty) - need to know when temps end
        pass

    def log_request(self, obj, request):
        job_request = work_requests.get(request)
        if job_request:
            job_request.update({"target": obj})
            job = WorkRequest(**job_request)
            self.work_requests(job)

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
        print(event, event.sym)

        # Handle pop up options
        if self.popup_open:
            if key_map.get(key) == "exit" or key == ord("x"):
                self.popup_open = False
                return False

            try:
                opt_index = key - ord('a')
                choice = self.popup_options[opt_index]
                self.popup_func(choice)
                self.popup_open = False
            except IndexError:
                pass

        # Handle Std game events
        else:
            if key_map.get(key) == "exit":
                raise SystemExit()

            if key_map.get(key) == "space":
                self.init_popup("Paused")

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
