r'''Configuration for the [POM configuration file format](https://www.pom.computer).

\mainpage pom_parser

See \ref pom_parser.
'''
import io
from typing import Optional, Any, Iterable, Iterator

class Error(ValueError):
	r'''An error raised by pom_parser.

Attributes
----------
- `next: Optional[Error]` -
	Next error (used when there are multiple errors in a file)
- `message: str` -
	Error message as a string. Note that this does not include
	file/line information, or all errors in a list, so you most
	likely want to use str(error) instead.
- `file: str` -
	File name where error occurred.
- `line: int` -
	Line number where error occurred.
'''

	next: Optional['Error']
	message: str
	file: str
	line: int
	def __init__(self, file: str, line_number: int, message: str) -> None:
		self.file = file
		self.line_number = line_number
		self.message = message
		self.next = None

	def __str__(self) -> str:
		err: Optional['Error'] = self
		messages = []
		while err:
			messages.append(f'{err.file}:{err.line_number}: {err.message}')
			err = err.next
		return '\n'.join(messages)

	@staticmethod
	def _from_list(l: list['Error']) -> 'Error':
		for (i, e) in enumerate(l[:-1]):
			e.next = l[i+1]
		return l[0]


class Item:
	r'''
An item (key-value pair) in a POM configuration.

Attributes
----------
- `key: str` -
	The key.
- `value: str` -
	The value.
- `file: str` -
	File name where item was defined.
- `line: int` -
	Line number where item was defined.
'''
	key: str
	value: str
	file: str
	line: int
	# This is a list so we can pass it around by reference
	_read: list[bool]

	def __repr__(self) -> str:
		return f'<Item {self.key} at {self.file}:{self.line}>'

	def read(self) -> bool:
		'''Returns whether this item's value has been accessed through `Configuration.get_*`.'''
		return self._read[0]

	def _error(self, message: str) -> Error:
		return Error(self.file, self.line, message)

	def _parse_uint(self, using: Optional[str] = None) -> Optional[int]:
		s = self.value if using is None else using
		if s.startswith('+'):
			s = s[1:]
		if s.startswith('0x') or s.startswith('0X'):
			if not all(c in '0123456789abcdefABCDEF' for c in s[2:]):
				return None
			value = int(s[2:], 16)
			if value >> 53:
				return None
			return value
		if s == '0':
			return 0
		if s.startswith('0'):
			return None
		if not all(c in '0123456789' for c in s):
			return None
		if s == '':
			return None
		value = int(s)
		if value >> 53:
			return None
		return value

	def _set_read(self) -> None:
		self._read[0] = True

	def _parse_int(self) -> Optional[int]:
		sign = 1
		value = self.value
		if value.startswith('-'):
			if value.startswith('-+'):
				return None
			sign = -1
			value = value[1:]
		uint = self._parse_uint(value)
		if uint is None:
			return None
		return uint * sign

	def _parse_float(self) -> Optional[float]:
		value = self.value
		if not all(c in '0123456789eE+-.' for c in value):
			return None
		for (i, c) in enumerate(value):
			# ensure . is preceded and followed by digit
			if c == '.' and (i == 0 or i == len(value)-1 or \
				not value[i+1].isdigit() or not value[i-1].isdigit()):
				return None
		try:
			return float(value)
		except ValueError:
			return None

	def _parse_bool(self) -> Optional[bool]:
		value = self.value
		if value in ('yes', 'true', 'on'):
			return True
		if value in ('no', 'false', 'off'):
			return False
		return None

	def _parse_list(self) -> list[str]:
		chars = iter(self.value)
		list_ = []
		entry: list[str] = []
		while (c := next(chars, '')):
			if c == ',':
				list_.append(''.join(entry).strip(' \t\n'))
				entry = []
			elif c == '\\':
				c = next(chars, '')
				if c not in ',\\':
					entry.append('\\')
				entry.append(c)
			else:
				entry.append(c)
		last_entry = ''.join(entry).strip(' \t\n')
		if last_entry:
			list_.append(last_entry)
		return list_

