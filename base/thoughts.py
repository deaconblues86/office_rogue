class WorkRequest():
    def __init__(self, game, name, job, target, actions, target_func=None):
        self.game = game
        self.name = name
        self.job = job
        self.target = target
        self.actions = actions
        self.target_func = target_func

        self.assignee = None

    def init_request(self, user):
        self.game.submit_actions(self.actions, user, self)

    def resolve_request(self):
        if self.target_func:
            req_method = getattr(self.target, self.target_func)
            req_method()
        self.assignee.remove_task()


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
