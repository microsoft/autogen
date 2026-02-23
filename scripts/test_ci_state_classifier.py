import unittest

from ci_state_classifier import classify


class ClassifierTests(unittest.TestCase):
    def test_no_checks(self):
        self.assertEqual(classify([]), "no checks")

    def test_pending(self):
        self.assertEqual(classify([{"status": "in_progress"}]), "pending")

    def test_failed(self):
        self.assertEqual(classify([{"conclusion": "failure"}]), "failed")

    def test_policy_blocked_wins(self):
        checks = [{"conclusion": "failure", "summary": "Resource not accessible by integration"}]
        self.assertEqual(classify(checks), "policy-blocked")


if __name__ == "__main__":
    unittest.main()