class Configuration:
	r'''A POM configuration.'''
	_items: dict[str, Item]
	_section_locations: dict[str, tuple[str, int]]
	def __str__(self) -> str:
		result = []
		for item in self._items.values():
			result.append(f'{item.key} = {repr(item.value)}')
		return '\n'.join(result)

	def __iter__(self) -> Iterator[Item]:
		r'''Get all items (key-value pairs) in configuration.

The order of the returned items is arbitrary and may change in future versions.'''
		import copy
		return iter(map(copy.copy, self._items.values()))

	def _init(self, items: dict[str, Item]) -> None:
		self._items = items
		self._section_locations = {}
		for item in self._items.values():
			for (i, c) in enumerate(item.key):
				if c != '.':
					continue
				section = item.key[:i]
				if section not in self._section_locations \
					or self._section_locations[section][1] > item.line:
					self._section_locations[section] = (item.file, item.line)

	def has(self, key: str) -> bool:
		r'''Returns whether this configuration contains `key`.'''
		return key in self._items

	def location(self, key: str) -> Optional[tuple[str, int]]:
		r'''Returns the location of `key` as `(filename, line_number)`, or `None` if it's not defined.'''
		item = self._items.get(key)
		if item is None:
			return self._section_locations.get(key, None)
		return (item.file, item.line)

	def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
		r'''Get value associated with `key`.

\param key Key to look up
\param default Default to use when `key` is not defined
		'''
		item = self._items.get(key)
		if item is None:
			return default
		item._set_read()
		return item.value

	def get_uint(self, key: str, default: Optional[int] = None) -> Optional[int]:
		r'''Get value associated with `key`, and parse as an unsigned integer.

\param key Key to look up
\param default Default to use when `key` is not defined

\exception pom_parser.Error The key is defined, but its value is
not a valid unsigned integer (< 2^53).
		'''
		item = self._items.get(key)
		if item is None:
			return None if default is None else int(default)
		item._set_read()
		uint = item._parse_uint()
		if uint is None:
			raise item._error(f'Value {repr(item.value)} for {item.key} is '
				'not a valid (non-negative) integer.')
		return uint

	def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
		r'''Get value associated with `key`, and parse as an integer.

\param key Key to look up
\param default Default to use when `key` is not defined

\exception pom_parser.Error The key is defined, but
its value is not a valid integer (with absolute value < 2^53).
		'''
		item = self._items.get(key)
		if item is None:
			return None if default is None else int(default)
		item._set_read()
		intv = item._parse_int()
		if intv is None:
			raise item._error(f'Value {repr(item.value)} for {item.key} is not a valid integer.')
		return intv

	def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
		r'''Get value associated with `key`, and parse as a floating-point number.

\param key Key to look up
\param default Default to use when `key` is not defined

\exception pom_parser.Error The key is defined, but its value is not a valid floating-point number.
		'''
		item = self._items.get(key)
		if item is None:
			return None if default is None else float(default)
		item._set_read()
		intv = item._parse_float()
		if intv is None:
			raise item._error(f'Value {repr(item.value)} for {item.key} is not a valid number.')
		return intv

	def get_bool(self, key: str, default: Optional[bool] = None) -> Optional[bool]:
		r'''Get value associated with `key`, and parse as a boolean (yes/no/on/off/true/false).

\param key Key to look up
\param default Default to use when `key` is not defined

\exception pom_parser.Error The key is defined, but its value is not one of the six mentioned above.
		'''
		item = self._items.get(key)
		if item is None:
			return None if default is None else bool(default)
		item._set_read()
		boolv = item._parse_bool()
		if boolv is None:
			raise item._error(f'Value {repr(item.value)} for {item.key} is '
				'invalid (want on/off/yes/no/true/false)')
		return boolv

	def get_list(self, key: str, default: Optional[list[str]] = None) -> Optional[list[str]]:
		r'''Get value associated with `key`, and parse as a comma-separated list.

Literal commas can be included in the list by using `\,`.

\param key Key to look up
\param default Default to use when `key` is not defined
		'''
		item = self._items.get(key)
		if item is None:
			return None if default is None else default
		item._set_read()
		return item._parse_list()


	def keys(self) -> Iterator[str]:
		r'''Get all "direct" keys (unique first components of keys) in configuration.

The order of the returned keys is arbitrary and may change in future versions.'''
		return iter({key.split('.', 1)[0] for key in self._items})

	def unread_keys(self) -> Iterator[str]:
		r'''Get all keys which have not been accessed using a `get_*` method.

The order of the returned keys is arbitrary and may change in future versions.'''
		return (item.key for item in self._items.values() if not item.read())

	def section(self, name: str) -> 'Configuration':
		r'''Extract a "section" out of a configuration.

Specifically, this will return a configuration consisting of all keys starting
with `name.` (with the `name.` stripped out) and their values.
'''
		import copy
		section_items = {}
		name_dot = name + '.'
		for item in self:
			if item.key.startswith(name_dot):
				item_copy = copy.copy(item)
				new_key = item.key[len(name_dot):]
				item_copy.key = new_key
				section_items[new_key] = item_copy
		conf = Configuration()
		conf._init(section_items)
		return conf

	def merge(self, other: 'Configuration') -> 'Configuration':
		'''Merge `other` configuration into `self`, preferring values in `other`.'''
		import copy
		new_items = {key: copy.copy(item) for key, item in other._items.items()}
		for key, item in self._items.items():
			if key not in new_items:
				new_items[key] = copy.copy(item)
		conf = Configuration()
		conf._init(new_items)
		return conf


