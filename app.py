import tcod
import tcod.event as Event

from base.game import Dispatcher, GameInstance
from base.renderer import Renderer
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
    game = GameInstance()
    renderer = Renderer(game, root_console)
    dispatcher = Dispatcher(game)
    map_gen = MapGenerator(game)

    map_gen.generate_map()
    map_gen.generate_path_map()

    fps = 20
    iters = 0
    while True:
        iters += 1
        renderer.render_all()
        renderer.render_actions()

        renderer.render_bars()
        renderer.render_messages()
        renderer.render_tasks()
        tcod.console_flush()  # Show the console.

        # TODO: This exists only to let the game tick while player is occupied
        # No longer really applies so long as the game runs in realtime
        # if not game.player.occupied:
        #     player_busy = None
        # else:
        #     player_busy = 1

        # TODO: While loop currently runs twice for each key press (up and down)
        # May not be a problem, but need to watch game ticks
        # Think this only applies when blocking on keystrok event, which we're not anymore
        for event in Event.get():
            dispatcher.dispatch(event)

        if not iters % fps:
            game.run_coworkers()
            iters = 0

        renderer.clear()
