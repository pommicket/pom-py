# Put root of repository in sys.path
# (Ordinarily you won't want to do this — this is only
#  needed to make this example work without pom_parser installed.)
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

import pom_parser

filename = 'examples/conf.pom' if len(sys.argv) < 2 else sys.argv[1]
try:
	# Load configuration from file
	conf = pom_parser.load_path(filename)
except pom_parser.Error as e:
	# Handle error due to invalid configuration file
	print('Parse error:\n' + str(e))
	sys.exit(1)

# Get value of key in configuration
indentation_type = conf.get('indentation-type')
if indentation_type is not None:
	# Key is set
	print('Indenting with', indentation_type)
else:
	# Key is not set
	print('No indentation type specified')
