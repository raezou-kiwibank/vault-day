import unittest


class WorkspaceSmokeTest(unittest.TestCase):
    """Smoke test to verify that python -m unittest runs properly in this workspace."""

    def test_unittest_environment_operational(self):
        self.assertTrue(True, "Python unittest runner is working correctly.")


if __name__ == "__main__":
    unittest.main()
