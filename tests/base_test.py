import json
from unittest import TestCase
from unittest.mock import patch
from base.game import GameInstance
from base.map_gen import MapGenerator


def message_patch(game, *args, **kwargs):
    """
    Intercepts messages that would normally be displayed through render
     - Pretty much only called by BaseObject.broadcast()
    """
    return f"{','.join(args)} - {json.dumps(kwargs)}"


class BaseTestCase(TestCase):
    def setUp(self):
        self.game = GameInstance()
        self.game.debugging = True
        self.map_gen = MapGenerator(self.game)

        self.map_gen.generate_map()
        self.map_gen.generate_path_map()

        # self.broadcase_patch = patch("base.game.GameInstance.log_message", message_patch)
        # self.broadcase_patch.start()

    def tearDown(self):
        pass
        # self.broadcase_patch.stop()
