import math
from constants import game_objects, colors
from base.thoughts import Memories
from base.items import BaseObject, Item, attrFormatter


class Mob(BaseObject):
    max_inventory = 4
    needs = ["social", "hunger", "thirst", "bladder", "bowels", "energy", "work", "mood"]

    def __init__(self, social, hunger, thirst, bladder, bowels, energy, gender, job, *args, **kwargs):
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
        self.inventory = []
        self.path = []

        # AI Controls
        # - target: That which the AI moves towards and plans to use
        # - target_job: The particular job the AI is currently performing
        # - satisfying: The goal to be fulfilled upon usage
        # - occupying: The item the worker is currently using
        # - waiting: Allows coworker to wait, for a time, while their path clears
        # - memories: Stores experiances of the coworker
        self.target = None
        self.target_job = None
        self.satisfying = None
        self.occupying = None
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
        phone_params.update({"game": self.game, "x": 0, "y": 0})
        phone = Item(**phone_params)
        self.inventory.append(phone)

    @property
    def occupied(self):
        return self._occupied

    @occupied.setter
    def occupied(self, value):
        """ occupied floors at zero.  Increased by actions and ticks down once with needs check """
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

    def remove_task(self):
        print(f"{self.name} completed {self.target_job.name} of {self.target_job.target.name}")
        self.memories.finish_job(self.target_job)
        self.game.complete_request(self.target_job)
        self.target_job = None

    def finished_action(self, action):
        print(f"{self.name} Finished {action.name}")
        self.target = None
        self.game.complete_action(action)

    def broken_target(self, obj):
        ''' Marks target as broken in memory and clears target '''
        self.memories.add_broken(obj)
        self.target = None

    def determine_closest(self, targets):
        """
        Determines closest target from list that could satisfy needs and isn't occupied.
        - Pathing in GameInstance can reject blocked targets as well if the situation changes
        - determine_closest only called when no target is held or when it was bad
        """
        min_distance = None
        closest = None
        targets = filter(lambda x: not x.owner or x.owner is self, targets)
        for target in targets:
            # # If no empty tiles, occupado
            # empty_tiles = list(filter(lambda x: not x.blocked, self.game.get_adjacent(target)))
            # if not empty_tiles:
            #     continue

            # If target currently in use, skip it
            if target.occupied_by:
                print(f"{target.name}: {target.x},{target.y} occupied by {target.occupied_by.name}")
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
        Asks GameInstance for path to target. If target now blocked, nothing will be returned.
        If its a bum target, add to memories as broken for now
        """
        self.path = self.game.find_path(self, self.target)
        if not self.path:
            self.broadcast(f"{self.name} can't path to {self.target.name} {self.target.x}, {self.target.y}")
            self.broken_target(self.target)
            self.target = None

    def check_needs(self):
        """
        Called every turn by take_turn. If not currently satsifying a need with a valid target in mind,
        determine lowest need and find something to fix it.
        - Inventory will be evaluated first to see if they have something for it
        - If looking for work and a task has been assiged, that will be pursued.  Otherwise, the closest
          unoccupied thing that satisfies will be picked and a path returned
        - If a bad target was previously acquired (considered broken) that'll be dropped from evaluation
          - bad targets: Unable to path
        """
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

            if self.satisfying == "work" and self.get_tasks():
                task = self.get_tasks()[0]
                self.target = task.target
                self.target_job = task
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
        - Frees up worker occupation
        - Ticks Mob Memories
        - Ticks Mob needs every four turns
          - Processes Special events as certain stats tank
        """
        # If not preoccupied, check needs and do stuff
        if not self.game.turns % 4:
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
            next_tile = self.game.get_tile(self.target.x, self.target.y)
            self.move(next_tile, arrived=True)
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

    def move(self, dest_tile, swapping=False, arrived=False):
        """
        Handles Player and Coworker Move actions.  If player 'moves' into tile of appliance,
        appliance will be used instead.  Likewise, Coworkers will be directed to do the same
        - dest_tile: Tile to be moved to/use
        - swapping: When True, overrides typical blocked check to allow to coworkers to exchange
          positions if they both want to be in each others' spots
        - arrived: When True, coworker will use target/resolve job.  Needed for when target does not block
        """
        # Standard Move action
        if (not dest_tile.blocked or swapping) and not arrived:
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
        # Will now use target object/resolve request
        else:
            if self.target_job:
                self.target_job.init_request(self)
            else:
                # Assumes one usable object per tile
                appliances = [c for c in dest_tile.contents if getattr(c, "use", None)]
                if appliances:
                    self.use_item(appliances[0])

    def use_item(self, item):
        ''' Called by AI when satisfying need & based on player choice as the popup callback function '''
        item.use(self)

    def pickup_item(self, item):
        item.move_to_inventory(self)

    def drop_item(self, item):
        item.drop_from_inventory(self)

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
        tasks = [f"{x.name}: {x.target.name}" for x in self.get_tasks()]
        return details + attrFormatter(attrs, self, override={"broken": broken, "tasks": tasks, "inventory": inv})
