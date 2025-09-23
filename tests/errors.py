import pom_parser
import unittest

def test_path(tester: unittest.TestCase, path: str) -> None:
	try:
		pom_parser.load_path(path)
		tester.fail(f'Parsing configuration {path} should have failed.')
	except pom_parser.Error:
		pass
