"""Signs one message with the key this machine has noted and checks it as a receiver would.

sign_once.py <folder of syn.py> <login>: exit 0 if the message verifies as 'ok', otherwise 1 with the verdict.
"""
import os
import sys

sys.path.insert(0, sys.argv[1])
import syn  # noqa: E402

login = sys.argv[2]
k = syn.config()
n = {'id': f"{syn.now().strftime('%Y%m%dT%H%M%SZ')}-{login}-{os.urandom(3).hex()}", 'to': ['alex-gh'], 'time': syn.iso(),
     'text': 'Signed with the key of syn key.'}
sig = syn.sign(n, k)
if not sig:
    sys.exit('sign() returned None')
n.update({'sig': sig, 'from': login})
verdict = syn.verify(n, k)
sys.exit(0 if verdict == 'ok' else f'verdict: {verdict}')
