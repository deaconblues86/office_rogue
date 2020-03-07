import textwrap
from random import randint
from tcod.console import Console
from constants import (
    screen_width,
    map_width,
    map_height,
    BAR_WIDTH,
    STATS,
    MSG_HEIGHT,
    msg_width,
    colors,
)


class PopUpMenu():
    # Configurable PopUp attrs
    # - These default values will be reloaded if others not provided
    dest_x = 0
    dest_y = 0
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
    def load_config(cls, dest_x, dest_y, width, height):
        cls.dest_x = dest_x
        cls.dest_y = dest_y
        cls.popup_width = width
        cls.popup_height = height

    @classmethod
    def load_options(cls, title, msg, options, popup_config=None):
        if not popup_config:
            cls.load_config(0, 0, map_width // 2, map_height // 2)
        else:
            cls.load_config(**popup_config)

        cls.title = title
        cls.text = ""
        if msg:
            cls.text += f"{msg}\n\n"
            print(cls.text)

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
            cls.dest_x,
            cls.dest_y,
            0,
            0,
            cls.popup_width,
            cls.popup_height,
            1.0,
            0.9,
        )


class Renderer():
    def __init__(self, game, root_console):
        self.game = game
        self.root_console = root_console
        self.game.renderer = self

        # Creating off screen console for UI - allows for alpha transparency
        self.popup = PopUpMenu

        # Pull bg color
        self.bg_color = tuple(colors["black"])

        self.action_cache = {}

    def render_all(self):
        for obj_type in self.game.world_objs:
            for obj in self.game.world_objs[obj_type]:
                self.render(obj)

        if self.game.cursor:
            self.render(self.game.cursor)

        if self.game.popup_open:
            self.render_popup()

    def render(self, obj):
        self.root_console.print(x=obj.x, y=obj.y, string=obj.char, fg=obj.color, bg=colors["black"])

    def render_actions(self):
        for action in self.game.actions:
            if not self.action_cache.get(action):
                self.action_cache[action] = []

            char = action.chars[randint(0, len(action.chars)-1)]
            adjacent = [(t.x, t.y) for t in self.game.get_adjacent(action.actor)]
            pos = adjacent[randint(0, len(adjacent) - 1)]
            args = {"x": pos[0], "y": pos[1], "string": char, "fg": colors[action.color], "bg": colors["black"]}

            for cache in self.action_cache[action]:
                self.root_console.print(**cache)

            self.root_console.print(**args)
            self.action_cache[action].append(args)

    def render_bars(self):
        for i, stat in enumerate(STATS):
            self.render_bar(i+1, *stat)

    def render_bar(self, count, stat, color):
        x = 1
        y = map_height + count
        val = getattr(self.game.player, stat)
        top = getattr(self.game.player, f"max_{stat}")
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

        # Starting with latest messages, capture as many lines as can be displayed
        rendered_msgs = []
        for msg, color in reversed(self.game.game_msgs):
            msg_lines = textwrap.wrap(msg, msg_width)
            rendered_msgs = [(line, color) for line in msg_lines] + rendered_msgs
            if len(rendered_msgs) > MSG_HEIGHT:
                break
        for msg, color in rendered_msgs[-1 * MSG_HEIGHT:]:
            y += 1
            self.root_console.print(x=x + 1, y=y, string=msg, fg=colors[color])

    def render_popup(self):
        self.popup.draw_popup(self.root_console)

    def init_popup(self, title, msg=None, options=[], popup_func=None):
        self.game.popup_open = True
        self.game.popup_options = options
        self.game.popup_func = popup_func
        self.popup.load_options(title, msg, [x if isinstance(x, str) else x.name for x in self.game.popup_options])

    def render_tasks(self):
        x = map_width
        self.root_console.print(x=x, y=0, string="Tasks")
        self.root_console.print(x=x, y=1, string="-" * (screen_width - map_width))

        y = 2
        for task in self.game.work_requests:
            objs = self.game.work_requests[task]
            for obj in objs:
                self.root_console.print(x=x, y=y, string=task)
                self.root_console.print(x=x, y=y+2, string=f" Trg: {obj.name}")
                self.root_console.print(x=x, y=y+3, string=f" Loc: {obj.x}, {obj.y}")
                y += 4

    def clear(self):
        self.root_console.clear(bg=self.bg_color)
