import unittest
import flaml


class TestVersion(unittest.TestCase):

    def test_version(self):
        self.assertTrue(hasattr(flaml, '__version__'))
        self.assertTrue(len(flaml.__version__) > 0)


if __name__ == "__main__":
    unittest.main()
