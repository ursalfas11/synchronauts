"""Entry point of the hooks. Imported instead of run, syn.py comes from Python's bytecode cache, so the hooks start
faster. A Python older than 3.9 cannot run syn.py: the session start says so, the other hooks stay quiet."""
import sys

if sys.version_info < (3, 9):
    if sys.argv[1:2] == ['SessionStart']:
        sys.stdout.write('{"systemMessage": "Synchronauts is off: it needs Python 3.9 or newer, this is Python %d.%d."}\n'
                         % tuple(sys.version_info[:2]))
    sys.exit(0)

import syn  # noqa: E402

sys.exit(syn.main(['hook', *sys.argv[1:]]))
