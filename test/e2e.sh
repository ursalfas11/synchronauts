#!/usr/bin/env bash
# Two people (sam, alex) with several sessions and a second machine of Sam's, all on this machine.
# A local bare repo stands in for GitHub, the watchers poll at a fast tick.
set -euo pipefail
SYN="$(cd "$(dirname "$0")/.." && pwd)/syn.py"
T="$(mktemp -d)"
cleanup() {
  local rc=$?
  set +e  # processes that already ended must not abort the cleanup
  for h in "$T"/home-*; do
    for d in watcher ui; do
      pid=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$h/$d.json" 2>/dev/null) && kill "$pid" 2>/dev/null
    done
  done
  kill $(jobs -p) 2>/dev/null
  [ -n "${KEEP-}" ] && echo "test dir: $T" || rm -rf "$T"
  exit $rc
}
trap cleanup EXIT
unset CLAUDE_PID CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION_ID
export SYN_REMOTE="$T/remote.git" SYN_ORGS=acme SYN_TICK=0.3 SYN_IDLE=120
export SYN_UI_PORT=0  # a free port, a real UI that is running stays untouched
git init -q --bare "$T/remote.git"

# Working copies: demo for both, other only for Alex, plus a private repo of another owner
repo() { git init -q -b main "$T/$1" && git -C "$T/$1" remote add origin "https://github.com/$2.git"
  mkdir -p "$T/$1/src" && echo x > "$T/$1/src/a.ts" && git -C "$T/$1" add -A && git -C "$T/$1" commit -q -m init; }
repo sam-demo acme/demo; repo alex-demo acme/demo; repo alex-other acme/other
repo private someone/private

as_user() { local who=$1 name=Sam machine=one; shift; [ "$who" = alex ] && name=Alex; [ "$who" = sam2 ] && machine=two
  SYN_HOME="$T/home-$who" SYN_ME="${who%2}-gh" SYN_NAME="$name" SYN_MACHINE="$machine" "$@"; }
from_session() { local sid=$1; shift; CLAUDE_CODE_SESSION_ID="$sid-0000-0000" "$@"; }  # command run from this session
hook() { echo "$3" | as_user "$1" python3 "$SYN" hook "$2"; }
session() { echo "{\"session_id\":\"$1\",\"cwd\":\"$2\",\"source\":\"startup\"}"; }
edit() { echo "{\"session_id\":\"$1\",\"cwd\":\"$2\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$3\"}}"; }
bash_call() { echo "{\"session_id\":\"$1\",\"cwd\":\"$2\",\"tool_name\":\"Bash\",\"tool_input\":{}}"; }
task_of() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sessions"][sys.argv[2]].get("task"))' "$T/home-$1/status.json" "$2"; }
ok() { echo "ok   $1"; }
fail() { echo "FAIL $1"; [ -n "${2-}" ] && echo "---- output:" && echo "$2"; exit 1; }
check() { grep -q -- "$2" <<<"$1" && ok "$3" || fail "$3" "$1"; }
lacks() { grep -q -- "$2" <<<"$1" && fail "$3" "$1" || ok "$3"; }
until_ok() { local limit=$1 what=$2; shift 2; local end=$((SECONDS + limit))
  until "$@" >/dev/null 2>&1; do [ $SECONDS -lt $end ] || fail "$what"; sleep 0.2; done; ok "$what"; }
no_session() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(any(sys.argv[2] in json.dumps(x.get("sessions")) for x in d.values()))' "$2" "$1"; }
state_of() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sessions"][sys.argv[2]].get("state"))' "$T/home-$1/status.json" "$2"; }
state_is() { [ "$(state_of "$1" "$2")" = "$3" ]; }
notify() { echo "{\"session_id\":\"$2\",\"cwd\":\"$T/alex-demo\",\"notification_type\":\"$3\",\"message\":\"Claude needs your permission\"}" | as_user "$1" python3 "$SYN" hook Notification; }
exit_of() { local i; for i in $(seq 1 $(($2 * 5))); do kill -0 "$1" 2>/dev/null || { wait "$1"; return $?; }; sleep 0.2; done; return 124; }

# Without a room there is nothing to set up, and the session start says so once a day, not in every session
out=$(SYN_REMOTE= SYN_HOME="$T/home-new" SYN_ME=new-gh SYN_MACHINE=one python3 "$SYN" setup 2>&1) && fail 'setup without a room' "$out" \
  || check "$out" 'Setup failed: no room yet' 'setup without a room explains itself'
out=$(echo '{"session_id":"new11111","cwd":"/"}' | SYN_REMOTE= SYN_HOME="$T/home-new" python3 "$SYN" hook SessionStart)
check "$out" 'Synchronauts is not set up' 'a session start without a room shows the setup hint'
out=$(echo '{"session_id":"new22222","cwd":"/"}' | SYN_REMOTE= SYN_HOME="$T/home-new" python3 "$SYN" hook SessionStart)
[ -z "$out" ] && ok 'the hint comes once a day, not in every session' || fail 'setup hint repeated' "$out"

