import pom_parser
import unittest

def test_list(tester: unittest.TestCase, path: str) -> None:
	conf = pom_parser.load_path(path)
	for key in conf.keys():
		section = conf.section(key)
		sep = section.get('sep')
		list_ = section.get_list('list')
		assert sep is not None
		sep_list = sep.split(';')
		sep_list.pop()
		tester.assertEqual(sep_list, list_, f'List values for {key} disagree.')

def test_path(tester: unittest.TestCase, path: str) -> None:
	if 'list' in path:
		test_list(tester, path)
		return
	conf = pom_parser.load_path(path)
	getters = [
		('uint', pom_parser.Configuration.get_uint),
		('int', pom_parser.Configuration.get_int),
		('float', pom_parser.Configuration.get_float),
		('bool', pom_parser.Configuration.get_bool),
	]
	(name, getter) = next((name, g) for (name, g) in getters if path.endswith(f'{name}.pom'))
	good = conf.section('good')
	bad = conf.section('bad')
	for key in good.keys():
		section = good.section(key)
		value_a = getter(section, 'a')
		value_b = getter(section, 'b')
		tester.assertEqual(value_a, value_b, f'Values for {key} disagree.')
	for key in bad.keys():
		try:
			getter(bad, key)
			tester.fail(f'Parsing {key} as a {name} should have failed.')
		except pom_parser.Error:
			pass
