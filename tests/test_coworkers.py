from tests.base_test import BaseTestCase
from base.enums import ObjType
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

    def test_bladder_trigger(self):
        self.coworker.bladder = 0
        self.coworker.tick_needs()
        self.assertEqual(self.coworker.bladder, 100)
        self.assertEqual(len(self.game.find_objs("Urine")), 1)

    def test_bowels_trigger(self):
        self.coworker.bowels = 0
        self.coworker.tick_needs()
        self.assertEqual(self.coworker.bowels, 100)
        self.assertEqual(len(self.game.find_objs("Poo")), 1)

    def test_fired_trigger(self):
        self.assertTrue("Test" in [x.name for x in self.game.world_objs[ObjType.mob]])
        self.coworker.work = 0
        self.coworker.tick_needs()
        self.assertTrue("Test" not in [x.name for x in self.game.world_objs[ObjType.mob]])
        self.assertEqual(len(self.game.find_objs("Test")), 0)
        self.assertEqual(len(self.game.find_objs("Corpse")), 1)
