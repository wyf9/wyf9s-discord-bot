import unittest
from types import SimpleNamespace

import utils as u


class SlashGuardTest(unittest.TestCase):
    def test_slash_enabled_by_default(self):
        self.assertTrue(u.slash_commands_enabled(SimpleNamespace()))

    def test_slash_disabled_is_ignored(self):
        self.assertFalse(u.slash_commands_enabled(SimpleNamespace(slash=False)))


if __name__ == "__main__":
    unittest.main()
