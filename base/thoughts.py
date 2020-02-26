from random import randint
from constants import game_actions, game_objs, actions_by_need


# This is being trashed - at least in its current implementation
# class WorkRequest():
#     def __init__(self, game, name, job, target, actions, target_func=None):
#         self.game = game
#         self.name = name
#         self.job = job
#         self.target = target
#         self.actions = actions
#         self.target_func = target_func

#         self.assignee = None

#     def init_request(self, user):
#         self.game.submit_actions(self.actions, user, self)

#     def resolve_request(self):
#         if self.target_func:
#             req_method = getattr(self.target, self.target_func)
#             req_method()
#         self.assignee.remove_task()


class Action():
    def __init__(self, actor, name, chars, color, duration, satisfies, requires=[], effects=[], produces=None):
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
        self.req_tags = requires.get("target_tag", None)        # Target is specified by generalized object tag
        self.req_state = requires.get("target_state", None)     # Target requires a certain state
        self.req_reagents = requires.get("reagents", [])

        # Handling producing actions
        # Will load a dict of Vendors by name as well as what they stock
        self.produces = produces
        if self.produces and not isinstance(self.produces, list):
            self.producers = {x.name: x.stock for x in game_objs if x.stock}
            print(self.producers)

        self.effects = effects

        # Sets inital state of actor & target (if not work request)
        # TODO: Currently allowing for multitasking.  Each Action should pile on to the user occupied attr
        # (e.g. 4 + 2).  Though, they're all ticked essentially simultaneously, only once they're nolonger occupied
        # will the actor resolve its actions
        # May want to keep like this since most things limited by proximity, but for some things could add
        # a blocking status.  Or maybe blocking not necessary since time stacks as it does prior to resolution
        self.actor.occupied += duration

    def find_target(self):
        pass

    def tick_action(self):
        self.actor.occupied -= 1
        if not self.actor.occupied:
            self.resolve_action()

    def resolve_action(self):
        for effect in self.effects:
            self.apply_effect(effect)

        self.target.occupied_by = None
        self.target.eval_events()
        self.actor.finished_action(self)

    def apply_effect(self, effect):
        # Determines to what the effect is being applied
        if effect["hits"] == "target":
            app_target = self.target
        elif effect["hits"] == "actor":
            app_target = self.actor
        else:
            app_target = [x for x in self.reagents if x.name == effect["hits"]][0]

        # If it's function call it, else it's a stat
        if effect.get("func"):
            req_method = getattr(app_target, effect["func"])
            req_method()
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
        self.potential_actions = list(
            filter(lambda x: x.get("job", None) is None or x.get("job", None) == mob.job, game_actions)
        )
        self.true_up_available()

    def true_up_available(self):
        # Reassess what can be done as new items added to inventory
        pass


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

    def finish_job(self, job):
        self.work_tasks = [x for x in self.work_tasks if x is not job]
