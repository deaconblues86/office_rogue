import math
from collections import defaultdict
from functools import reduce
from constants import game_actions, game_objects
from utils import search_by_obj, search_by_tag, eval_obj_state


class Action():
    def __init__(self, actor, name, chars, color, duration, satisfies=[], requires=[], effects=[], produces=[]):
        self.actor = actor
        self.target = None
        self.reagents = []

        # From Action Defs
        self.name = name
        self.chars = chars
        self.color = color
        self.duration = duration
        self.satisfies = satisfies

        # Initializing Action requirements
        # Required Job to peform actions
        self.actor_job = requires.get("job", None)

        # Target will raise it's own alarm OR
        # Target is specified by object name OR
        # Target is specified by generalized object tag
        #  - req_appliance: mormalizes above required target object requirememts
        self.req_task = requires.get("target_task", False)
        self.req_object = requires.get("target", None)
        self.req_tag = requires.get("target_tag", None)
        self.req_appliance = self.req_task or self.req_object or self.req_tag

        self.req_state = requires.get("target_state", None)     # Target requires a certain state

        self.req_reagents = requires.get("reagents", {})

        # Handling producing actions
        # Will load a dict of Vendors by name as well as what they stock if simple "vending" action
        # Difference being, some actions only make things & some only buy things
        # In either case, it doesn't yield anything on its own (satisifies)
        # In essence, "vending" action mutates depending on good required
        # - target will be determined based on list of vendors
        self.produces = produces
        self.producers = []
        if self.produces and not isinstance(self.produces, list):
            self.producers = {
                x["name"]: [s["name"]for s in x["stock"]]
                for x in game_objects.values() if x.get("stock")
            }
            self.produces = reduce(lambda x, y: x + y, self.producers.values(), [])

        self.effects = effects

    def __str__(self):
        return f"{self.name} action"

    def __repr__(self):
        return f"Action: {self.name} of {self.actor}"

    def find_targets(self):
        if not self.req_appliance:
            return self.actor
        if self.producers:
            # Build a dictionary of possible producers/vendors that sell goods actor wants
            possible_vendors = {
                x: len([good for good in self.actor.memories.wanted_items if good in self.producers[x]])
                for x in self.producers
            }
            best = sorted(possible_vendors, key=lambda x: possible_vendors[x], reverse=True)[0]
            return self.actor.game.find_objs(best, self.req_state)
        elif self.req_task:
            return self.actor.game.find_tasks(self.name)
        elif self.req_object:
            return self.actor.game.find_objs(self.req_object, self.req_state)
        else:
            return self.actor.game.find_tags(self.req_tag, self.req_state)

    def valid_target(self, obj):
        if self.req_task:
            return obj in self.actor.game.find_tasks(self.name)
        elif self.req_object:
            return obj.name == self.req_object and eval_obj_state(obj, self.req_state)
        elif self.req_tag:
            return self.req_tag in obj.tags and eval_obj_state(obj, self.req_state)
        else:
            return True

    def missing_reagents(self):
        missing = []
        if self.req_reagents:
            for reagent in self.req_reagents:
                if reagent.get("name"):
                    search_func = search_by_obj
                else:
                    search_func = search_by_tag

                match = search_func(self.actor.inventory, reagent["name"], reagent.get("state"))
                if match:
                    continue
                missing.append(reagent)

        return missing

    def init_action(self):
        self.target = self.actor.target
        self.actor.occupied += self.duration
        self.target.occupied_by = self.actor

    def tick_action(self):
        self.actor.occupied -= 1
        if not self.actor.occupied:
            self.resolve_action()

    def resolve_action(self):
        for effect in self.effects:
            self.apply_effect(effect)

        self.target.eval_triggers()
        self.actor.finished_action(self)
        self.target.occupied_by = None
        self.target = None              # TODO: Ya know...  could hang on to this target... re-eval as need

    def apply_effect(self, effect):
        # Determines to what the effect is being applied
        if effect["hits"] == "target":
            app_target = self.target
        elif effect["hits"] == "actor":
            app_target = self.actor
        else:
            app_target = [x for x in self.reagents if x.name == effect["hits"]][0]

        # If it's a function call it, else it's a stat
        if effect.get("func"):
            req_method = getattr(app_target, effect["func"])
            args = [self.actor] if effect["func"] == "use" else []  # use functions take actor as an arg
            req_method(*args)
        else:
            app_stat = effect["stat"]
            app_type = effect["mod_type"]
            app_mod = effect["value"]
            app_target.apply_modifier(app_stat, app_mod, app_type)


