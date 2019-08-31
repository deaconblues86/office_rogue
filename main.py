import tcod as libtcod
import tcod.event as event
from traits import *
from constants import LIMIT_FPS
from base.objects import Player, BasicCoworker


out = open("coworkers.txt", "w")

def player_move_or_attack(dx, dy):
    global fov_recompute
    x = player.x + dx
    y = player.y + dy

    target = None
    for object in objects:
        if object.x == x and object.y == y:
            target = object
            break

    if target:
        if target.blocks:
            if target.fighter:
                player.fighter.give_social(target)
            else:
                player.use_object(target)
        else:
            player.move(dx, dy)
            fov_recompute = True
    else:
        player.move(dx, dy)
        fov_recompute = True


def player_death(player):
    global game_state
    message("You're Fired!", libtcod.red)
    game_state = "dead"

    player.char = "%"
    player.color = libtcod.dark_red


def request_worker(ai):

    coworker = ai.owner

    # Maxing out Work for IT -- Need to tick work to check for broken objects
    # coworker.fighter.work_drain = 0
    coworker.fighter.work = coworker.fighter.max_work
    coworker.fighter.specialty = "repair"


def request_work(ai, obj_names):

    # Creating list of requests to handle requests for terminal service
    requests = [x for x in objects if x.name in obj_names and x.state == "broken"]

    # Setting work drain at plus 10% for each broken machine
    if len(requests) != 0:
        ai.owner.fighter.work_drain += ai.owner.fighter.work_drain * 0.1
        ai.owner.state += "-brepairing"
        print([x.name for x in requests], ai.owner.fighter.work_drain)

    else:
        ai.owner.fighter.work = ai.owner.fighter.max_work
        ai.owner.state = "success: " + ai.owner.state
        print("nothing broken found")

    return requests


# Sets FPS limit (only affects realtime)
libtcod.sys_set_fps(LIMIT_FPS)

# Sets player
social = libtcod.random_get_int(0, 25, 100)
hunger = libtcod.random_get_int(0, 25, 100)
thirst = libtcod.random_get_int(0, 25, 100)
bladder = libtcod.random_get_int(0, 75, 100)
bowels = libtcod.random_get_int(0, 75, 100)
energy = libtcod.random_get_int(0, 25, 100)

fighter_component = Player(
    social=social,
    hunger=hunger,
    thirst=thirst,
    bladder=bladder,
    bowels=bowels,
    energy=energy,
    traits=None,
    death_function=player_death,
)
player = Object(
    "player",
    SCREEN_WIDTH / 2,
    SCREEN_HEIGHT / 2,
    "@",
    libtcod.white,
    blocks=True,
    fighter=fighter_component,
    satisfies=["social"],
    state="idle",
)

COWORKERS.append(player)

objects = [player]
game_msgs = []

# Sets up font for Console
libtcod.console_set_custom_font(
    "arial12x12.png", libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD
)

# Init Console Window
with libtcod.console_init_root(
    SCREEN_WIDTH, SCREEN_HEIGHT, "CIS", False, renderer=libtcod.RENDERER_SDL2, vsync=True
) as root_console:
    # Generates Map
    make_map()

    # a warm welcoming message!
    message("Welcome to your new job...", libtcod.red)

    # Sets up main loop (each pass == turn/frame) --> runs until window is closed
    while True:

        t = event.get()
        # print(t)
        libtcod.sys_check_for_event(
            libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse
        )

        render_all()

        libtcod.console_blit(
            con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0
        )  # Writing offscreen console to main console

        # Calls key function.  Only returns True is exit is hit
        player_action = handle_keys()

        # Need to remove didn't take turn check for realtime & fix key response
        # if game_state == 'playing' and player_action != 'didnt-take-turn':
        # if player_action == 'wait':
        #     message("Player Waits...")
        if game_state == "playing":
            if player_action != "didnt-take-turn":
                for object in objects:
                    if object.ai:
                        object.fighter.tick_needs()
                        object.ai.take_turn()
                        object.fighter.check_needs()

                ### Inconsistent: AI ticks needs, then performs actions
                player.fighter.tick_needs()
                player.fighter.check_needs()

                TURN_COUNT += 1
                out.write(
                    "\n------------------------------------------------------------------\n"
                )

        for o in objects:
            object.clear()

        for coworker in COWORKERS:
            if "success" in coworker.state:
                coworker.state = "idle"

        libtcod.console_flush()  # Flushes console window (always at end of loop to refresh screen)

        # time.sleep(GAME_SPEED)
        if player_action == "exit":
            break


out.close()
