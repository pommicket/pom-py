# Put root of repository in sys.path
# (Ordinarily you won't want to do this — this is only
#  needed to make this example work without pom_parser installed.)
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

import pom_parser
filename = 'examples/conf.pom' if len(sys.argv) < 2 else sys.argv[1]
print(pom_parser.load_path(filename))
