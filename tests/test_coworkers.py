import json
from tests.base_test import BaseTestCase
from base.enums import ObjType
from constants import game_objects


class TestCoworkerClass(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.coworker = self.game.create_object(0, 0, game_objects["Coworker"])
        self.coworker.name = "Test"
        print(self.coworker.job)

    def test_check_needs(self):
        self.coworker.bladder = 5
        self.coworker.check_needs()
        self.assertEqual(self.coworker.satisfying, "bladder")
        self.assertEqual(repr(self.coworker.target_action), "Action: peeing_in_toilet of Test at 0, 0")
        self.assertEqual(
            [x.split(" at ")[0] for x in self.game.game_debug_msgs],    # Need to normalize error message
            ["Test can't path to Toilet"]
        )

    def test_unsatsified(self):
        self.coworker.bowels = 5
        toilets = self.game.find_objs("Toilet")
        for toilet in toilets:
            toilet.occupied_by = True

        self.coworker.check_needs()
        self.coworker.check_needs()
        self.assertNotEqual(self.coworker, "bowels")
        self.assertEqual(self.coworker.memories.unsatisfied, ["bowels"])

        for toilet in toilets:
            toilet.occupied_by = None

    def test_action_weighting(self):
        """
        Test that action chosen is based on weighted criteria
        """
        # Move the coworker somewhere within the level (top-right corner) to avoid pathing issues
        # and test for thirst
        self.coworker.thirst = 5
        self.coworker.x = 5
        self.coworker.y = 5
        self.coworker.check_needs()

        self.assertEqual(self.coworker.target_action.name, "making_coffee")
        self.coworker.perform_action()
        self.coworker.target_action.resolve_action()
        self.coworker.thirst = 5
        self.coworker.check_needs()

    def test_task_action_failure(self):
        """
        Test to verify that actions require associated tasks will not be performed unless the task actually exists
        """
        self.coworker.work = 5
        self.coworker.job = "housekeeping"
        self.coworker.action_center.true_up_actions()
        self.coworker.check_needs()

        # First attempt will be unavailable as nothing is dirty
        self.assertEqual(self.coworker.satisfying, "work")
        self.assertEqual(
            [repr(x) for x in self.coworker.memories.unavailable_actions],
            ["Action: cleaning of Test at 0, 0"]
        )
        self.assertEqual(self.coworker.target, None)

        # Second attempt will be unavailable as no "Trash" objects exist
        self.coworker.check_needs()
        self.assertEqual(self.coworker.satisfying, "work")
        self.assertEqual(
            [repr(x) for x in self.coworker.memories.unavailable_actions],
            ["Action: cleaning of Test at 0, 0", "Action: cleaning_up of Test at 0, 0"]
        )
        self.assertEqual(self.coworker.target, None)

        # Third attempt may work if unowned terminals exist, otherwise
        # computing will at least be tried.  In either case, no target will be acquired as,
        # even if an available terminal exist, the test coworker can't path to it.
        self.coworker.check_needs()
        if any([x.owner is None for x in self.game.find_objs("Terminal")]):
            self.assertEqual(repr(self.coworker.target_action), "Action: computing of Test at 0, 0")
            self.assertEqual(self.coworker.target, None)
        else:
            self.assertEqual(
                [repr(x) for x in self.coworker.memories.unavailable_actions],
                [
                    "Action: cleaning of Test at 0, 0",
                    "Action: cleaning_up of Test at 0, 0",
                    "Action: computing of Test at 0, 0"
                ]
            )
            self.assertEqual(self.coworker.target, None)

    def test_task_action_success(self):
        """
        Test that once a task is actually created, the associated action will be performed
        """
        toilet = self.game.find_objs("Toilet")[0]
        toilet.cleanliness = 0
        toilet.eval_triggers()

        self.coworker.work = 5
        self.coworker.job = "housekeeping"
        self.coworker.action_center.true_up_actions()

        # In addtion to changing job, lets move the coworker somewhere within the level (top-right corner actually)
        # This way, we can verify we pick up our dirty toilet as a target
        self.coworker.x = 5
        self.coworker.y = 5

        self.coworker.check_needs()
        self.assertEqual(self.coworker.satisfying, "work")
        self.assertEqual(self.coworker.target, toilet)

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
        self.assertTrue(self.coworker not in self.game.world_objs[ObjType.mob])

    def test_quit_trigger(self):
        self.assertTrue("Test" in [x.name for x in self.game.world_objs[ObjType.mob]])
        self.coworker.mood = 0
        self.coworker.tick_needs()
        self.assertTrue("Test" not in [x.name for x in self.game.world_objs[ObjType.mob]])
        self.assertEqual(len(self.game.find_objs("Test")), 0)
        self.assertEqual(len(self.game.find_objs("Corpse")), 1)
        self.assertTrue(self.coworker not in self.game.world_objs[ObjType.mob])
