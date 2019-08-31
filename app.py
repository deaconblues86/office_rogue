import tcod
import tcod.event as Event

from base.game import Dispatcher, GameInstance
from base.map_gen import MapGenerator
from constants import screen_width, screen_height

# Setup the font.
tcod.console_set_custom_font(
    "arial12x12.png",
    tcod.FONT_LAYOUT_TCOD | tcod.FONT_TYPE_GREYSCALE,
)

# Initialize the root console in a context.
with tcod.console_init_root(
    screen_width, screen_height, order="F", renderer=tcod.RENDERER_SDL2, vsync=True
) as root_console:
    game = GameInstance(root_console)
    dispatcher = Dispatcher(game)
    map_gen = MapGenerator(game)

    map_gen.generate_map()
    while True:
        game.render_all()
        tcod.console_flush()  # Show the console.
        for event in Event.wait():
            dispatcher.dispatch(event)

        root_console.clear()
