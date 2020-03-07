from base.enums import ObjType
from constants import colors, game_objects
from utils import eval_obj_state


def attrFormatter(obj, attrs=[], override={}, base=False):
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

        self.triggers = kwargs.get("triggers", [])

    def adjacent(self):
        # Asks GameInstance 'What's Next to Me?
        return self.game.get_adjacent(self)

    @property
    def broken(self):
        return self.durability <= 0

    def destroy(self):
        self.game.delete_object(self)

    def eval_triggers(self):
        triggered = []
        for trigger in self.triggers:
            if eval_obj_state(self, trigger):
                triggered.append(self.triggers[trigger])

        for trigger in triggered:
            if trigger.get("request"):
                self.game.log_request(self, trigger["request"])
            elif trigger.get("become"):
                self.game.transform_object(self, trigger["become"])
            elif trigger.get("emit"):
                self.game.log_emitter(self, trigger["emit"])
            elif trigger.get("create"):
                self.game.create_object(self, self.x, self.y, trigger["create"])

    def broadcast(self, message, color="white"):
        """ Publishes call backs from objects to game """
        self.game.log_message(message, color)

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        return attrFormatter(self, ["durability", "cleanliness", "occupied_by"], base=True)


class Appliance(BaseObject):
    def __init__(self, tags, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tags = tags
        self.owner = owner
        self.holder = None

    def can_use(self, user):
        can_use = False
        if self.owner and self.owner is not user:
            self.broadcast(f"{self.name} doesn't belong to {user.name}")
            user.broken_target()
        elif self.broken:
            self.broadcast(f"{self.name} is broken")
            user.broken_target()
        elif self.occupied_by:
            self.broadcast(f"{self.name}: {self.x},{self.y} occupied by {self.occupied_by.name}")
            user.broken_target()
        else:
            can_use = True

        return can_use

    def dump(self):
        """ Dumps pertinent object attributes for user to view """
        details = super().dump()
        return details + attrFormatter(self, ["owner"])


class Item(Appliance):
    def __init__(self, holder=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Note that owner (from Appliance) & holder are not always the same
        # Holder: always current possessor
        # Owner: person who purchased item or held item as it was transformed (for whatever reason)
        self.holder = holder

    def can_use(self, user):
        # Items can only be used while held
        return user == self.holder


class Vendor(Appliance):
    '''
    Vendor's dispense items from a limited pool
    Player may choose from menu while AI will choose first to satisfy
    Vendor no longer loses durability like other items
    Instead stocks are drained
    '''
    def __init__(self, stock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stock = stock
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
                self.inventory.append(obj)

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
            # If satisfying isn't found, they'll consider it broken
            desired = filter(lambda x: user.wants_item(x), self.inventory)
            for item in desired:
                self.dispense(item, user)
                break
            else:
                user.broken_target()

    def dispense(self, item, user=None):
        """
        Places requested Item in users inventory if not full
        - Items bought from vendor will be "owned" by user
        - Coworkers should use items in inventory first so full inventory shouldn't matter
        - Coworkers instructed to "pickup_item" as part of dispense (handles whole "holder" thing)
        - Inventory should be evaluated as part of action resolution so, if empty, restock request will be made
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
        return details + attrFormatter(self, override={'stock': grouped_inv})