class ActionCenter():
    def __init__(self, mob):
        self.mob = mob
        # TODO: Usage of this could be expanded based on other criteria besides job
        # Initialize all game actions which will then be trued up based on coworkers job
        self.all_actions = list(
            map(lambda x: Action(actor=self.mob, **x), game_actions.values())
        )
        self.true_up_actions()

    def true_up_actions(self):
        self.actions = [x for x in self.all_actions if not x.actor_job or x.actor_job == self.mob.job]

    def available_actions(self, target_object):
        return list(
            filter(lambda x: x.valid_target(target_object) and not x.missing_reagents(), self.actions)
        )

    def find_action(self, need):
        possible_actions = []
        target_action = None
        # Starting from actions that satisfy need (lowest level)
        for action in filter(
            lambda x: need in x.satisfies and x not in self.mob.memories.unavailable_actions, self.actions
        ):
            missing_reagents = action.missing_reagents()

            # If we have everything we required for what we need, we're good
            if not missing_reagents:
                target_action = action
                break

            possible_actions.append((action, missing_reagents))
        else:
            target_action = self.walk_options(possible_actions)

        return target_action

    def find_target(self, action):
        targets = action.find_targets()
        if targets is self.mob:
            return self.mob
        else:
            return self.determine_closest(targets)

    def store_tasks(self, task_list):
        for task in task_list:
            self.mob.memories.add_job(task)

    def store_missing_reagents(self, reagent_list):
        for reagent in reagent_list:
            self.mob.memories.add_wanted(reagent["name"])

    def walk_action(self, action, missing_reagents):
        action_list = [(action, missing_reagents)]
        for reagent in missing_reagents:
            # TODO: Don't currently have a way to support production search for reagents by tag
            for production in filter(lambda x: reagent["name"] in x.produces, self.actions):
                production_reagents = production.missing_reagents()
                break
            action_list += self.walk_action(production, production_reagents)

        return action_list

    def walk_options(self, possibilites):
        """
        This is where we need to dive through the action tree to figure out the most efficient option
        """
        possible_task_lists = defaultdict(list)
        for possible_action, missing_reagents in possibilites:
            print(possible_action.name)
            task_list = self.walk_action(possible_action, missing_reagents)
            task_list.reverse()
            print(task_list)
            possible_task_lists[possible_action] = task_list

        if not possible_task_lists:
            return None

        # Weighing options only by number of tasks for now
        winner = sorted(possible_task_lists, key=lambda x: len(possible_task_lists[x]))[0]
        task_list = possible_task_lists[winner]

        # If we have nested actions, store task list, store missing reagents, & return first item
        if task_list:
            self.store_tasks([task[0] for task in task_list[1:]])
            self.store_missing_reagents(reduce(lambda x, y: x + y, [task[1] for task in task_list], []))
            first_task = task_list[0][0]
            return first_task
        else:
            return winner

    def determine_closest(self, targets):
        """
        Determines closest target from list that could satisfy needs and isn't occupied.
        - Pathing in GameInstance can reject blocked targets as well if the situation changes
        - determine_closest only called when no target is held or when it was bad
        """
        min_distance = 99999
        closest = None
        targets = filter(lambda x: not x.owner or x.owner is self, targets)
        for target in targets:
            # If target currently in use, skip it
            if target.occupied_by:
                continue

            # If target is known to be broken, skip it
            elif target in self.mob.memories.broken_items:
                continue

            # If target is adjacent, definitely closest
            elif target in self.mob.adjacent():
                return target

            # TODO: Dropped path eval for as the crow flies to separate the
            # resence of obj vs. ability to path to it
            dx = target.x - self.mob.x
            dy = target.y - self.mob.y
            distance = math.sqrt(dx**2 + dy**2)
            if distance < min_distance:
                min_distance = distance
                closest = target

        return closest


class Thought():
    def __init__(self, name, description, duration, target_stat, modifier):
        self.name = name
        self.description = description
        self.duration = duration
        self.target_stat = target_stat
        self.modifier = modifier

    def apply_modifier(self, target):
        target.apply_modifier(self.modifier)


class Memories():
    def __init__(self, mob):
        self.mob = mob
        self.unavailable_actions = []
        self.broken_items = []
        self.wanted_items = []
        self.work_tasks = []
        self.thoughts = []
        self.relationships = {}
        self.broken_cycle = 0

    def tick_memories(self):
        """
        Every 15 cycles, 1 cycle == 6 game turns, remove oldest item found to be broken
        Tick thought lifetimes, apply modifiers, and remove timed out thoughts
        """
        self.broken_cycle += 1
        if self.broken_cycle == 15:
            self.broken_cycle = 0
            if self.broken_items:
                self.broken_items.pop(0)
            if self.unavailable_actions:
                self.unavailable_actions.pop(0)

        for thought in self.thoughts:
            thought.apply_modifier(self.mob)
            thought.duration -= 1
        self.thoughts = [t for t in self.thoughts if t.duration <= 0]

    def add_unavailable(self, obj):
        """
        Try to pop already found action with no available target from list if present
        Add unavailable action object to end of list
        - pop done to "refresh" memory
        """
        try:
            i = self.unavailable_actions.index(obj)
            self.unavailable_actions.pop(i)
        except ValueError:
            pass
        finally:
            self.unavailable_actions.append(obj)

    def add_broken(self, obj):
        """
        Try to pop already found broken obj from list if present
        Add broken object to end of list
        - pop done to "refresh" memory
        """
        try:
            i = self.broken_items.index(obj)
            self.broken_items.pop(i)
        except ValueError:
            pass
        finally:
            self.broken_items.append(obj)

    def add_wanted(self, item_name):
        self.wanted_items.append(item_name)

    def remove_wanted(self, item_name):
        self.wanted_items = [x for x in self.wanted_items if x != item_name]

    def add_job(self, job):
        self.work_tasks.append(job)

    def start_next_job(self):
        return self.work_tasks.pop(0)

    def interrupt_job(self, job):
        self.work_tasks.insert(0, job)

    def remove_job(self, job):
        self.work_tasks = [x for x in self.work_tasks if x is not job]
