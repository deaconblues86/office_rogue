import json
from unittest import TestCase
from base.thoughts import Memories


class MemoryTestCase(TestCase):
    def setUp(self):
        mob = {
            "name": "placeholder_mob",
            "energy": 100,
            "mmood": 100,
        }
        self.memory = Memories(mob)

    def test_add_unsatisfied(self):
        self.memory.add_unsatisfied("work")
        self.assertEqual(self.memory.unsatisfied, ["work"])

        self.memory.add_unsatisfied("social")
        self.assertEqual(self.memory.unsatisfied, ["work", "social"])

        self.memory.add_unsatisfied("energy")
        self.assertEqual(self.memory.unsatisfied, ["work", "social", "energy"])

        # Adds already present will be popped and added to end
        self.memory.add_unsatisfied("work")
        self.assertEqual(self.memory.unsatisfied, ["social", "energy", "work"])

    def test_add_unavailable(self):
        self.memory.add_unavailable("computing")
        self.assertEqual(self.memory.unavailable_actions, ["computing"])

        self.memory.add_unavailable("cleaning")
        self.assertEqual(self.memory.unavailable_actions, ["computing", "cleaning"])

        self.memory.add_unavailable("writing")
        self.assertEqual(self.memory.unavailable_actions, ["computing", "cleaning", "writing"])

        # Adds already present will be popped and added to end
        self.memory.add_unavailable("computing")
        self.assertEqual(self.memory.unavailable_actions, ["cleaning", "writing", "computing"])

    def test_add_broken(self):
        self.memory.add_broken("terminal")
        self.assertEqual(self.memory.broken_items, ["terminal"])

        self.memory.add_broken("toilet")
        self.assertEqual(self.memory.broken_items, ["terminal", "toilet"])

        self.memory.add_broken("sink")
        self.assertEqual(self.memory.broken_items, ["terminal", "toilet", "sink"])

        # Adds already present will be popped and added to end
        self.memory.add_broken("terminal")
        self.assertEqual(self.memory.broken_items, ["toilet", "sink", "terminal"])

    def test_add_remove_wanted(self):
        self.memory.add_wanted("coffee")
        self.assertEqual(self.memory.wanted_items, ["coffee"])

        self.memory.add_wanted("guitar")
        self.assertEqual(self.memory.wanted_items, ["coffee", "guitar"])

        # Duplicates will not be added
        self.memory.add_wanted("coffee")
        self.assertEqual(self.memory.wanted_items,  ["coffee", "guitar"])

        self.memory.remove_wanted("coffee")
        self.assertEqual(self.memory.wanted_items, ["guitar"])

    def test_tick_memories(self):
        self.memory.broken_items = ["terminal", "toilet", "sink"]
        self.memory.unavailable_actions = ["computing", "cleaning", "writing"]
        self.memory.wanted_items = ["coffee", "guitar"]
        self.memory.unsatisfied = ["work", "social", "energy"]

        for x in range(15):
            self.memory.tick_memories()

        self.assertEqual(self.memory.broken_items, ["toilet", "sink"])
        self.assertEqual(self.memory.unavailable_actions, ["cleaning", "writing"])
        self.assertEqual(self.memory.wanted_items, ["coffee", "guitar"])
        self.assertEqual(self.memory.unsatisfied, ["social", "energy"])

    def tearDown(self):
        pass
