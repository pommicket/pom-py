import unittest
import os
from tests import parsing

class TestParsing(unittest.TestCase):
	def test_all(self) -> None:
		test_dir = '../tests/parsing'
		for file in os.listdir(test_dir):
			if not file.endswith('.flat.pom'): continue
			with self.subTest(file):
				parsing.test_path(self, f'{test_dir}/{file}')

if __name__ == '__main__':
	unittest.main()

