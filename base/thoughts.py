from collections import defaultdict
from functools import reduce
from random import randint
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
        self.actor_job = requires.get("job", None)              # Required Job to peform actions
        self.req_task = requires.get("target_task", False)      # Target will raise it's own alarm OR

        self.req_object = requires.get("target", None)          # Target is specified by object name OR
        self.req_tag = requires.get("target_tag", None)         # Target is specified by generalized object tag
        self.req_appliance = self.req_object or self.req_tag    # Normalized Required Target

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

    def find_targets(self):
        if not self.req_appliance:
            return self.actor
        elif self.producers:
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

            # TODO: Use setter/getter approach for stats to avoid the mod check
            if effect.get("new_value"):
                setattr(app_target, app_stat, effect.get("new_value"))
            elif effect.get("modifier"):
                mod = effect.get("modifier")
                if mod < 0:
                    setattr(app_target, app_stat, int(max(getattr(app_target, app_stat, 0) + mod, 0)))
                else:
                    setattr(app_target, app_stat, int(min(getattr(app_target, app_stat, 0) + mod, 100)))
            else:
                exec_vars = {"app_target": app_target, "randint": randint, "ret": 0}
                exec(effect.get("exec"), exec_vars)
                mod = exec_vars["ret"]
                if mod < 0:
                    setattr(app_target, app_stat, int(max(getattr(app_target, app_stat, 0) + mod, 0)))
                else:
                    setattr(app_target, app_stat, int(min(getattr(app_target, app_stat, 0) + mod, 100)))


class ActionCenter():
    def __init__(self, mob):
        self.mob = mob
        # Initilizes Actions based on mob's job
        self.actions = filter(lambda x: not x.get("job", None) or x.get("job", None) == mob.job, game_actions.values())
        self.actions = list(
            map(lambda x: Action(actor=self.mob, **x), self.actions)
        )

    def available_actions(self, target_object):
        return list(
            filter(lambda x: x.valid_target(target_object) and not x.missing_reagents(), self.actions)
        )

    def find_action(self, need):
        """
        How deep can this really go?  Huge production chains of course lead to evaluations within evaluations, but
        is this that really a concern or what we want?
         - The initial impetus of this rougelike was to set up a functional office of sorts, now, with larger goals, we're thinking villages within a world
         - In either case, I would expected a certain amount of separation of duties... Not one guy mining stone, smelting ore it, forging it, etc
           - goods that can't be sourced locally should be requested from traders who look beyond borders
           - also need to ability to train people for missing jobs/create missing appliances
         - The player can certainly do all that, and that's fine, they have a brain.
         - If we assume a certain amount of specialization, which would be better ultimately I feel, then we need a way to manage requests of materials as well
            - "no food at the granary sire"
         - already have plans for a "manager" class whose sole job it is to post requests for items & generally direct workers
        """
        possible_actions = []
        target_action = None
        # Starting from actions that satisfy need (lowest level)
        for action in filter(lambda x: need in x.satisfies, self.actions):
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
        This is where we need to dive through the action tree to figure out the most efficient regardless of all the notes above...
        Let's consider hunting...
        - needs bolts/arrows & needs crossbow/bow
        - OR needs traps & checks traps
            - Traps are easy enough => place traps satsifies work & checks traps satisfies work
                - intresting though, check should take priority & once done, then place
                - place traps would require traps...  reagent check would prioritize check
        - Assuming "hunters" start with req. gear, really only the ammo that matters
        - "Purchase" would be one action
        - "Make" is several (harvet_wood, harvest_stone/(harvest_iron_ore & smelt_iron), make_arrowheads)
        - Think it's safe to, regardless of action, it's always about missing reagents...
            - Maybe "flatten" all missing reagents (going back to "Make"):
                - actions = what gives wood + what gives stone/what gives iron => what gives iron_ore + make_arrowheads
                - at every step, some of these goods could be purchasable
        """
        possible_task_lists = defaultdict(list)
        for possible_action, missing_reagents in possibilites:
            print(possible_action.name)
            task_list = self.walk_action(possible_action, missing_reagents)
            task_list.reverse()
            print(task_list)
            possible_task_lists[possible_action] = task_list

        # Weighing options only by number of tasks for now
        winner = sorted(possible_task_lists, key=lambda x: len(possible_task_lists[x]))[0]
        task_list = possible_task_lists[winner]

        # If we have nested actions, store task list, store missing reagents, & return first item
        # TODO: Assumes list is ordered from top (deep up tree) to bottom (action we actually want)
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
            if target in self.mob.memories.broken_items:
                continue

            # TODO: Dropped as the crow flies eval for actual path.  Depending on Cost, may have to redo
            path = self.mob.calculate_target_path(target_obj=target)
            if path and len(path) < min_distance:
                min_distance = len(path)
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
        attr = getattr(target, self.target_stat)
        attr += self.modifier
        setattr(target, self.target_stat, attr)


class Memories():
    def __init__(self, mob):
        self.mob = mob
        self.broken_items = []
        self.wanted_items = []
        self.work_tasks = []
        self.thoughts = []
        self.relationships = []
        self.iters = 0

    def tick_memories(self):
        """
        Every 20 turns, remove oldest item found to be broken,
        tick thought lifetimes, apply modifiers, and remove timed out thoughts
        """
        self.iters += 1
        if not self.iters % 20:
            if self.broken_items:
                self.broken_items.pop(0)
            for thought in self.thoughts:
                thought.apply_modifier(self.mob)
                thought.duration -= 1
            self.thoughts = [t for t in self.thoughts if t.duration <= 0]
            self.iters = 0

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
