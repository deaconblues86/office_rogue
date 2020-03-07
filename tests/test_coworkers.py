from tests.base_test import BaseTestCase
from constants import game_objects


class TestCoworkerClass(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.coworker = self.game.create_object(0, 0, game_objects["Coworker"])
        self.coworker.name = "Test"

    def test_check_needs(self):
        self.coworker.bladder = 5
        self.coworker.check_needs()
        self.assertEqual(self.coworker.satisfying, "bladder")
        self.assertEqual(self.game.game_debug_msgs, ["Test can't find a target to perform peeing_in_toilet"])
