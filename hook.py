"""Entry point of the hooks. Imported instead of run, syn.py comes from Python's bytecode cache, so the hooks start
faster."""
import sys

import syn

sys.exit(syn.main(['hook', *sys.argv[1:]]))
