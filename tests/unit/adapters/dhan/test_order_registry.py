"""OrderRegistry — bidirectional local_id <-> broker orderId map."""
from __future__ import annotations

import unittest

from scalpr.adapters.dhan._order_registry import OrderRegistry


class TestOrderRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = OrderRegistry()

    def test_register_maps_both_directions(self):
        self.reg.register("local-1", "ORD123456")
        self.assertEqual(self.reg.broker_id("local-1"), "ORD123456")
        self.assertEqual(self.reg.local_id("ORD123456"), "local-1")

    def test_unknown_ids_return_none(self):
        self.assertIsNone(self.reg.broker_id("nope"))
        self.assertIsNone(self.reg.local_id("nope"))

    def test_re_register_replaces_stale_reverse_entry(self):
        """A re-submitted local id must not leave the old broker id resolvable."""
        self.reg.register("local-1", "ORD_OLD")
        self.reg.register("local-1", "ORD_NEW")
        self.assertEqual(self.reg.broker_id("local-1"), "ORD_NEW")
        self.assertEqual(self.reg.local_id("ORD_NEW"), "local-1")
        self.assertIsNone(self.reg.local_id("ORD_OLD"))

    def test_forget_removes_both_directions(self):
        self.reg.register("local-1", "ORD123456")
        self.reg.forget("local-1")
        self.assertIsNone(self.reg.broker_id("local-1"))
        self.assertIsNone(self.reg.local_id("ORD123456"))

    def test_forget_unknown_local_id_is_a_no_op(self):
        self.reg.forget("never-registered")

    def test_all_broker_ids_lists_every_registered_broker_id(self):
        self.reg.register("local-1", "ORD1")
        self.reg.register("local-2", "ORD2")
        self.assertEqual(sorted(self.reg.all_broker_ids()), ["ORD1", "ORD2"])

    def test_empty_broker_id_is_rejected(self):
        """A blank orderId means the broker response was malformed; refuse it
        rather than poisoning the map with an unusable key."""
        with self.assertRaises(ValueError):
            self.reg.register("local-1", "")
        self.assertIsNone(self.reg.broker_id("local-1"))
