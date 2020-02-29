from base.enums import ObjType
from constants import colors, game_objects
from utils import eval_obj_state


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

        self.occupied_by = None
        self.durability = durability
        self.cleanliness = 100
        self.state = ""

        self.triggers = kwargs.get("triggers", [])

    def adjacent(self):
        # Asks GameInstance 'What's Next to Me?
        return self.game.get_adjacent(self)

    @property
    def broken(self):
        return self.durability <= 0

    def destroy(self):
        self.game.delete_object(self)

    def init_actions(self, user, actions=[]):
        if not actions:
            self._action()
            return None

        self.game.log_actions(actions, user, self)

    def _action(self):
        self.broadcast(f"{self.name.capitalize()} has no use!", "red")

    def eval_triggers(self):
        triggered = []
        for trigger in self.triggers:
            if eval_obj_state(self, trigger):
                triggered.append(self.triggers[trigger])

        for trigger in triggered:
            if trigger.get("request"):
                self.log_request(self, trigger["request"])
            if trigger.get("become"):
                self.transform_object(self, trigger["become"])
            if trigger.get("emits"):
                self.log_emitter(self, trigger["emits"])

    def broadcast(self, message, color="white"):
        """ Publishes call backs from objects to game """
        self.game.log_message(message, color)

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        return attrFormatter(["durability", "state", "occupied_by"], self, base=True)


class Item(BaseObject):
    def __init__(self, satisfies, actions=[], owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.satisfies = satisfies
        self.actions = actions

        # Note that owner & holder are not always the same
        # Holder: always current possessor
        # Owner: person who purchased item or hodl item as it was transformed (for whatever reason)
        self.owner = owner
        self.holder = None

    def use(self, user):
        if self.owner and self.owner is not user:
            self.broadcast(f"{self.name} doesn't belong to {user.name}")
        elif self.broken:
            self.broadcast(f"{self.name} is broken")
            user.broken_target(self)
        elif self.occupied_by:
            print(f"{self.name}: {self.x},{self.y} occupied by {self.occupied_by.name}")
            user.broken_target(self)
        else:
            self.init_actions(user, self.actions)

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
    def __init__(self, satisfies, stock, actions=[], owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.satisfies = satisfies
        self.stock = stock
        self.actions = actions
        self.owner = owner
        self.inventory = []

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
        self.init_actions(user, self.actions)
        if user is self.game.player:
            self.game.init_popup(self.name.capitalize(), options=self.inventory, popup_func=self.dispense)
        else:
            # AI will choose first item to satisfy their needs
            # If satisfying isn't found, they'll consider it broken
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
        user.pickup_item(item)
        user.broadcast(f"{user.name.capitalize()} received {item.name}", "white")

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        inv = [x.name for x in self.inventory]
        grouped_inv = set([f"{x}: {inv.count(x)}" for x in inv])
        details = super().dump()
        return details + attrFormatter(["owner", "satisfies"], self, override={'stock': grouped_inv})
