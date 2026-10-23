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

    def test_enabling_consent_over_an_empty_tool_map_is_refused(self):
        """THE DISCRIMINATING CASE for issue #1.

        This state used to succeed and then print a note about itself after
        the PUT. Cloudflare does not gate a tool with no defaultPurpose, so
        this combination shows a modal, writes a cookie and gates nothing.
        """
        config = {"tools": {}}
        consent = {
            "enabled": True,
            "purposes": {"analytics": {"name": "Analytics", "description": "Measure use."}},
        }
        with self.assertRaises(ValueError) as caught:
            sync_consent.merge(config, consent, {})
        self.assertIn("empty tool map", str(caught.exception))

    def test_the_refusal_can_be_overridden_on_purpose(self):
        """The documented bootstrap path still works, and still creates no tool.

        Without this, the case above is satisfied by a merge that refuses
        everything, which is not a fix.
        """
        config = {"tools": {}}
        consent = {
            "enabled": True,
            "purposes": {"analytics": {"name": "Analytics", "description": "Measure use."}},
        }
        updated = sync_consent.merge(config, consent, {}, allow_empty_tool_map=True)
        self.assertEqual(updated["tools"], {})
        self.assertTrue(updated["consent"]["enabled"])

    def test_an_empty_map_is_fine_while_consent_is_off(self):
        """The guard is about the COMBINATION, not about an empty map.

        Consent disabled with no tools is a coherent state and must not be
        refused, or staging a configuration becomes impossible.
        """
        config = {"tools": {}}
        consent = {
            "enabled": False,
            "purposes": {"analytics": {"name": "Analytics", "description": "Measure use."}},
        }
        updated = sync_consent.merge(config, consent, {})
        self.assertFalse(updated["consent"]["enabled"])

    def test_an_empty_map_is_fine_when_there_are_no_purposes(self):
        """Nothing to gate and nothing claiming to gate it."""
        config = {"tools": {}}
        consent = {"enabled": True, "purposes": {}}
        updated = sync_consent.merge(config, consent, {})
        self.assertEqual(updated["consent"]["purposes"], {})

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
