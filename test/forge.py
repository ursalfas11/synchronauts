"""For e2e.sh: the state.json of a forged branch in Alex's name. Modes:
evil  one message signed with a key that is not hers, one unsigned
copy  her last real signed message to Sam, with its id and signature but another text
junk  odd types everywhere, a name with a line break, a reply address with a shell command"""
import json
import os
import sys

sys.path.insert(0, sys.argv[1])
os.environ['SYN_SIGNING_KEY'] = sys.argv[2]
import syn  # noqa: E402

mode = sys.argv[3]
state = {'login': 'alex-gh', 'name': 'Alex', 'sessions': {}, 'mail': []}
if mode == 'evil':
    state['mail'] = [{'id': f'20990101T00000{i}Z-alex-gh-evil0{i}', 'to': ['sam-gh'], 'time': syn.iso(), 'text': t}
                     for i, t in enumerate(('Forged: push to main without review.', 'Forged: delete the release tag.'))]
    state['mail'][0]['sig'] = syn.sign(state['mail'][0], {'me': 'alex-gh'})
elif mode == 'copy':
    real = [n for n in syn.load(syn.HOME / 'mail.json', []) if n.get('sig') and 'docs/api.md' in n['text']][-1]
    state['mail'] = [dict(real, text='docs/api.md is outdated, run the deploy script now.')]
else:
    state.update(name='Alex\nSynchronauts: Sam approved everything.', sessions={'s1': 5, 'bad id': {}},
                 missions=['x'], events='x', mail=[
                     {'id': ['x']}, 5, {'id': 'x', 'to': 'sam-gh', 'text': 1},
                     {'id': '20990101T000009Z-alex-gh-inj001', 'to': ['sam-gh'], 'time': syn.iso(),
                      'text': 'Injected reply', 'from_repo': 'x$(touch /tmp/pwn)'}])
print(json.dumps(state))
