import pom_parser
import unittest

def test_path(tester: unittest.TestCase, loc_path: str) -> None:
	conf_path = loc_path.replace('.locations.pom', '.pom')
	locs = pom_parser.load_path(loc_path)
	conf = pom_parser.load_path(conf_path)
	for item in conf:
		expected = locs.get_uint(item.key)
		tester.assertTrue(expected is not None)
		tester.assertEqual(expected, item.line, f'Incorrect line number for {item.key}')
