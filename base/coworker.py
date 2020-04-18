from constants import game_objects, colors
from base.thoughts import Memories, ActionCenter
from base.items import BaseObject, Item, attrFormatter


class Mob(BaseObject):
    """
    Class to handle player/NPC status and actions
     - includes ticking needs, managing AI decisions
    """
    max_inventory = 4
    boredom_threshold = 5

    def __init__(self, needs, social, hunger, thirst, bladder, bowels, energy, gender, job, tags, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.needs = needs
        self.tags = tags

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
        phone.holder = self
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

    def get_need_perc(self, need):
        return getattr(self, need) / getattr(self, f"max_{need}")

    def get_tasks(self):
        # Returns current tasks from Memories
        return self.memories.work_tasks

    def no_target_available(self):
        # Marks action as unavailable when no target can be found
        self.memories.add_unavailable(self.target_action)
        self.target_action = None

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

    def find_next_target_action(self):
        """
        Iterates over ordered list of needs from most to least pressing
         - If a task as been stored in memory, that will be returned instead
         - Called every turn, so first need check we don't already know what to do
        """
        if not self.target_action:
            if self.get_tasks():
                self.target_action = self.memories.start_next_job()
            else:
                # TODO: Will need to add social back to coworker def at some point
                # Iterate over list of sorted needs by priority, adding needs unsatisfied to list as needed
                # break out once target is found
                need_checks = sorted(
                    [{"need": need, "perc": self.get_need_perc(need)} for need in self.needs],
                    key=lambda x: x["perc"]
                )
                while True:
                    try:
                        self.satisfying = need_checks.pop(0)["need"]
                    except IndexError:
                        break

                    self.target_action = self.action_center.find_action(self.satisfying)
                    print(self.target_action)
                    if self.target_action:
                        break

                    self.broadcast(f"{self.name} can't satisfy {self.satisfying}", debug=True)
                    self.memories.add_unsatisfied(self.satisfying)

    def find_next_target(self):
        """
        Requests closest target from action_center.  If none exist, the action will be marked
        as unavailable
         - Called every turn, so first need to check we don't ready have a target in mind
        """
        if not self.target:
            self.target = self.action_center.find_target(self.target_action)
            if not self.target:
                self.broadcast(f"{self.name} can't find a target to perform {self.target_action}", debug=True)
                self.no_target_available()

    def calculate_target_path(self):
        """
        Asks GameInstance for path to target. If target now blocked, nothing will be returned.
         - If target is self or we're already adjacent, no path needed
        """
        # Don't really need a path for self or adjacent target
        if self.target is self or self.target in self.adjacent():
            self.path = []
        else:
            self.path = self.game.find_path(self, self.target)
            if not self.path:
                self.broadcast(f"{self.name} can't path to {self.target}", debug=True)
                self.broken_target()

    def check_needs(self):
        """
        Called every turn by take_turn.
         - Finds action to satisfy need if no action's in mind
         - If a task list has been created, pull next item instead
         - Finds target for current action if no target's in mind
        """
        self.find_next_target_action()
        if self.target_action:
            self.find_next_target()
        if self.target:
            self.calculate_target_path()

    def tick_needs(self):
        """
        Controls Mob state throught time
        - Frees up worker occupation
        - Ticks Mob Memories
        - Ticks Mob needs every six turns
        """
        # If not preoccupied, check needs and do stuff
        if not self.game.turns % 6:
            self.memories.tick_memories()
            self.mood_drain = 0
            for need in self.needs:
                # Mood is ticked last - dependent on others
                if need == "mood":
                    continue
                self.apply_modifier(need, getattr(self, f"{need}_drain"))
                if getattr(self, need) == 0:
                    self.mood_drain -= 1

            # If mood's not currently draining, increase mood equal to stats 75% filled
            if not self.mood_drain:
                positives = len([x for x in self.needs if self.get_need_perc(need) > .75])
                self.apply_modifier("mood", positives)
            else:
                self.apply_modifier("mood", self.mood_drain)

            self.eval_triggers()

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
                self.broadcast(f"{self.name} dropped {t.name}", debug=True)
                self.drop_item(t)
                break

        # If not preoccupied, check needs and do stuff
        if not self.occupied:
            self.check_needs()
            if self.target:
                self.move_to_target()

    def move_to_target(self):
        # Dest. has been reached -> use target
        if not self.path:
            self.perform_action()
            return None

        next_tile = self.game.get_tile(*self.path.pop(0))
        blockers = [x for x in next_tile.contents if x.blocks]

        # If path not blocked, will be standard move
        # If path blocked by coworker who wants my spot, lets swap places
        # Otherwise we'll wait a bit
        if not blockers:
            self.move(next_tile)
        elif len(blockers) == 1 and isinstance(blockers[0], Mob):
            coworker = blockers[0]
            if coworker.path and coworker.path[0] == (self.x, self.y):
                self.broadcast(f"{self.name} swapped with {coworker.name}...", debug=True)
                coworker.move(self.game.get_tile(*coworker.path.pop(0)), swapping=True)
                self.move(next_tile, swapping=True)
        else:
            self.waiting += 1
            if self.waiting == 4:
                self.waiting = 0
                self.broadcast(f"{self.name} is recalcing path...", debug=True)
                self.path = self.calculate_target_path()

    def move(self, dest_tile, swapping=False):
        """
        Handles Player and Coworker Move actions
        - dest_tile: Tile to be moved to/use
        """
        # Standard Move action
        if not dest_tile.blocked or swapping:
            self.game.remove_tile_content(self)
            self.x = dest_tile.x
            self.y = dest_tile.y
            self.game.add_tile_content(self)

        else:
            # AI Shouldn't path to places it can't go - this is for player "bump" actions
            # Assumes one usable object (Appliance/Vendor) per tile
            appliances = [c for c in dest_tile.contents if getattr(c, "can_use", None)]
            if appliances:
                selected_obj = appliances[0]
                options = self.action_center.available_actions(selected_obj)
                self.target = selected_obj
                self.game.init_popup(
                    f"{selected_obj.name} options", options=options, popup_func=self.perform_action
                )

    def perform_action(self, player_action=None):
        '''
        Called by AI when satisfying need & based on player choice as the popup callback function
         - If the target can be used, lets do it (init_action())
            - action will be logged in both action_center (for tracking usage) and game (for rendering/ticking duration)
         - Otherwise, lose it and something new will be chosen
            - can_use() marks target as broken by calling Mob's broken_target method
         - If this is a player action, be sure to close popups/destroy cursor
        '''
        self.target_action = player_action or self.target_action
        if self.target_action.usage_override or self.target.can_use(self):
            self.action_center.log_action_performed(self.target_action)
            self.game.log_action(player_action or self.target_action)
            self.target_action.init_action()

        if player_action:
            self.game.close_popup()

    def can_use(self, user):
        can_use = False
        if self.occupied:
            self.broadcast(f"{self.name}: {self.x},{self.y} is currently occupied")
            user.broken_target()
        else:
            can_use = True
        return can_use

    def pickup_item(self, item):
        """ Called whenever a coworker picks up and item & by vendor when dispensing goods """
        if self.inventory_full():
            self.broadcast(f"{self.name.capitalize()}'s inventory is full", "dark_red")
            return

        self.inventory.append(item)
        self.memories.remove_wanted(item.name)
        item.holder = self
        self.game.remove_tile_content(item)

        if self is self.game.player:
            self.game.close_popup()  # need to close popup first in order for game to reinit properly
            self.game.open_pickup_item()

    def drop_item(self, item):
        self.inventory = list(filter(lambda x: x is not item, self.inventory))
        item.x, item.y = self.x, self.y
        item.holder = None
        self.game.add_tile_content(item)

        if self is self.game.player:
            self.game.close_popup()  # need to close popup first in order for game to reinit properly
            self.game.open_drop_item()

    def item_actions(self, selected_obj):
        """
        Function, similiar to cursor's, to generate list of actions available based on player's
        choice in inventory
        """
        options = self.action_center.available_actions(selected_obj)
        self.game.player.target = selected_obj
        self.game.init_popup(
            f"{selected_obj.name} options", options=options, popup_func=self.game.player.perform_action
        )

    def inventory_full(self):
        return len(self.inventory) == self.max_inventory

    def mob_fired(self):
        self.broadcast(self.name.capitalize() + " is fired!", "orange")
        self.char = "%"
        self.color = colors["dark_red"]
        self.blocks = False
        self.name = "remains of " + self.name
        self.fired = True

    def mob_quits(self):
        self.broadcast(self.name.capitalize() + " quits!", "orange")
        self.char = "%"
        self.color = colors["dark_red"]
        self.blocks = False
        self.name = "remains of " + self.name
        self.fired = True

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        details = super().dump()
        attrs = list(self.needs)
        attrs += ["target", "satisfying", "job", "occupied"]
        inv = [x.name for x in self.inventory]
        broken = [x.name for x in self.memories.broken_items]
        unavailable = [x.name for x in self.memories.unavailable_actions]
        tasks = [x.name for x in self.get_tasks()]
        wants = self.memories.wanted_items
        return details + attrFormatter(
            self,
            attrs,
            override={
                "broken": broken, "unavail": unavailable, "tasks": tasks, "inventory": inv, "wants": wants
            }
        )
