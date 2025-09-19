import io
from typing import Optional, Any, Iterable, Iterator

class Error(ValueError):
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
	key: str
	value: str
	file: str
	line: int
	read: bool
	def __repr__(self) -> str:
		return f'<Item {self.key} at {self.file}:{self.line}>'

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
		value = int(s)
		if value >> 53:
			return None
		return value

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

class Configuration:
	_items: dict[str, Item]
	def __repr__(self) -> str:
		result = []
		for item in self._items.values():
			result.append(f'{item.key}: {repr(item.value)}')
		return '\n'.join(result)

	def has(self, key: str) -> bool:
		return key in self._items

	def location(self, key: str) -> Optional[tuple[str, int]]:
		item = self._items.get(key)
		if item is None:
			return item
		return (item.file, item.line)

	def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
		item = self._items.get(key)
		if item is None:
			return default
		item.read = True
		return item.value

	def get_uint(self, key: str, default: Optional[int] = None) -> Optional[int]:
		item = self._items.get(key)
		if item is None:
			return default
		item.read = True
		uint = item._parse_uint()
		if uint is None:
			raise item._error(f'Value {repr(item.value)} for {item.key} is not a valid (non-negative) integer.')
		return uint

	def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
		item = self._items.get(key)
		if item is None:
			return default
		item.read = True
		intv = item._parse_int()
		if intv is None:
			raise item._error(f'Value {repr(item.value)} for {item.key} is not a valid integer.')
		return intv

	def items(self) -> Iterable[Item]:
		import copy
		return map(copy.copy, self._items.values())

	def keys(self) -> Iterable[str]:
		return iter({key.split('.', 1)[0] for key in self._items})

	def unread_keys(self) -> Iterable[str]:
		return (item.key for item in self._items.values() if not item.read)

	def section(self, name: str) -> 'Configuration':
		import copy
		section_items = {}
		name_dot = name + '.'
		for item in self.items():
			if item.key.startswith(name_dot):
				item_copy = copy.copy(item)
				section_items[item.key[len(name_dot):]] = item_copy
		conf = Configuration()
		conf._items = section_items
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
		key = f'{self.current_section}.{relative_key}' if self.current_section else relative_key
		item = Item()
		item.key = key
		item.read = False
		item.value = value
		item.file = self.filename
		item.line = self.line_number
		self.items[key] = item
		return True

def load_file(filename: str, file: io.BufferedIOBase) -> Configuration:
	parser = _Parser(filename, file)
	while parser._parse_line():
		pass
	if parser.errors:
		raise Error._from_list(parser.errors)
	conf = Configuration()
	conf._items = parser.items
	return conf

def load_string(filename: str, string: str) -> Configuration:
	return load_file(filename, io.BytesIO(string.encode()))

def load_path(path: str) -> Configuration:
	with open(path, 'rb') as file:
		return load_file(path, file)
