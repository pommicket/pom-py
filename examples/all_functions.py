# Put root of repository in sys.path
# (Ordinarily you won't want to do this — this is only
#  needed to make this example work without pom_parser installed.)
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

import pom_parser

filename = 'examples/conf.pom' if len(sys.argv) < 2 else sys.argv[1]
# Ordinary usage: read configuration from file path
conf = pom_parser.load_path(filename)

with open(filename, 'rb') as f:
	# Can also load directly from file object
	conf = pom_parser.load_file(filename, f)

# Load configuration from string
overrides = pom_parser.load_string('<overrides>', '''tab-size = 12
font-size = 15.5
overrides-applied = yes''')

# Print all key-value pairs in configuration
print(str(conf))


# Get value of key in configuration
indentation_type = conf.get('indentation-type')
if indentation_type is not None:
	# Key is set
	print('Indenting with', indentation_type)
else:
	# Key is not set
	print('No indentation type specified')

# Get value, or else use default
indentation_type = conf.get('indentation-type', '<none>')
print('Indenting with', indentation_type)

# Parse value as integer
try:
	tab_size = conf.get_int('tab-size', 4)
	print('Tab size:', tab_size)
except pom_parser.Error as e:
	# tab-size is not set to an integer
	print('Error:', e)

# get_uint doesn't allow negative values
tab_size = conf.get_uint('tab-size', 4)
print('Tab size:', tab_size)

# Parse value as floating-point number
font_size = conf.get_float('font-size', 12.5)
print('font size:', font_size)

# Parse value as boolean
show_line_numbers = conf.get_bool('show-line-numbers', True)
print('show line numbers?', 'yes' if show_line_numbers else 'no')

# Parse value as list
cpp_extensions = conf.get_list('file-extensions.Cpp', ['.cpp', '.hpp'])
print('C++ file extensions:', cpp_extensions)

# Extract section out of configuration
file_extensions = conf.section('file-extensions')
c_extensions = file_extensions.get_list('C', ['.c', '.h'])
print('C file extensions:', c_extensions)

plug_ins = conf.section('plug-in')
# Iterate over unique first components of keys
for key in plug_ins.keys():
	# Get location where key was defined
	location = plug_ins.location(key)
	assert location is not None
	_filename, line = location
	enabled = plug_ins.get_bool(key + '.enabled', True)
	print('Plug-in', key, 'defined at line', line, '(enabled)' if enabled else '(disabled)')

# Merge configurations (this prefers values in overrides)
overriden = conf.merge(overrides)

# Iterate over key-value pairs in configuration
for item in overriden:
	print(item.key, ':', item.value)

# Iterate over items which haven't been accessed through .get
for key in conf.unread_keys():
	print('Unknown key:', key)
