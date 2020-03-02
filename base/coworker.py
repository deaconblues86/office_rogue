from constants import game_objects, colors
from base.thoughts import Memories, ActionCenter
from base.items import BaseObject, Item, attrFormatter


class Mob(BaseObject):
    """
    Class to handle player/NPC status and actions
     - includes ticking needs, managing AI decisions
    """
    max_inventory = 4

    def __init__(self, needs, social, hunger, thirst, bladder, bowels, energy, gender, job, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.needs = needs

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
        self.inventory = []
        self.path = []

        # AI Controls
        # - target: That which the AI moves towards and plans to use
        # - target_action: The particular action the AI is/will be performing
        # - satisfying: The goal to be fulfilled upon usage
        # - occupying: The item the worker is currently using
        # - waiting: Allows coworker to wait, for a time, while their path clears
        # - memories: Stores experiances of the coworker
        # - action_center: Determines what the coworker will do next
        self.target = None
        self.target_action = None
        self.satisfying = None
        self.occupying = None
        self.waiting = 0
        self.memories = Memories(self)
        self.action_center = ActionCenter(self)

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
        phone_params.update({"game": self.game, "x": 0, "y": 0})
        phone = Item(**phone_params)
        self.inventory.append(phone)

    @property
    def occupied(self):
        return self._occupied

    @occupied.setter
    def occupied(self, value):
        # Occupied floors at zero.  Increased by performing actions and ticks down once with needs check
        self._occupied = max(value, 0)
        if self._occupied:
            self.char = '?'
        else:
            self.char = '@'

    def get_tasks(self):
        # Returns current tasks from Memories
        return self.memories.work_tasks

    def broken_target(self, broken_obj=None):
        # Marks target as broken in memory
        broken_obj = broken_obj or self.target
        self.memories.add_broken(broken_obj)
        self.target = None

    def wants_item(self, obj):
        return obj.name in self.memories.wanted_items

    def finished_action(self, action):
        # Notifies GameInstance that action was completed and resets target.  Called by Action object
        self.broadcast(f"{self.name} Finished {action.name}", action.color)
        self.game.complete_action(action)
        self.game.complete_request(action, self.target)
        self.target = None
        self.target_action = None

    def check_needs(self):
        """
        Called every turn by take_turn.
         - Finds action to satisfy need if no action's in mind
         - If a task list has been created, pull next item instead
         - Finds target for current action if no target's in mind
        """
        if not self.target_action:
            if self.memories.work_tasks:
                self.target_action = self.memories.start_next_job()
            else:
                lowest_status = 1
                for need in self.needs:
                    if need == "social":
                        continue
                    perc = getattr(self, need) / getattr(self, f"max_{need}")
                    if perc < lowest_status:
                        lowest_status = perc
                        self.satisfying = need

                self.target_action = self.action_center.find_action(self.satisfying)
            if not self.target_action:
                print(f"{self.name} can't satisfy {self.satisfying}")
                return

        if not self.target:
            self.target = self.action_center.find_target(self.target_action)
            if not self.target:
                print(f"{self.name} can't find a target to perform {self.target_action.name}")
                return

            # Don't really need a path for self
            if self.target is self:
                return

            self.path = self.calculate_target_path(self.target)
            if not self.path:
                print(f"{self.name} can't path to {self.target.name} {self.target.x}, {self.target.y}")

    def calculate_target_path(self, target_obj=None):
        """
        Asks GameInstance for path to target. If target now blocked, nothing will be returned.
        """
        path_target = target_obj or self.target
        path = self.game.find_path(self, path_target)

        return path

    def tick_needs(self):
        """
        Controls Mob state throught time
        - Frees up worker occupation
        - Ticks Mob Memories
        - Ticks Mob needs every four turns
          - Processes Special events as certain stats tank
        """
        # If not preoccupied, check needs and do stuff
        if not self.game.turns % 6:
            self.memories.tick_memories()
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
                self.mob_fired()

            if self.mood <= 0:
                self.mob_quits()

            if self.bladder <= 0:
                urine = game_objects["Urine"]
                self.game.create_object(self.x, self.y, urine)
                self.bladder = self.max_bladder

            if self.bowels <= 0:
                poo = game_objects["Poo"]
                self.game.create_object(self.x, self.y, poo)
                self.bowels = self.max_bowels

    def take_turn(self):
        """
        Main AI Method called by GameInstance for each turn
        - Ticks Needs/Handles worker state
        - Checks Inventory
        - Frees up Mob as it's occupying action is performed
        - Check whether occupied and, if not, do things
        """
        if self.fired:
            return None

        self.tick_needs()
        # TODO: Currently dropping Trash, stuff that doesn't satisfy, where ever
        # May want to look for Trash Can at some point
        # Dropping first Trash item found when inventory full
        if self.inventory_full():
            trash = filter(lambda x: any(s not in self.needs for s in x.satisfies), self.inventory)
            for t in trash:
                print(f"{self.name} dropped {t.name}")
                self.drop_item(t)
                break

        # If not preoccupied, check needs and do stuff
        if not self.occupied:
            self.check_needs()
            self.move_to_target()

    def move_to_target(self):
        if not self.target:
            return None

        # Dest. has been reached -> use target, clear state
        if not self.path:
            self.perform_action()
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
                    print(f"{self.name} swapped with {coworker.name}...")
                    coworker.move(self.game.get_tile(*coworker.path[0]), swapping=True)
                    self.move(next_tile, swapping=True)

            self.waiting += 1
            if self.waiting == 4:
                print(f"{self.name} is recalcing path...")
                self.path = self.calculate_target_path()

    def move(self, dest_tile, swapping=False):
        """
        Handles Player and Coworker Move actions
        - dest_tile: Tile to be moved to/use
        - swapping: When True, overrides typical blocked check to allow to coworkers to exchange
          positions if they both want to be in each others' spots
        """
        # Standard Move action.  GameInstance will be notified
        if (not dest_tile.blocked or swapping):
            self.game.remove_tile_content(self)
            self.x = dest_tile.x
            self.y = dest_tile.y
            self.game.add_tile_content(self)

            # Wrapped pop in a try as player won't have a path
            try:
                self.path.pop(0)
            except IndexError:
                pass
        else:
            # AI Shouldn't path to places it can't go so shouldn't need player check here, but this is for player
            # "bump" actions
            # Assumes one usable object per tile
            appliances = [c for c in dest_tile.contents if getattr(c, "use", None)]
            if appliances:
                selected_obj = appliances[0]
                options = self.action_center.available_actions(selected_obj)
                self.target = selected_obj
                self.game.init_popup(
                    f"{selected_obj.name} options", options=options, popup_func=self.perform_action
                )

    def perform_action(self, player_action=None):
        ''' Called by AI when satisfying need & based on player choice as the popup callback function '''
        # If the target can be used, lets do it
        # Otherwise, lose it and something new will be chosen
        self.target_action = player_action or self.target_action
        if self.target.use(self):
            self.game.log_action(player_action or self.target_action)
            self.target_action.init_action()

        if player_action:
            self.game.cursor = None
            self.game.popup_open = False

    def use(self, user):
        can_use = False
        if self.occupied:
            print(f"{self.name}: {self.x},{self.y} is currently occupied")
            user.broken_target()
        else:
            can_use = True
        return can_use

    def pickup_item(self, item):
        """ Called whenever a coworker picks up and item & by vendor when dispensing goods """
        self.inventory.append(item)
        self.memories.remove_wanted(item.name)
        item.holder = self
        self.game.remove_tile_content(item)

    def drop_item(self, item):
        self.inventory = list(filter(lambda x: x is not item, self.inventory))
        item.x, item.y = self.x, self.y
        item.holder = None
        self.game.add_tile_content(item)

    def inventory_full(self):
        return len(self.inventory) == self.max_inventory

    def mob_fired(self):
        self.broadcast(self.name.capitalize() + " is fired!", "orange")
        self.char = "%"
        self.color = colors["dark_red"]
        self.blocks = False
        self.name = "remains of " + self.name
        self.state = "fired"
        self.fired = True

    def mob_quits(self):
        self.broadcast(self.name.capitalize() + " quits!", "orange")
        self.char = "%"
        self.color = colors["dark_red"]
        self.blocks = False
        self.name = "remains of " + self.name
        self.state = "fired"
        self.fired = True

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        details = super().dump()
        attrs = list(self.needs)
        attrs += ["target", "satisfying", "job", "occupied"]
        inv = [x.name for x in self.inventory]
        broken = [x.name for x in self.memories.broken_items]
        tasks = [x.name for x in self.get_tasks()]
        wants = self.memories.wanted_items
        return details + attrFormatter(
            attrs, self, override={"broken": broken, "tasks": tasks, "inventory": inv, "wants": wants}
        )
