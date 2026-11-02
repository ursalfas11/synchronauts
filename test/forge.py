"""For e2e.sh: the state.json of a forged branch in Alex's name, one message signed with a key that is not hers,
one unsigned."""
import json
import os
import sys

sys.path.insert(0, sys.argv[1])
os.environ['SYN_SIGNING_KEY'] = sys.argv[2]
import syn  # noqa: E402

mail = [{'id': f'20990101T00000{i}Z-alex-gh-evil0{i}', 'to': ['sam-gh'], 'time': syn.iso(), 'text': t}
        for i, t in enumerate(('Forged: push to main without review.', 'Forged: delete the release tag.'))]
mail[0]['sig'] = syn.sign(mail[0], {'me': 'alex-gh'})
print(json.dumps({'login': 'alex-gh', 'name': 'Alex', 'sessions': {}, 'mail': mail}))
