import unittest
import os
from tests import parsing, errors, location, interpretation
import sys

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

class TestLocation(unittest.TestCase):
	def test_all(self) -> None:
		test_dir = '../tests/location'
		for file in os.listdir(test_dir):
			if not file.endswith('.locations.pom'): continue
			with self.subTest(file):
				location.test_path(self, f'{test_dir}/{file}')

class TestInterpretation(unittest.TestCase):
	def test_all(self) -> None:
		test_dir = '../tests/interpretation'
		for file in os.listdir(test_dir):
			if not file.endswith('.pom'): continue
			with self.subTest(file):
				interpretation.test_path(self, f'{test_dir}/{file}')

if __name__ == '__main__':
	unittest.main()

