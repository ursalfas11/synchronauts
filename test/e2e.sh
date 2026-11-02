#!/usr/bin/env bash
# Two people (sam, alex) with several sessions and a second machine of Sam's, all on this machine.
# A local bare repo stands in for GitHub, the watchers poll at a fast tick. Runs on macOS, Linux and Windows (Git Bash).
set -euo pipefail
WIN=; [ "${OS-}" = Windows_NT ] && WIN=1
PY=python3; [ -n "$WIN" ] && PY=python  # as in hooks.json
ROOT="$(cd "$(dirname "$0")/.." && { [ -n "$WIN" ] && pwd -W || pwd -P; })"  # on Windows C:/..., which Python understands
SYN="$ROOT/syn.py" HOOK="$ROOT/hook.py"
T="$(mktemp -d)"; [ -n "$WIN" ] && T="$(cygpath -m "$T")"
stop() { if [ -n "$WIN" ]; then taskkill //F //PID "$1" >/dev/null 2>&1; else kill "$1" 2>/dev/null; fi; }
cleanup() {
  local rc=$?
  set +e  # processes that already ended must not abort the cleanup
  [ $rc = 0 ] || for f in "$T"/home-*/*.log; do echo "---- $f"; tail -15 "$f"; done
  for h in "$T"/home-*; do
    for d in watcher ui; do
      pid=$("$PY" -c 'import json,sys; sys.stdout.write(str(json.load(open(sys.argv[1]))["pid"]))' "$h/$d.json" 2>/dev/null) && stop "$pid"
    done
  done
  kill $(jobs -p) 2>/dev/null
  [ -n "${KEEP-}" ] && echo "test dir: $T" || rm -rf "$T"
  exit $rc
}
trap cleanup EXIT
unset CLAUDE_PID CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION_ID
export SYN_REMOTE="$T/remote.git" SYN_ORGS=acme SYN_TICK=0.3 SYN_IDLE=120 SYN_CONFLICT_TICK=1
# acme/conf on "GitHub" is a local bare repo, for the conflict check against a teammate's pushed work
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.$T/conf.git.insteadOf" GIT_CONFIG_VALUE_0=https://github.com/acme/conf.git
export SYN_UI_PORT=0  # a free port, a real UI that is running stays untouched
git init -q --bare "$T/remote.git"

# Working copies: demo for both, other only for Alex, plus a private repo of another owner
repo() { git init -q -b main "$T/$1" && git -C "$T/$1" remote add origin "https://github.com/$2.git"
  mkdir -p "$T/$1/src" && echo x > "$T/$1/src/a.ts" && git -C "$T/$1" -c core.autocrlf=false add -A \
  && git -C "$T/$1" -c user.name=test -c user.email=test@example.com commit -q -m init; }
repo sam-demo acme/demo; repo alex-demo acme/demo; repo alex-other acme/other
repo private someone/private

as_user() { local who=$1 name=Sam machine=one; shift; [ "$who" = alex ] && name=Alex; [ "$who" = sam2 ] && machine=two
  SYN_HOME="$T/home-$who" SYN_ME="${who%2}-gh" SYN_NAME="$name" SYN_MACHINE="$machine" "$@"; }
from_session() { local sid=$1; shift; CLAUDE_CODE_SESSION_ID="$sid-0000-0000" "$@"; }  # command run from this session
hook() { echo "$3" | as_user "$1" "$PY" "$HOOK" "$2"; }
session() { echo "{\"session_id\":\"$1\",\"cwd\":\"$2\",\"source\":\"startup\"}"; }
edit() { echo "{\"session_id\":\"$1\",\"cwd\":\"$2\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$3\"}}"; }
bash_call() { echo "{\"session_id\":\"$1\",\"cwd\":\"$2\",\"tool_name\":\"Bash\",\"tool_input\":{}}"; }
task_of() { "$PY" -c 'import json,sys; sys.stdout.write(str(json.load(open(sys.argv[1]))["sessions"][sys.argv[2]].get("task")))' "$T/home-$1/status.json" "$2"; }
ok() { echo "ok   $1"; }
fail() { echo "FAIL $1"; [ -n "${2-}" ] && echo "---- output:" && echo "$2"; exit 1; }
check() { grep -q -- "$2" <<<"$1" && ok "$3" || fail "$3" "$1"; }
lacks() { grep -q -- "$2" <<<"$1" && fail "$3" "$1" || ok "$3"; }
until_ok() { local limit=$1 what=$2; shift 2; local end=$((SECONDS + limit))
  until "$@" >/dev/null 2>&1; do [ $SECONDS -lt $end ] || fail "$what"; sleep 0.2; done; ok "$what"; }
no_session() { "$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(any(sys.argv[2] in json.dumps(x.get("sessions")) for x in d.values()))' "$2" "$1"; }
state_of() { "$PY" -c 'import json,sys; sys.stdout.write(str(json.load(open(sys.argv[1]))["sessions"][sys.argv[2]].get("state")))' "$T/home-$1/status.json" "$2"; }
state_is() { [ "$(state_of "$1" "$2")" = "$3" ]; }
notify() { echo "{\"session_id\":\"$2\",\"cwd\":\"$T/alex-demo\",\"notification_type\":\"$3\",\"message\":\"Claude needs your permission\"}" | as_user "$1" "$PY" "$HOOK" Notification; }
exit_of() { local i; for i in $(seq 1 $(($2 * 5))); do kill -0 "$1" 2>/dev/null || { wait "$1"; return $?; }; sleep 0.2; done; return 124; }

out=$("$PY" - "$SYN" <<'EOF'
import json, re, sys
from pathlib import Path
root = Path(sys.argv[1]).parent
plugin = json.loads((root / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
market = json.loads((root / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
versions = {re.search(r"^VERSION = '(.+)'", (root / 'syn.py').read_text(encoding='utf-8'), re.M).group(1),
            plugin['version'],
            *(p['version'] for p in market['plugins'])}
print(', '.join(sorted(versions)))
sys.exit(len(versions) != 1)
EOF
) && ok "one version in script, plugin and marketplace ($out)" || fail 'the versions differ' "$out"

out=$(SYN_REMOTE= SYN_HOME="$T/home-new" SYN_ME=new-gh SYN_MACHINE=one "$PY" "$SYN" setup 2>&1) && fail 'setup without a room' "$out" \
  || check "$out" 'Setup failed: no room yet' 'setup without a room explains itself'
# A room that cannot be joined: the session start says so once a day, not in every session
out=$(echo '{"session_id":"new11111","cwd":"/"}' | SYN_REMOTE="$T/missing.git" SYN_HOME="$T/home-new" "$PY" "$HOOK" SessionStart)
check "$out" 'Synchronauts cannot join the room' 'a room that cannot be joined shows a hint'
out=$(echo '{"session_id":"new22222","cwd":"/"}' | SYN_REMOTE="$T/missing.git" SYN_HOME="$T/home-new" "$PY" "$HOOK" SessionStart)
[ -z "$out" ] && ok 'the hint comes once a day, not in every session' || fail 'setup hint repeated' "$out"

# Without a room: the own sessions and worktrees see each other on this machine, without GitHub, without a watcher
solo() { echo "$2" | SYN_REMOTE= SYN_ME= SYN_NAME= SYN_MACHINE= SYN_HOME="$T/home-solo" "$PY" "$HOOK" "$1"; }
git -C "$T/sam-demo" worktree add -q -b feature "$T/sam-demo-wt"
git init -q -b main "$T/plain" && git -C "$T/plain" -c user.name=test -c user.email=test@example.com commit -q --allow-empty -m init
out=$(solo SessionStart '{"session_id":"solo0000","cwd":"/"}')
[ -z "$out" ] && ok 'without a room, a session start outside Git repos stays silent' || fail 'solo start' "$out"
solo PostToolUse "$(edit solo1111 "$T/sam-demo" "$T/sam-demo/src/a.ts")" >/dev/null
out=$(solo SessionStart "$(session solo2222 "$T/sam-demo-wt")")
check "$out" 'what your other sessions on this machine are working on' 'without a room, the other own sessions are in the picture'
check "$out" '- Your other session: demo@main' 'a session in another worktree sees the first one'
lacks "$out" 'send <name' 'without a room there is no send in the usage'
out=$(solo PostToolUse "$(edit solo2222 "$T/sam-demo-wt" "$T/sam-demo-wt/src/a.ts")")
check "$out" '⚠️ Your other session is editing the same files in demo' 'the same file in two worktrees is reported'
solo PostToolUse "$(edit solo3333 "$T/plain" "$T/plain/notes.md")" >/dev/null
check "$(cat "$T/home-solo/status.json")" '"local/plain"' 'a repo without a GitHub remote counts too'
[ ! -e "$T/home-solo/watcher.json" ] && [ ! -e "$T/home-solo/git" ] && ok 'without a room no watcher starts and nothing syncs' || fail 'solo watcher'
SECONDS_BEFORE=$SECONDS; solo Stop "$(session solo1111 "$T/sam-demo")" >/dev/null 2>&1
[ $((SECONDS - SECONDS_BEFORE)) -lt 5 ] && ok 'without a room the Stop hook does not wait for mail' || fail 'solo Stop waits'
check "$(SYN_REMOTE= SYN_ME= SYN_NAME= SYN_MACHINE= SYN_HOME="$T/home-solo" "$PY" "$SYN" status)" 'My sessions on this machine' 'status works without a room'

# Two worktrees change the same line: the check merges both working trees and reports a real conflict
printf 'main\n' > "$T/sam-demo/src/a.ts"; printf 'feature\n' > "$T/sam-demo-wt/src/a.ts"
solo_conflict() { out=$(solo PostToolUse "$(edit solo2222 "$T/sam-demo-wt" "$T/sam-demo-wt/src/a.ts")"); grep -q 'would conflict' <<<"$out"; }
until_ok 20 'two worktrees that would conflict are reported' solo_conflict
check "$out" "Merging your other session (demo@main) with this session's work would conflict in: src/a.ts" 'the note names the session, branch and file'
check "$out" 'systemMessage' 'and the human sees it too'
[ -z "$(git -C "$T/sam-demo" diff --cached --name-only)" ] && [ -z "$(git -C "$T/sam-demo" stash list)" ] \
  && ok 'the check leaves index and stash alone' || fail 'the check touched the repo' "$(git -C "$T/sam-demo" status)"
git -C "$T/sam-demo" checkout -q -- src/a.ts; git -C "$T/sam-demo-wt" checkout -q -- src/a.ts
out=$(SYN_REMOTE= SYN_HOME="$T/home-solo" "$PY" "$SYN" send alex hello 2>&1) && fail 'send without a room' "$out" \
  || check "$out" 'needs a room' 'send without a room explains itself'

# Joining with an open invitation: setup accepts it, nobody has to click it on GitHub first. gh and GitHub are
# faked; Windows starts no shell script as gh, so this runs on macOS and Linux only
if [ -z "$WIN" ]; then
  mkdir "$T/bin"
  cat > "$T/bin/gh" <<EOF
#!/bin/sh
case "\$*" in
  'api user/repository_invitations') echo '[{"id": 7, "repository": {"full_name": "Acme/Room"}}]' ;;
  'api -X PATCH user/repository_invitations/7') git init -q --bare "$T/room.git" ;;
  *) exit 1 ;;
esac
EOF
  chmod +x "$T/bin/gh"
  out=$(PATH="$T/bin:$PATH" GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.$T/room.git.insteadOf" \
    GIT_CONFIG_VALUE_0=https://github.com/acme/room.git SYN_REMOTE= SYN_HOME="$T/home-kim" SYN_ME=kim-gh SYN_NAME=Kim \
    SYN_MACHINE=one "$PY" "$SYN" setup acme/room 2>&1) || fail 'setup with an open invitation' "$out"
  check "$out" 'Accepted the invitation to acme/room' 'setup accepts an open invitation to the room'
  check "$(git -C "$T/room.git" for-each-ref refs/heads/syn/)" 'syn/kim-gh/one' 'and then joins the room'
fi

as_user sam "$PY" "$SYN" setup >/dev/null
as_user alex "$PY" "$SYN" setup >/dev/null
check "$(git -C "$T/remote.git" for-each-ref --format='%(refname)' refs/heads/syn/)" 'syn/alex-gh/one' 'one branch per person and machine'

# Alex works in two sessions. Each sets its own task, even while the other one runs commands at the same time
hook alex SessionStart "$(session ale11111 "$T/alex-demo")" >/dev/null
hook alex PostToolUse "$(edit ale11111 "$T/alex-demo" "$T/alex-demo/src/a.ts")" >/dev/null
hook alex SessionStart "$(session ale22222 "$T/alex-other")" >/dev/null
from_session ale11111 as_user alex "$PY" "$SYN" task "Build tickets API" >/dev/null
from_session ale22222 as_user alex "$PY" "$SYN" task "Other construction site" >/dev/null
hook alex PostToolUse "$(bash_call ale22222 "$T/alex-other")" >/dev/null
hook alex PostToolUse "$(bash_call ale11111 "$T/alex-demo")" >/dev/null
[ "$(task_of alex ale11111) | $(task_of alex ale22222)" = 'Build tickets API | Other construction site' ] \
  && ok 'each session gets its own task' || fail 'tasks mixed up' "$(cat "$T/home-alex/status.json")"
hook alex SessionEnd "$(session ale22222 "$T/alex-other")" >/dev/null

# Sam edits a private repo on the side: it must not show up in the picture
hook sam PostToolUse "$(edit sam22222 "$T/private" "$T/private/src/a.ts")" >/dev/null
until_ok 10 "the watchers bring Alex's task to Sam" grep -q 'Build tickets API' "$T/home-sam/others.json"

# Outside the team repos the plugin costs no context until the session touches a team repo
out=$(hook sam SessionStart "$(session sam66666 "$T/private")")
[ -z "$out" ] && ok 'outside the team repos the session start stays silent' || fail 'session start outside the team repos' "$out"
out=$(hook sam PostToolUse "$(edit sam66666 "$T/private" "$T/sam-demo/src/c.ts")")
check "$out" 'Build tickets API' 'the first team repo brings the picture'
out=$(hook sam UserPromptSubmit "{\"session_id\":\"sam77777\",\"cwd\":\"$T/private\",\"prompt\":\"Continue in demo\"}")
check "$out" 'Build tickets API' 'a prompt that names a team repo brings the picture at once'

# Sam starts in the same repo: sees Alex and the task
out=$(hook sam SessionStart "$(session sam33333 "$T/sam-demo")")
check "$out" '- Alex: demo@main' "the session start shows Alex's session"
check "$out" 'Build tickets API' "the session start shows Alex's task"
check "$out" '⚠️ Alex is on the same branch main in demo' 'the same branch is reported'
check "$out" 'main in demo (last .*): src/a.ts' "the overlap names Alex's files there"
check "$out" 'send <name|all>' 'usage is included'

# Before Sam's first edit of a file Alex is editing, Claude Code asks Sam. The reason is for Sam, Claude gets no text
out=$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
check "$out" '"permissionDecision": "ask"' "before the first edit of Alex's file, Sam is asked"
check "$out" 'Alex is also editing src/a.ts (demo@main, last .* · \\"Build tickets API\\")' 'the question says who, where and on what'
lacks "$out" 'additionalContext' 'the question costs Claude no tokens'
check "$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.ts")")" '"ask"' 'after a no, the next attempt asks again'
out=$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/new.ts")")
[ -z "$out" ] && ok 'a file nobody else is editing needs no question' || fail 'question without an overlap' "$out"

# Sam allows it: Claude learns about the overlap without stopping again, and Sam is not warned a second time
out=$(hook sam PostToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
check "$out" 'Alex is editing the same files in demo (branch main): src/a.ts. Sam knows and allowed the edit' 'Claude learns that Sam allowed it'
lacks "$out" 'systemMessage' 'Sam is not warned twice'
check "$out" 'no task set yet' 'reminder to set a task'
out=$(hook sam PostToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
lacks "$out" 'the same files' 'the note comes only once'
out=$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
[ -z "$out" ] && ok 'once edited, the file needs no question' || fail 'asked again after the edit' "$out"

# A second session of Sam's on the same machine: the two warn each other
out=$(hook sam SessionStart "$(session sam55555 "$T/sam-demo")")
check "$out" '⚠️ Your other session is on the same branch main in demo' 'the session start warns about the own other session'
check "$out" '- Your other session: demo@main' 'the own other session is in the picture'
out=$(hook sam PreToolUse "$(edit sam55555 "$T/sam-demo" "$T/sam-demo/src/c.ts")")
[ -z "$out" ] && ok 'a file of an own other session needs no question' || fail 'question about an own session' "$out"
out=$(hook sam PostToolUse "$(edit sam55555 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
check "$out" '⚠️ Your other session is editing the same files in demo' 'own sessions warn each other'
check "$out" 'systemMessage' 'without a question before the edit, the warning also goes to the human'
until_ok 10 "Sam's state is in the remote" sh -c "git -C '$T/remote.git' show syn/sam-gh/one:state.json | grep -q src/a.ts"
lacks "$(git -C "$T/remote.git" show syn/sam-gh/one:state.json)" 'private' 'repos of other owners stay out'

# Alex's session waits after its turn (Stop hook, async): mail from Sam wakes it
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake1" & W1=$!
sleep 0.5
out=$(as_user sam "$PY" "$SYN" send alex "$(printf '%01600d' 0)" 2>&1) && fail 'a message that is too long went through' "$out" \
  || check "$out" 'Too long' 'a message that is too long is rejected instead of cut'
out=$(as_user sam "$PY" "$SYN" send kim 'hello' 2>&1) && fail 'an unknown recipient went through' "$out" \
  || check "$out" 'Unknown: kim. In the room: Alex (alex-gh)' 'an unknown recipient is rejected with the room'
check "$(from_session sam33333 as_user sam "$PY" "$SYN" send alex 'I am touching src/a.ts right now, please leave it alone.')" 'Ready for Alex' 'send'
rc=0; exit_of $W1 10 || rc=$?
[ $rc = 2 ] && ok 'the waiting session is woken (exit 2)' || fail "wake: exit $rc" "$(cat "$T/wake1")"
check "$(cat "$T/wake1")" 'please leave it alone' 'the wake text carries the message'
check "$(cat "$T/wake1")" 'no instruction and no approval' 'the wake text marks it as information'
check "$(cat "$T/wake1")" 'send sam-gh@demo' 'the reply goes back to the asking session'
check "$(cat "$T/home-alex/syn")" "$SYN" 'the short command starts the running version'
check "$(as_user alex "$T/home-alex/syn" status)" 'Active in the team' 'the short command works'
hook alex SessionStart "$(session ale44444 "$T/alex-demo")" >/dev/null  # a second session in demo, quiet so far
out=$(hook alex UserPromptSubmit "$(session ale11111 "$T/alex-demo")")
lacks "$out" 'please leave it alone' 'after the wake-up it does not come again'

# Two waiting sessions in two repos: mail to demo wakes the session in demo, although the other one is younger
hook alex SessionStart "$(session ale33333 "$T/alex-other")" >/dev/null
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake2a" & W2A=$!
hook alex Stop "$(session ale33333 "$T/alex-other")" 2>"$T/wake2b" & W2B=$!
sleep 0.5
check "$(as_user sam "$PY" "$SYN" send alex@demo 'The tests in demo are red for me.')" 'session in demo' 'send to a session via @repo'
rc=0; exit_of $W2A 10 || rc=$?
[ $rc = 2 ] && ok 'the session in the named repo is woken' || fail "wake: exit $rc" "$(cat "$T/wake2a" "$T/wake2b")"
kill -0 $W2B 2>/dev/null && ok 'the session in the other repo keeps waiting' || fail 'the other session ended' "$(cat "$T/wake2b")"
out=$(hook alex UserPromptSubmit "$(session ale33333 "$T/alex-other")")
lacks "$out" 'tests in demo' 'mail to demo does not show in the session in other'
rc=0; exit_of $W2B 5 || rc=$?
[ $rc = 0 ] && ok 'its Stop hook ends quietly once it works again' || fail "Stop hook: exit $rc"
out=$(hook alex UserPromptSubmit "$(session ale44444 "$T/alex-demo")")
check "$out" 'FYI' 'the second session in demo gets it as FYI'
lacks "$out" '📨 Sam:' 'Alex does not see it again there'
check "$(as_user sam "$PY" "$SYN" send alex@nowhere 'Anyone in nowhere?')" 'Alex: no session in nowhere right now' \
  'mail to a repo without a session says who gets it instead'

# Without a repo the most recently active session shows the mail, no other one. If it is working, none is woken
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake3" & W3=$!
sleep 0.5
as_user sam "$PY" "$SYN" send alex 'Quick question: who builds the tests?' >/dev/null
sleep 3
kill -0 $W3 2>/dev/null && ok 'while the most recently active session works, no other one is woken' || fail 'wrong session woken' "$(cat "$T/wake3")"
out=$(hook alex PostToolUse "$(bash_call ale44444 "$T/alex-demo")")
check "$out" 'who builds the tests' 'the working session shows it at its next step'
check "$out" '📨 Sam:' 'Alex sees it in the terminal'
out=$(hook alex UserPromptSubmit "$(session ale11111 "$T/alex-demo")")
check "$out" 'FYI' 'the other session only gets it as FYI'
rc=0; exit_of $W3 5 || rc=$?
[ $rc = 0 ] && ok 'its Stop hook ends quietly' || fail "Stop hook: exit $rc"

# After the wake window the Stop hook ends quietly, since waking would have to read all the context again
(export SYN_WAKE_MIN=0.02; hook alex Stop "$(session ale11111 "$T/alex-demo")") 2>"$T/wake4" & W4=$!
rc=0; exit_of $W4 10 || rc=$?
[ $rc = 0 ] && ok 'after the wake window the Stop hook ends quietly' || fail "Stop hook: exit $rc" "$(cat "$T/wake4")"

# A second machine of Sam's gets its own branch and does not overwrite the first one
as_user sam2 "$PY" "$SYN" setup >/dev/null
hook sam2 SessionStart "$(session sam44444 "$T/sam-demo")" >/dev/null
hook sam2 PostToolUse "$(edit sam44444 "$T/sam-demo" "$T/sam-demo/src/b.ts")" >/dev/null
until_ok 10 'Sam sees the second machine' grep -q 'src/b.ts' "$T/home-sam/others.json"
check "$(git -C "$T/remote.git" show syn/sam-gh/one:state.json)" 'src/a.ts' 'the first machine stays untouched'
out=$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/b.ts")")
[ -z "$out" ] && ok 'a file of an own session on another machine needs no question' || fail 'question about the own other machine' "$out"

# Claims: Alex claims a file and a folder before starting. Every other session asks its human before editing them,
# also Sam's for a claim of Sam's own other session
mkdir -p "$T/alex-demo/src/lib"
out=$(from_session ale11111 as_user alex "$PY" "$SYN" claim "$T/alex-demo/src/claimed.ts" "$T/alex-demo/src/lib")
check "$out" 'Claimed demo: src/claimed.ts, src/lib/' 'Alex claims a file and a folder'
check "$(from_session ale11111 as_user alex "$PY" "$SYN" claim)" 'demo: src/claimed.ts, src/lib/' 'claim without paths lists the claims'
until_ok 10 "the claims reach Sam" grep -q 'src/claimed.ts' "$T/home-sam/others.json"
out=$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/claimed.ts")")
check "$out" 'Alex has claimed src/claimed.ts (demo@main' 'a claimed file is asked about before the first edit'
check "$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/lib/util.ts")")" 'Alex has claimed src/lib/util.ts' 'a claimed folder covers its files'
out=$(from_session sam33333 as_user sam "$PY" "$SYN" claim "$T/sam-demo/src/lib/util.ts" 2>&1) && fail 'claimed twice' "$out" \
  || check "$out" 'Alex has claimed src/lib/ already' 'what another session claimed cannot be claimed again'
check "$(hook sam UserPromptSubmit "$(session sam33333 "$T/sam-demo")")" '(claimed: src/claimed.ts, src/lib/)' 'the picture shows the claims'
from_session sam55555 as_user sam "$PY" "$SYN" claim "$T/sam-demo/src/own.ts" >/dev/null
check "$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/own.ts")")" 'Your other session has claimed src/own.ts' 'a claim of an own other session is asked about too'
check "$(from_session ale11111 as_user alex "$PY" "$SYN" claim --release)" 'Released all claims' 'Alex releases the claims'
from_session sam55555 as_user sam "$PY" "$SYN" claim --release "$T/sam-demo/src/own.ts" >/dev/null
released() { [ -z "$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/claimed.ts")")" ]; }
until_ok 10 'after the release, the file needs no question' released
[ -z "$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/own.ts")")" ] && ok 'an own release takes effect at once' || fail 'own release'
check "$(cat "$T/home-alex/events.json")" '"kind": "claim"' 'claims are in the history'
check "$(as_user alex "$PY" "$SYN" status)" 'Sam → Alex' 'status lists the mail'

# State and history for the UI. An open permission prompt reports via Notification without ending the waiting Stop hook
hook alex UserPromptSubmit "$(session ale11111 "$T/alex-demo")" >/dev/null
state_is alex ale11111 working && ok 'a prompt sets the state to working' || fail 'state after the prompt' "$(state_of alex ale11111)"
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake5" & W5=$!
until_ok 5 'after the turn the session waits' state_is alex ale11111 waiting
notify alex ale11111 idle_prompt >/dev/null
state_is alex ale11111 waiting && ok 'idle_prompt does not change the state' || fail 'idle_prompt' "$(state_of alex ale11111)"
notify alex ale11111 permission_prompt >/dev/null
state_is alex ale11111 approval && ok 'an open permission prompt sets the state to approval' || fail 'approval' "$(state_of alex ale11111)"
echo "{\"session_id\":\"ale44444\",\"cwd\":\"$T/alex-demo\"}" | as_user alex "$PY" "$HOOK" StopFailure
state_is alex ale44444 error && ok 'an API error sets the state to error' || fail 'StopFailure' "$(state_of alex ale44444)"
sleep 1.5
kill -0 $W5 2>/dev/null && ok 'the notification does not end the waiting Stop hook' || fail 'Stop hook ended' "$(cat "$T/wake5")"
check "$(cat "$T/home-alex/events.json")" '"kind": "approval"' 'the approval is in the history'
check "$(cat "$T/home-sam/events.json")" '"kind": "warning"' 'warnings to Claude are in the history'
check "$(cat "$T/home-sam/events.json")" '"src/a.ts"' 'edited files are in the history'
until_ok 10 'state and history go into the branch' sh -c "git -C '$T/remote.git' show syn/alex-gh/one:state.json | grep -q '\"state\": \"approval\"'"
check "$(git -C "$T/remote.git" show syn/alex-gh/one:state.json)" '"kind": "task"' 'the task is in the shared history'
lacks "$(git -C "$T/remote.git" show syn/sam-gh/one:state.json)" '"cwd"' "a session's working directory stays on the machine"
lacks "$(git -C "$T/remote.git" show syn/sam-gh/one:state.json)" 'private' 'events in repos of other owners stay out'

# UI: data only with the token from the page and only for 127.0.0.1. Mail from the UI wakes the waiting session,
# and the reply goes back to the UI, not into a session
out=$(as_user sam "$PY" "$SYN" ui --no-browser 2>&1) || fail 'the UI starts in the background' "$out $(cat "$T/home-sam/ui.log")"
check "$out" 'Synchronauts UI: http://127.0.0.1:' 'the UI starts in the background'
U="http://127.0.0.1:$("$PY" -c 'import json,sys; sys.stdout.write(str(json.load(open(sys.argv[1]))["port"]))' "$T/home-sam/ui.json")"
tok=$(curl -s "$U/" | sed -n 's/.*name="syn-token" content="\([^"]*\)".*/\1/p')
[ -n "$tok" ] && [ "$tok" != __TOKEN__ ] && ok 'the page carries the token' || fail 'no token in the page' "$(curl -s "$U/" | head -12)"
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
[ "$(status "$U/api/state")" = 403 ] && ok 'no data without the token' || fail 'data without the token'
[ "$(status -H "X-SYN-Token: $tok" -H 'Host: evil.example' "$U/api/state")" = 403 ] && ok 'a foreign host is rejected (DNS rebinding)' || fail 'foreign host'
[ "$(status -X POST -H "X-SYN-Token: $tok" -H 'Origin: https://evil.example' -H 'Content-Type: application/json' \
  -d '{"to":"alex","text":"x"}' "$U/api/send")" = 403 ] && ok 'a foreign page cannot send' || fail 'a foreign page sends'
until_ok 10 "Alex's state reaches Sam" grep -q '"state": "approval"' "$T/home-sam/others.json"
data=$(curl -s -H "X-SYN-Token: $tok" "$U/api/state")
ui_check() { "$PY" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if ($1) else 1)" <<<"$data" && ok "$2" || fail "$2" "$data"; }
ui_check 'any(s["task"] == "Build tickets API" and s["state"] == "approval" for s in d["sessions"])' "the UI shows Alex's session with task and state"
ui_check 'any(u["kind"] == "file" and "src/a.ts" in u["files"] for u in d["overlaps"])' 'the UI shows the overlap at src/a.ts'
ui_check 'any(s["here"] and not s["repos"] and s["cwd"].endswith("private") for s in d["sessions"])' 'own sessions outside the team repos only show in the own UI'
ui_check 'any(x["kind"] == "approval" and x["login"] == "alex-gh" for x in d["events"])' "the UI history contains Alex's events"
unchanged() { local e; e=$(curl -s -D - -o /dev/null -H "X-SYN-Token: $tok" "$U/api/state" | tr -d '\r' | sed -n 's/^[Ee][Tt][Aa][Gg]: //p')
  [ "$(status -H "X-SYN-Token: $tok" -H "If-None-Match: $e" "$U/api/state")" = 304 ]; }
until_ok 10 'unchanged, the UI answers 304' unchanged
out=$(curl -s -X POST -H "X-SYN-Token: $tok" -H 'Content-Type: application/json' -H "Origin: $U" \
  -d '{"to":"alex","repo":"demo","text":"From the UI: please do not touch src/a.ts today."}' "$U/api/send")
check "$out" '"who": "Alex (session in demo)"' 'send from the UI'
rc=0; exit_of $W5 15 || rc=$?
[ $rc = 2 ] && ok 'mail from the UI wakes the waiting session' || fail "wake: exit $rc" "$(cat "$T/wake5")"
check "$(cat "$T/wake5")" 'Message from Sam in person (UI' 'the wake text says that the human writes in person'
check "$(cat "$T/wake5")" 'send sam-gh@ui' 'the reply goes back to the UI'
state_is alex ale11111 working && ok 'the woken session is working' || fail 'state after the wake-up' "$(state_of alex ale11111)"
check "$(cat "$T/home-alex/events.json")" '"kind": "woken"' 'the wake-up is in the history'
from_session ale11111 as_user alex "$PY" "$SYN" send sam@ui "Sure, I'll leave src/a.ts alone." >/dev/null
until_ok 10 "the reply shows in Sam's UI" sh -c "curl -s -H 'X-SYN-Token: $tok' '$U/api/state' | grep -q 'leave src/a.ts alone'"
out=$(hook sam UserPromptSubmit "$(session sam33333 "$T/sam-demo")")
lacks "$out" 'leave src/a.ts alone' 'mail to the UI shows in no session'

# A real conflict with a teammate: Alex pushed a change to src/x.ts, Sam changes the same line without committing.
# Sam's check fetches Alex's pushed commit and merges it with Sam's working tree
g() { git -c user.name=test -c user.email=test@example.com "$@"; }
git init -q --bare -b main "$T/conf.git"
g clone -q https://github.com/acme/conf.git "$T/c-alex" 2>/dev/null && mkdir "$T/c-alex/src" && echo base > "$T/c-alex/src/x.ts"
g -C "$T/c-alex" checkout -q -b main 2>/dev/null; g -C "$T/c-alex" add -A && g -C "$T/c-alex" commit -q -m base && g -C "$T/c-alex" push -q origin main
g clone -q https://github.com/acme/conf.git "$T/c-sam"
echo alex > "$T/c-alex/src/x.ts" && g -C "$T/c-alex" commit -q -am 'alex' && g -C "$T/c-alex" push -q origin main
echo sam > "$T/c-sam/src/x.ts"
hook alex PostToolUse "$(edit ale55555 "$T/c-alex" "$T/c-alex/src/x.ts")" >/dev/null
alex_tip() { hook alex PostToolUse "$(bash_call ale55555 "$T/c-alex")" >/dev/null; grep -q '"tip"' "$T/home-sam/others.json"; }
until_ok 20 "what Alex pushed reaches Sam" alex_tip
sam_conflict() { out=$(hook sam PostToolUse "$(edit sam99999 "$T/c-sam" "$T/c-sam/src/x.ts")"); grep -q 'would conflict' <<<"$out"; }
until_ok 20 "a conflict with Alex's pushed work is reported" sam_conflict
check "$out" "Merging Alex's session (conf@main) with this session's work would conflict in: src/x.ts" 'with the teammate, branch and file'
data=$(curl -s -H "X-SYN-Token: $tok" "$U/api/state")
ui_check 'any(o["kind"] == "conflict" and o["files"] == ["src/x.ts"] for o in d["overlaps"])' 'the UI shows the conflict'
hook sam SessionEnd "$(session sam99999 "$T/c-sam")" >/dev/null; hook alex SessionEnd "$(session ale55555 "$T/c-alex")" >/dev/null

# Missions: Sam's and Alex's Claudes solve one problem together without their humans. Each human approves once, in
# Claude Code's prompt and only in auto mode; until the end, messages between the two sessions count as approved work
call() { echo "{\"session_id\":\"$1\",\"cwd\":\"$2\",\"tool_name\":\"Bash\",\"tool_use_id\":\"$3\",\"permission_mode\":\"$4\",\"tool_input\":{\"command\":\"~/.synchronauts/syn mission approve $5\"}}"; }
out=$(from_session sam33333 as_user sam "$PY" "$SYN" mission propose --with alex@demo --hours 1 \
  "Make the ticket tests green: Sam fixes src/a.ts, Alex writes the tests. Done when both agree.")
check "$out" 'Draft sam-gh-' 'a mission starts as a draft'
MID=$(sed -n 's/^Draft \([^.]*\)\..*/\1/p' <<<"$out")
out=$(from_session sam33333 as_user sam "$PY" "$SYN" mission approve "$MID" 2>&1) && fail 'approved without a prompt' "$out" \
  || check "$out" 'Claude Code has not asked Sam' 'without the prompt there is no approval'
out=$(hook sam PreToolUse "$(call sam33333 "$T/sam-demo" toolu_1 default "$MID")")
check "$out" '"permissionDecision": "deny"' 'outside auto mode a mission does not start'
check "$out" 'only run in auto mode' 'and Claude learns why'
out=$(hook sam PreToolUse "$(call sam33333 "$T/sam-demo" toolu_2 auto "$MID")")
check "$out" '"permissionDecision": "ask"' 'in auto mode Claude Code asks Sam'
check "$out" 'Start this mission with Alex for up to 1 h' 'the prompt says with whom and how long'
check "$out" 'Plan: Make the ticket tests green' 'the prompt shows the plan'
hook sam PostToolUse "$(call sam33333 "$T/sam-demo" toolu_other auto "$MID")" >/dev/null
lacks "$(cat "$T/home-sam/missions.json")" '"joined"' 'another call does not count as the approval'
hook alex UserPromptSubmit "$(session ale11111 "$T/alex-demo")" >/dev/null
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake6" & W6=$!
sleep 0.5
check "$(from_session sam33333 as_user sam "$PY" "$SYN" mission approve "$MID")" 'Sam approved' 'the command after the yes'
out=$(hook sam PostToolUse "$(call sam33333 "$T/sam-demo" toolu_2 auto "$MID")")
check "$out" "mission $MID is approved until" 'the yes starts the mission'
check "$out" 'woken when they join' 'Claude learns that it is woken'
rc=0; exit_of $W6 15 || rc=$?
[ $rc = 2 ] && ok "the proposal wakes Alex's session" || fail "wake: exit $rc" "$(cat "$T/wake6")"
check "$(cat "$T/wake6")" 'Mission proposal from Sam' 'the wake text is the proposal'
check "$(cat "$T/wake6")" "mission approve $MID" 'with the command that asks Alex'

# Alex says yes: Sam's waiting session is woken and goes on without Sam
hook sam Stop "$(session sam33333 "$T/sam-demo")" 2>"$T/wake7" & W7=$!
sleep 0.5
out=$(hook alex PreToolUse "$(call ale11111 "$T/alex-demo" toolu_3 auto "$MID")")
check "$out" "Join Sam's mission with Sam until" 'Claude Code asks Alex'
from_session ale11111 as_user alex "$PY" "$SYN" mission approve "$MID" >/dev/null
check "$(hook alex PostToolUse "$(call ale11111 "$T/alex-demo" toolu_3 auto "$MID")")" "this session joined mission $MID" 'Alex joins'
rc=0; exit_of $W7 15 || rc=$?
[ $rc = 2 ] && ok "Alex's yes wakes Sam's session" || fail "wake: exit $rc" "$(cat "$T/wake7")"
check "$(cat "$T/wake7")" "Alex joined mission $MID" 'the wake text says Alex joined'
check "$(cat "$T/wake7")" 'Go on with the mission' 'and Claude goes on instead of asking Sam'

# Within the mission: messages are approved work, and a file of the other side needs no question
hook alex PostToolUse "$(edit ale11111 "$T/alex-demo" "$T/alex-demo/src/a.test.ts")" >/dev/null
until_ok 10 'Sam sees the joined session and the test file' sh -c "grep -q a.test.ts '$T/home-sam/others.json' && grep -q '\"joined\"' '$T/home-sam/others.json'"
out=$(hook sam PreToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.test.ts")")
[ -z "$out" ] && ok "within the mission, Alex's file needs no question" || fail 'question within the mission' "$out"
check "$(hook sam PreToolUse "$(edit sam55555 "$T/sam-demo" "$T/sam-demo/src/a.test.ts")")" '"ask"' 'a session outside the mission is still asked'
hook sam Stop "$(session sam33333 "$T/sam-demo")" 2>"$T/wake8" & W8=$!
sleep 0.5
from_session ale11111 as_user alex "$PY" "$SYN" send sam 'Tests are in src/a.test.ts, three of them fail on the id check.' >/dev/null
rc=0; exit_of $W8 15 || rc=$?
[ $rc = 2 ] && ok 'a mission message wakes the session that joined' || fail "wake: exit $rc" "$(cat "$T/wake8")"
check "$(cat "$T/wake8")" "Approved work within mission $MID" 'it counts as approved work'
check "$(cat "$T/wake8")" 'without asking Sam' 'without asking Sam'
lacks "$(hook sam UserPromptSubmit "$(session sam55555 "$T/sam-demo")")" 'three of them fail' 'other sessions get no FYI of mission mail'
data=$(curl -s -H "X-SYN-Token: $tok" "$U/api/state")
ui_check "any(m['id'] == '$MID' and m['live'] and len(m['joined']) == 2 for m in d['missions'])" 'the UI shows the mission with both sessions'

# The end: everyone gets the result, then messages are information again
check "$(from_session ale11111 as_user alex "$PY" "$SYN" mission end 'All 12 tests green, PR #7 is open.')" "Mission $MID ended" 'Alex ends the mission'
until_ok 10 'the end reaches Sam' grep -q '"ended"' "$T/home-sam/others.json"
out=$(hook sam PostToolUse "$(bash_call sam33333 "$T/sam-demo")")
check "$out" "Mission $MID ended by Alex's Claude" 'Sam learns that it is over'
check "$out" 'All 12 tests green' 'with the result'
lacks "$(hook sam PostToolUse "$(bash_call sam33333 "$T/sam-demo")")" 'mission' 'the end is reported once'
from_session sam33333 as_user sam "$PY" "$SYN" send alex 'Thanks!' >/dev/null
lacks "$(tail -12 "$T/home-sam/mail.json")" '"mission"' 'after the end, messages are no longer mission mail'
out=$(curl -s -X POST -H "X-SYN-Token: $tok" -H 'Content-Type: application/json' -H "Origin: $U" -d "{\"id\":\"$MID\"}" "$U/api/end")
check "$out" 'No such active mission' 'an ended mission cannot be stopped again'
check "$(as_user sam "$PY" "$SYN" status)" "$MID by Sam, ended" 'status lists the mission'

# Several owners count as team repos with --org a,b, for friends who each keep their repos in their own account
out=$(echo "$(edit sam88888 "$T/private" "$T/private/src/a.ts")" | SYN_ORGS=acme,someone as_user sam "$PY" "$HOOK" PostToolUse)
grep -q 'someone/private' "$T/home-sam/status.json" && ok 'a second owner in --org makes its repos team repos' || fail 'orgs list' "$(cat "$T/home-sam/status.json")"
hook sam SessionEnd "$(session sam88888 "$T/private")" >/dev/null

# Session end: Alex drops out of the picture
hook alex SessionEnd "$(session ale11111 "$T/alex-demo")" >/dev/null
hook alex SessionEnd "$(session ale33333 "$T/alex-other")" >/dev/null
hook alex SessionEnd "$(session ale44444 "$T/alex-demo")" >/dev/null
until_ok 10 'ended sessions drop out of the picture' no_session 'Build tickets API' "$T/home-sam/others.json"
[ ! -s "$T/home-sam/hook.log" ] && [ ! -s "$T/home-alex/hook.log" ] && ok 'no errors in the hooks' || fail 'hook.log' "$(cat "$T"/home-*/hook.log)"
echo "all green"
