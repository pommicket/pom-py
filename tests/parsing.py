import pom_parser
import unittest

def test_path(tester: unittest.TestCase, flat_path: str) -> None:
	conf_path = flat_path.replace('.flat.pom', '.pom')
	conf = pom_parser.load_path(conf_path)
	flat = pom_parser.load_path(flat_path)
	conf_items = {}
	for item in conf:
		tester.assertTrue(flat.has(item.key), f'{conf_path} has key {item.key} but {flat_path} does not')
		conf_items[item.key] = item
	for item in flat:
		tester.assertTrue(conf.has(item.key), f'{flat_path} has key {item.key} but {conf_path} does not')
		conf_item = conf_items[item.key]
		tester.assertEqual(conf_item.value, item.value, f'Values for key {item.key} do not match.')

