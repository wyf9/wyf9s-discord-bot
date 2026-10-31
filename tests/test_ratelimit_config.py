import unittest

from config import ConfigModel


class RateLimitConfigTest(unittest.TestCase):
    def parse(self, ratelimit=None, **sections):
        data = {"token": "test-token", **sections}
        if ratelimit is not None:
            data["ratelimit"] = ratelimit
        return ConfigModel.model_validate(data).ratelimit

    def test_new_config_uses_subcommand_then_command_then_module(self):
        rl = self.parse(
            {
                "enabled": True,
                "window": 60,
                "mod_multiplier": 3,
                "modules": {"emoji": 10},
                "commands": {"vc": 20, "emoji update": 5},
            }
        )

        self.assertEqual(rl.resolve("emoji", "emoji update"), 5)
        self.assertEqual(rl.resolve("emoji", "emoji info"), 10)
        self.assertEqual(rl.resolve("tools", "vc join"), 20)
        self.assertIsNone(rl.resolve("tools", "random"))

    def test_new_config_does_not_inherit_hidden_command_defaults(self):
        rl = self.parse({"modules": {"emoji": 10}})

        self.assertEqual(rl.resolve("emoji", "e"), 10)
        self.assertIsNone(rl.resolve("tools", "random"))

    def test_default_config_keeps_legacy_command_limits(self):
        rl = self.parse()

        self.assertEqual(rl.resolve("tools", "random"), 10)
        self.assertEqual(rl.resolve("emoji", "emoji info"), 10)

    def test_flat_legacy_commands_on_top_level_are_migrated(self):
        rl = self.parse({"random": 5, "uuid": 4, "2file": 3})

        self.assertEqual(rl.resolve("tools", "random"), 5)
        self.assertEqual(rl.resolve("tools", "uuid"), 4)
        self.assertEqual(rl.resolve("tools", "to-file"), 3)

    def test_new_config_accepts_legacy_command_aliases(self):
        rl = self.parse(
            {
                "commands": {
                    "emoji_info": 4,
                    "2file": 2,
                }
            }
        )

        self.assertEqual(rl.resolve("emoji", "emoji info"), 4)
        self.assertEqual(rl.resolve("tools", "to-file"), 2)

    def test_legacy_module_ratelimit_is_migrated(self):
        rl = self.parse(
            tools={
                "ratelimit": {
                    "enabled": True,
                    "window": 30,
                    "mod_multiplier": 2,
                    "random": 5,
                    "uuid": 4,
                    "2file": 3,
                }
            }
        )

        self.assertTrue(rl.enabled)
        self.assertEqual(rl.window, 30)
        self.assertEqual(rl.mod_multiplier, 2)
        self.assertEqual(rl.resolve("tools", "random"), 5)
        self.assertEqual(rl.resolve("tools", "uuid"), 4)
        self.assertEqual(rl.resolve("tools", "to-file"), 3)
        self.assertEqual(rl.resolve("emoji", "e"), 10)

    def test_legacy_disabled_module_keeps_other_module_limits(self):
        rl = self.parse(tools={"ratelimit": {"enabled": False}})

        self.assertIsNone(rl.resolve("tools", "random"))
        self.assertEqual(rl.resolve("emoji", "e"), 10)


if __name__ == "__main__":
    unittest.main()
