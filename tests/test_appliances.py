from tests.base_test import BaseTestCase
from constants import game_objects


class TestApplianceClass(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.appliance = self.game.create_object(0, 0, game_objects["T"])
        self.user = self.game.create_object(0, 0, game_objects["Coworker"])

    def test_not_broken(self):
        self.appliance.eval_triggers()
        self.assertTrue("repairing" not in self.game.work_requests)

    def test_broken(self):
        self.assertEqual(len(self.game.work_requests.keys()), 0)
        # Might as well test that negatives work for these less or equals
        self.appliance.durability = -1
        self.appliance.eval_triggers()
        self.assertTrue("repairing" in self.game.work_requests)

    def test_not_dirty(self):
        self.appliance.eval_triggers()
        self.assertTrue("cleaning" not in self.game.work_requests)

    def test_dirty(self):
        self.assertEqual(len(self.game.work_requests.keys()), 0)
        # Might as well test that negatives work for these less or equals
        self.appliance.cleanliness = -1
        self.appliance.eval_triggers()
        self.assertTrue("cleaning" in self.game.work_requests)

    def test_occupied(self):
        # Name needs to be the same for mesage test
        self.user.name = 'Natalie'
        self.appliance.occupied_by = self.user

        self.assertFalse(self.appliance.can_use(self.user))
        self.assertEqual(self.game.game_msgs, [('Toilet: 0,0 occupied by Natalie', 'white')])