def _parse_hex_digit(d: Optional[str]) -> Optional[int]:
	if d in list('0123456789'):
		return ord(d) - ord('0')
	if d in list('abcdef'):
		return ord(d) - ord('a') + 10
	if d in list('ABCDEF'):
		return ord(d) - ord('A') + 10
	return None

class _Parser:
	line_number: int
	filename: str
	current_section: str
	errors: list[Error]
	file: io.BufferedIOBase
	items: dict[str, Item]

	def __init__(self, filename: str, file: io.BufferedIOBase):
		self.errors = []
		self.filename = filename
		self.file = file
		self.line_number = 0
		self.current_section = ''
		self.items = {}

	def _error(self, message: str) -> None:
		self.errors.append(Error(self.filename, self.line_number, message))

	def _check_key(self, key: str) -> None:
		if not key:
			self._error('Empty key (expected something before =)')
			return
		if '..' in key:
			self._error(f"Key {key} shouldn't contain ..")
			return
		if key.startswith('.'):
			self._error(f"Key {key} shouldn't start with .")
			return
		if key.endswith('.'):
			self._error(f"Key {key} shouldn't end with .")
			return
		for c in key:
			o = ord(c)
			if (0xf800000178000001fc001bffffffffff >> o) & 1:
				self._error(f"Key {key} contains illegal character {c}")

	def _process_escape_sequence(self, chars: Iterator[str]) -> str:
		def bad_escape_sequence(chs: Iterable[Optional[str]]) -> str:
			seq = ''.join(c for c in chs if c)
			self._error(f'Invalid escape sequence: \\{seq}')
			return ''
		c = next(chars, None)
		simple_sequences: dict[str | None, str] = {
			'n': '\n', 't': '\t', 'r': '\r',
			'\'': '\'', '"': '"', '`': '`',
			',': '\\,', '\\': '\\'
		}
		simple = simple_sequences.get(c)
		if simple is not None:
			return simple
		if c == 'x':
			c1 = next(chars, None)
			c2 = next(chars, None)
			dig1 = _parse_hex_digit(c1)
			dig2 = _parse_hex_digit(c2)
			if dig1 is None or dig2 is None:
				return bad_escape_sequence((c, c1, c2))
			value = dig1 << 4 | dig2
			if value == 0 or value >= 0x80:
				return bad_escape_sequence((c, c1, c2))
			return chr(value)
		if c == 'u':
			open_brace = next(chars, None)
			if open_brace != '{':
				return bad_escape_sequence((c, open_brace))
			sequence: list[str | None] = ['u{']
			value = 0
			for i in range(7):
				c = next(chars, None)
				sequence.append(c)
				if c == '}':
					break
				if i == 6:
					return bad_escape_sequence(sequence)
				digit = _parse_hex_digit(c)
				if digit is None:
					return bad_escape_sequence(sequence)
				value <<= 4
				value |= digit
			if value == 0 or \
				0xD800 <= value <= 0xDFFF or \
				value > 0x10FFFF:
				return bad_escape_sequence(sequence)
			return chr(value)
		bad_escape_sequence((c,))
		return ''

	def _read_line(self) -> Optional[str]:
		line_bytes = self.file.readline()
		if not line_bytes:
			return None
		self.line_number += 1
		try:
			line = line_bytes.decode()
		except UnicodeDecodeError:
			self._error('Bad UTF-8')
			return ''
		if self.line_number == 1 and line.startswith('\ufeff'):
			# skip byte order mark
			line = line[1:]
		if line.endswith('\r\n'):
			line = line[:-2]
		elif line.endswith('\n'):
			line = line[:-1]
		for c in line:
			if ord(c) < 32 and c != '\t':
				self._error(f'Invalid character in file: ASCII control character {ord(c)}')
				return ''
		return line

	def _parse_quoted_value(self, value_start: str) -> str:
		delimiter = value_start[0]
		start_line = self.line_number
		line = value_start[1:] + '\n'
		value = []
		while True:
			chars = iter(line)
			while (c := next(chars, None)) is not None:
				if c == '\\':
					value.append(self._process_escape_sequence(chars))
				elif c == delimiter:
					for stray in chars:
						if stray not in ' \t\n':
							self._error(f'Stray {stray} after string.')
					return ''.join(value)
				else:
					value.append(c)
			next_line = self._read_line()
			if next_line is None:
				self.line_number = start_line
				self._error(f'Closing {delimiter} not found.')
				return ''
			line = next_line + '\n'

	def _parse_line(self) -> bool:
		line = self._read_line()
		if line is None:
			return False
		start_line_number = self.line_number
		line = line.lstrip(' \t')
		if not line or line.startswith('#'):
			return True
		if line.startswith('['):
			line = line.rstrip(' \t')
			if not line.endswith(']'):
				self._error('[ with no matching ]')
				return True
			self.current_section = line[1:-1]
			if self.current_section:
				self._check_key(self.current_section)
			return True
		equals_idx = line.find('=')
		if equals_idx == -1:
			self._error('Invalid line — should either start with [ or contain =')
			return True
		relative_key = line[:equals_idx].rstrip(' \t')
		self._check_key(relative_key)
		value = line[equals_idx+1:].lstrip(' \t')
		if value.startswith('"') or value.startswith('`'):
			value = self._parse_quoted_value(value)
		else:
			value = value.rstrip(' \t')
		key = f'{self.current_section}.{relative_key}' if self.current_section else relative_key
		item = Item()
		item.key = key
		item._read = [False]
		item.value = value
		item.file = self.filename
		item.line = start_line_number
		if prev_item := self.items.get(key):
			self._error(f'Re-definition of {key} (first definition was on line {prev_item.line})')
		self.items[key] = item
		return True

def load_file(filename: str, file: io.BufferedIOBase) -> Configuration:
	r'''Load a configuration from a file object.

\param filename File name to use for errors.
\param file File object, such as one returned from `open`.

\exception pom_parser.Error The configuration is invalid in some way.'''
	parser = _Parser(filename, file)
	while parser._parse_line():
		pass
	if parser.errors:
		raise Error._from_list(parser.errors)
	conf = Configuration()
	conf._init(parser.items)
	return conf

def load_string(filename: str, string: str) -> Configuration:
	r'''Load a configuration from a string.

\param filename File name to use for errors.
\param string String containing configuration.

\exception pom_parser.Error The configuration is invalid in some way.'''
	return load_file(filename, io.BytesIO(string.encode()))

def load_path(path: str) -> Configuration:
	r'''Load a configuration from a file path.

\exception pom_parser.Error The configuration is invalid in some way.'''
	with open(path, 'rb') as file:
		return load_file(path, file)
