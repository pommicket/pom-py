import io
from typing import Optional, Any, Iterable

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
	def __repr__(self) -> str:
		return f'<Item {self.key} at {self.file}:{self.line}>'

class Configuration:
	_items: dict[str, Item]
	def __repr__(self) -> str:
		result = []
		for item in self._items.values():
			result.append(f'{item.key}: {repr(item.value)}')
		return '\n'.join(result)

	def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
		item = self._items.get(key)
		if item is None:
			return default
		return item.value

	def items(self) -> Iterable[Item]:
		import copy
		return map(copy.copy, self._items.values())

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

	def _process_escape_sequence(self, chars: Iterable[str]) -> str:
		raise NotImplementedError('TODO')

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
			line = self._read_line()
			if line is None:
				self.line_number = start_line
				self._error(f'Closing {delimiter} not found.')
				return ''
			line += '\n'

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