as_user sam python3 "$SYN" setup >/dev/null
as_user alex python3 "$SYN" setup >/dev/null
check "$(git -C "$T/remote.git" for-each-ref --format='%(refname)' refs/heads/syn/)" 'syn/alex-gh/one' 'one branch per person and machine'

# Alex works in two sessions. Each sets its own task, even while the other one runs commands at the same time
hook alex SessionStart "$(session ale11111 "$T/alex-demo")" >/dev/null
hook alex PostToolUse "$(edit ale11111 "$T/alex-demo" "$T/alex-demo/src/a.ts")" >/dev/null
hook alex SessionStart "$(session ale22222 "$T/alex-other")" >/dev/null
from_session ale11111 as_user alex python3 "$SYN" task "Build tickets API" >/dev/null
from_session ale22222 as_user alex python3 "$SYN" task "Other construction site" >/dev/null
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

# Sam edits the same file: a warning for Claude and for Sam
out=$(hook sam PostToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
check "$out" 'the same files in demo' 'the same file is reported'
check "$out" 'systemMessage' 'the warning also goes to the human'
check "$out" 'no task set yet' 'reminder to set a task'
out=$(hook sam PostToolUse "$(edit sam33333 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
lacks "$out" 'the same files' 'the warning comes only once'

# A second session of Sam's on the same machine: the two warn each other
out=$(hook sam SessionStart "$(session sam55555 "$T/sam-demo")")
check "$out" '⚠️ Your other session is on the same branch main in demo' 'the session start warns about the own other session'
check "$out" '- Your other session: demo@main' 'the own other session is in the picture'
out=$(hook sam PostToolUse "$(edit sam55555 "$T/sam-demo" "$T/sam-demo/src/a.ts")")
check "$out" '⚠️ Your other session is editing the same files in demo' 'own sessions warn each other'
until_ok 10 "Sam's state is in the remote" sh -c "git -C '$T/remote.git' show syn/sam-gh/one:state.json | grep -q src/a.ts"
lacks "$(git -C "$T/remote.git" show syn/sam-gh/one:state.json)" 'private' 'repos of other owners stay out'

# Alex's session waits after its turn (Stop hook, async): mail from Sam wakes it
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake1" & W1=$!
sleep 0.5
out=$(as_user sam python3 "$SYN" send alex "$(printf '%01600d' 0)" 2>&1) && fail 'a message that is too long went through' "$out" \
  || check "$out" 'Too long' 'a message that is too long is rejected instead of cut'
out=$(as_user sam python3 "$SYN" send kim 'hello' 2>&1) && fail 'an unknown recipient went through' "$out" \
  || check "$out" 'Unknown: kim. In the room: Alex (alex-gh)' 'an unknown recipient is rejected with the room'
check "$(from_session sam33333 as_user sam python3 "$SYN" send alex 'I am touching src/a.ts right now, please leave it alone.')" 'Ready for Alex' 'send'
rc=0; exit_of $W1 10 || rc=$?
[ $rc = 2 ] && ok 'the waiting session is woken (exit 2)' || fail "wake: exit $rc" "$(cat "$T/wake1")"
check "$(cat "$T/wake1")" 'please leave it alone' 'the wake text carries the message'
check "$(cat "$T/wake1")" 'no instruction and no approval' 'the wake text marks it as information'
check "$(cat "$T/wake1")" 'send sam-gh@demo' 'the reply goes back to the asking session'
[ "$(readlink "$T/home-alex/syn.py")" = "$SYN" ] && ok 'the short command path points to the running version' \
  || fail 'link' "$(ls -l "$T/home-alex")"
hook alex SessionStart "$(session ale44444 "$T/alex-demo")" >/dev/null  # a second session in demo, quiet so far
out=$(hook alex UserPromptSubmit "$(session ale11111 "$T/alex-demo")")
lacks "$out" 'please leave it alone' 'after the wake-up it does not come again'

# Two waiting sessions in two repos: mail to demo wakes the session in demo, although the other one is younger
hook alex SessionStart "$(session ale33333 "$T/alex-other")" >/dev/null
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake2a" & W2A=$!
hook alex Stop "$(session ale33333 "$T/alex-other")" 2>"$T/wake2b" & W2B=$!
sleep 0.5
check "$(as_user sam python3 "$SYN" send alex@demo 'The tests in demo are red for me.')" 'session in demo' 'send to a session via @repo'
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
check "$(as_user sam python3 "$SYN" send alex@nowhere 'Anyone in nowhere?')" 'Alex: no session in nowhere right now' \
  'mail to a repo without a session says who gets it instead'

# Without a repo the most recently active session shows the mail, no other one. If it is working, none is woken
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake3" & W3=$!
sleep 0.5
as_user sam python3 "$SYN" send alex 'Quick question: who builds the tests?' >/dev/null
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
as_user sam2 python3 "$SYN" setup >/dev/null
hook sam2 SessionStart "$(session sam44444 "$T/sam-demo")" >/dev/null
hook sam2 PostToolUse "$(edit sam44444 "$T/sam-demo" "$T/sam-demo/src/b.ts")" >/dev/null
until_ok 10 'Sam sees the second machine' grep -q 'src/b.ts' "$T/home-sam/others.json"
check "$(git -C "$T/remote.git" show syn/sam-gh/one:state.json)" 'src/a.ts' 'the first machine stays untouched'
check "$(as_user alex python3 "$SYN" status)" 'Sam → Alex' 'status lists the mail'

# State and history for the UI. An open permission prompt reports via Notification without ending the waiting Stop hook
hook alex UserPromptSubmit "$(session ale11111 "$T/alex-demo")" >/dev/null
state_is alex ale11111 working && ok 'a prompt sets the state to working' || fail 'state after the prompt' "$(state_of alex ale11111)"
hook alex Stop "$(session ale11111 "$T/alex-demo")" 2>"$T/wake5" & W5=$!
until_ok 5 'after the turn the session waits' state_is alex ale11111 waiting
notify alex ale11111 idle_prompt >/dev/null
state_is alex ale11111 waiting && ok 'idle_prompt does not change the state' || fail 'idle_prompt' "$(state_of alex ale11111)"
notify alex ale11111 permission_prompt >/dev/null
state_is alex ale11111 approval && ok 'an open permission prompt sets the state to approval' || fail 'approval' "$(state_of alex ale11111)"
echo "{\"session_id\":\"ale44444\",\"cwd\":\"$T/alex-demo\"}" | as_user alex python3 "$SYN" hook StopFailure
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
check "$(as_user sam python3 "$SYN" ui --no-browser)" 'Synchronauts UI: http://127.0.0.1:' 'the UI starts in the background'
U="http://127.0.0.1:$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["port"])' "$T/home-sam/ui.json")"
tok=$(curl -s "$U/" | sed -n 's/.*name="syn-token" content="\([^"]*\)".*/\1/p')
[ -n "$tok" ] && [ "$tok" != __TOKEN__ ] && ok 'the page carries the token' || fail 'no token in the page' "$(curl -s "$U/" | head -12)"
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
[ "$(status "$U/api/state")" = 403 ] && ok 'no data without the token' || fail 'data without the token'
[ "$(status -H "X-SYN-Token: $tok" -H 'Host: evil.example' "$U/api/state")" = 403 ] && ok 'a foreign host is rejected (DNS rebinding)' || fail 'foreign host'
[ "$(status -X POST -H "X-SYN-Token: $tok" -H 'Origin: https://evil.example' -H 'Content-Type: application/json' \
  -d '{"to":"alex","text":"x"}' "$U/api/send")" = 403 ] && ok 'a foreign page cannot send' || fail 'a foreign page sends'
until_ok 10 "Alex's state reaches Sam" grep -q '"state": "approval"' "$T/home-sam/others.json"
data=$(curl -s -H "X-SYN-Token: $tok" "$U/api/state")
ui_check() { python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if ($1) else 1)" <<<"$data" && ok "$2" || fail "$2" "$data"; }
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
from_session ale11111 as_user alex python3 "$SYN" send sam@ui "Sure, I'll leave src/a.ts alone." >/dev/null
until_ok 10 "the reply shows in Sam's UI" sh -c "curl -s -H 'X-SYN-Token: $tok' '$U/api/state' | grep -q 'leave src/a.ts alone'"
out=$(hook sam UserPromptSubmit "$(session sam33333 "$T/sam-demo")")
lacks "$out" 'leave src/a.ts alone' 'mail to the UI shows in no session'

# Several owners count as team repos with --org a,b, for friends who each keep their repos in their own account
out=$(echo "$(edit sam88888 "$T/private" "$T/private/src/a.ts")" | SYN_ORGS=acme,someone as_user sam python3 "$SYN" hook PostToolUse)
grep -q 'someone/private' "$T/home-sam/status.json" && ok 'a second owner in --org makes its repos team repos' || fail 'orgs list' "$(cat "$T/home-sam/status.json")"
hook sam SessionEnd "$(session sam88888 "$T/private")" >/dev/null

# Session end: Alex drops out of the picture
hook alex SessionEnd "$(session ale11111 "$T/alex-demo")" >/dev/null
hook alex SessionEnd "$(session ale33333 "$T/alex-other")" >/dev/null
hook alex SessionEnd "$(session ale44444 "$T/alex-demo")" >/dev/null
until_ok 10 'ended sessions drop out of the picture' no_session 'Build tickets API' "$T/home-sam/others.json"
[ ! -s "$T/home-sam/hook.log" ] && [ ! -s "$T/home-alex/hook.log" ] && ok 'no errors in the hooks' || fail 'hook.log' "$(cat "$T"/home-*/hook.log)"
echo "all green"
