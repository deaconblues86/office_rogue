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
    map_gen.generate_path_map()

    fps = 20
    iters = 0
    while True:
        iters += 1
        game.render_all()
        game.render_bars()
        game.render_messages()
        tcod.console_flush()  # Show the console.

        # if not game.player.occupied:
        #     player_busy = None
        # else:
        #     player_busy = 1

        # TODO: While loop currently runs twice for each key press (up and down)
        # May not be a problem, but need to watch game ticks
        for event in Event.get():
            dispatcher.dispatch(event)

        if not iters % fps:
            game.run_coworkers()
            iters = 0

        root_console.clear()
