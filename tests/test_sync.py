#!/usr/bin/env python3
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "iac"))
import sync_consent  # noqa: E402


class MergeTest(unittest.TestCase):
    def test_assigns_purpose_and_keeps_the_tool(self):
        config = {
            "debugKey": "do-not-copy-into-logs",
            "tools": {"ga": {"name": "Analytics", "enabled": True, "type": "component"}},
            "triggers": {"pageview": {"name": "Pageview"}},
        }
        consent = {
            "enabled": True,
            "purposes": {"analytics": {"name": "Analytics", "description": "Measure use."}},
        }
        updated = sync_consent.merge(config, consent, {"ga": "analytics"})
        self.assertEqual(updated["tools"]["ga"]["defaultPurpose"], "analytics")
        self.assertEqual(updated["tools"]["ga"]["name"], "Analytics")
        self.assertEqual(updated["triggers"], config["triggers"])
        self.assertEqual(updated["consent"], consent)
        self.assertNotIn("defaultPurpose", config["tools"]["ga"])

    def test_empty_map_does_not_create_a_tool(self):
        config = {"tools": {}}
        consent = {
            "enabled": True,
            "purposes": {"analytics": {"name": "Analytics", "description": "Measure use."}},
        }
        updated = sync_consent.merge(config, consent, {})
        self.assertEqual(updated["tools"], {})
        self.assertTrue(updated["consent"]["enabled"])

    def test_missing_tool_is_refused(self):
        config = {"tools": {}}
        consent = {
            "enabled": False,
            "purposes": {"analytics": {"name": "Analytics", "description": "Measure use."}},
        }
        with self.assertRaises(ValueError):
            sync_consent.merge(config, consent, {"ga": "analytics"})

    def test_unknown_purpose_is_refused(self):
        config = {"tools": {"ga": {"name": "Analytics"}}}
        consent = {"enabled": True, "purposes": {}}
        with self.assertRaises(ValueError):
            sync_consent.merge(config, consent, {"ga": "analytics"})


if __name__ == "__main__":
    unittest.main()
