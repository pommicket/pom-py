import unittest
import os
from tests import parsing, errors

class TestParsing(unittest.TestCase):
	def test_all(self) -> None:
		test_dir = '../tests/parsing'
		for file in os.listdir(test_dir):
			if not file.endswith('.flat.pom'): continue
			with self.subTest(file):
				parsing.test_path(self, f'{test_dir}/{file}')

class TestErrors(unittest.TestCase):
	def test_all(self) -> None:
		test_dir = '../tests/errors'
		for file in os.listdir(test_dir):
			if not file.endswith('.pom'): continue
			with self.subTest(file):
				errors.test_path(self, f'{test_dir}/{file}')

if __name__ == '__main__':
	unittest.main()

