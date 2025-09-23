# Put root of repository in sys.path
# (Ordinarily you won't want to do this — this is only
#  needed to make this example work without pom_parser installed.)
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

import pom_parser
try:
	filename = 'examples/conf.pom' if len(sys.argv) < 2 else sys.argv[1]
	conf = pom_parser.load_path(filename)
	print(conf.get_list('file-extensions.C',['a']))
except pom_parser.Error as e:
	print('Parse error:', str(e), sep = '\n')
