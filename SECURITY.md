# Security

## Supported versions

| Version | Supported |
|---|---|
| 0.6.x | yes, the latest release gets the fixes |
| 0.5.x and older | no, update to 0.6 |

Everyone in a room should run the same release: 0.5 peers keep working for presence, plain mail and the board, but see
the [compatibility table](CHANGELOG.md#compatibility) for what they cannot take part in.

## Reporting

Please report a vulnerability privately, through GitHub's advisory page:
<https://github.com/ursalfas11/synchronauts/security/advisories/new>. Do not open a public issue for it.

You get an answer within 7 days. There is no bounty. Fixes are coordinated: the report stays private until a release
with the fix is out, and in any case for at most 90 days. Describe what you can do, with which access (room member,
local user, website in a browser), and the version.

## Threat model

Synchronauts has no server. A private Git repo, the room, is the bus: every person writes one branch per machine,
`syn/<login>/<machine>`, holding one `state.json`. The hooks and the watcher run as the user, and what they read from
the room ends up in Claude's context.

### Assets

- The user's machine and what their Claude can do on it (files, commands, pushes).
- Claude's context: text from the room that Claude reads can steer it.
- The room repo: its states, history and **mail. The room has no private messages: every member of the room can read
  every message, also those addressed to someone else.** Do not put secrets or customer data in a message.
- The SSH key that signs messages, and the key of the local board with the one-time code that pairs a browser with it.

### Trust boundaries

- **The room is the trust boundary.** Whoever can write to the room repo can write any branch in it, including one named
  after somebody else. A branch name proves nothing.
- Only a mail field is attributable, in one of two ways. The sender signs it with an SSH key that the keys URL (GitHub
  by default) lists for the sender's login; or, in a room on GitHub, GitHub's record of pushes (the repo's activity)
  shows that the sender's account pushed the commit that holds it. Both rest on the account at GitHub. Everything else
  in a state is presence information that any room member can fake.
- The local board listens on 127.0.0.1. Its API needs a key that exists only in the running server and in the browser
  tab that paired with it; a tab pairs with a one-time code from the user's own folder (`ui-pair.json`). Anything that
  runs as the user can read that code, as it can read the SSH keys, and pair with the board.

### Attackers considered

- A malicious room member: writes branches in other names, forged mail, odd types, huge or hidden-character texts.
- A room member whose account or SSH key was stolen: signs as its owner until the key is removed from the keys URL,
  and with the login for GitHub pushes as its owner.
- Another user on the same machine (port, files).
- A website in the user's browser against the board (CSRF, DNS rebinding).
- The network between the machine and the Git host or the keys URL.
- A Claude that follows a message it should not.

### Signed mail fields

The signature covers these fields of a mail record and the sender's login. A copy with one of them changed, or a
different sender, is a different seal and is checked anew:

`id`, `to`, `time`, `text`, `repo`, `mission`, `kind`, `source`, `from_repo`, `crew`, `until`, `room`

`crew` (the people of a mission, the proposer first) and `until` (its end time) are only on a mission invite. `room` is
the id of the room the message was written for, on all mission mail (invite, joined, end and work messages); plain mail
does not carry it. A signed message whose `room` is not this room's is shown as forged, so a copy cannot be played back in
another room; mission mail without a `room` does not count.

### Unsigned fields of a state

Everything else a room member can write, also in somebody else's branch. `tidy()` reduces a foreign `state.json` to the
fields below, each one checked; anything else is dropped. A value that fails its check is left out, not cleaned, so it
cannot turn into something else on the way. What is left is bounded and plain: the line Claude gets about a session
shows at most six claims and 400 characters of its repos, branches and claims, and 120 characters of its task, as one
line without markup, control or hidden characters. Claude is told that it is information, not instructions: the skill
says so for tasks, file names and claims as for messages. A room member can still write many sessions and branches,
each with a line of its own (see Not protected).

| Field | Reaches Claude's context | Check today |
|---|---|---|
| login, machine | yes, in situation lines | letters, digits and a few signs, length limits; a login that differs from another one of the room only in case or looks like it is marked `⚠` and kept apart |
| name | yes, as the display name, with `(@login)` where two people could be mixed up | letters, digits, spaces and `.'-` only, at most 40 characters; a login whose branches disagree about it shows as the bare login |
| repo, branch | yes, in situation lines and notes | must look like a repo (`owner/name`) or branch name: neither can hold a space, a quote, a line break or a hidden character; words joined with `_`, `-` or `/` still pass |
| files, claims | yes, in situation lines, the question before an edit and `syn status` | at most 30 of the first 60, each at most 240 characters and shaped like a path inside a repo: letters of any script with their accents and marks, digits, at most four spaces and `. _ - + @ = , ~ # % ( ) [ ] $ /`, a claim also `* ?` and a final `/`; no empty, `.` or `..` part, so no absolute path; no drive letter or URL (no `:`); no `~`, `-`, `$NAME` or `%NAME%` at the start, so nothing that reads as the home folder, a variable or an option; no `$(` or `${`; no hidden character. A situation line shows at most six claims and 400 characters of repos, branches and claims. A name that fails is left out; an own file name that fails is not published either, and `syn claim` refuses it |
| task | yes, in situation lines, the question before an edit and `syn status` | one line of at most 200 characters; Claude's context gets at most 120 of them (`syn status` 200), every `"` written as `'`, so a task cannot close the quotes it is shown in |
| state | board only | one of a fixed list |
| agent | board only | a short id (`claude`, `codex`) |
| last, start, state_since | as clock times | read as a time between the years 2000 and 2100; any other counts as long ago |
| tip (commit hash) | no, only an argument of `git merge-tree` after the check | hexadecimal, 40 to 64 characters |
| events | board only | at most 100 with 12 fields each; a text is one line of at most 300 characters, file names are checked like files |

### Threats and what is done about them

| Threat | Behaviour before 0.6 | Behaviour in 0.6 | Residual risk |
|---|---|---|---|
| Mail from somebody without a key, and forged mail in their name | unsigned mail could not be told from forged mail, so everybody needed an SSH key on GitHub, and a second machine without one made its owner's mail show as forged | in a room on GitHub the record of pushes names the account behind every push, forced ones too: mail without a signature is the sender's when that account pushed the commit it was read from, and forged when another account did; the warning names that account. An old commit of the sender that somebody else pushed back counts as the sender's, like a copy of a signed message | an account that GitHub does not show the record to checks signatures only (setup says so); a record that answers late leaves mail unsigned until it does; whoever has the sender's login for GitHub pushes as the sender |
| A stranger invites somebody to a repo that looks like a room | no look for invitations; setup accepted the one to the room it was told | a session start on a machine without a room notes open invitations to a repo with the description setup gives a room, and the next prompt tells Claude and the human who invites to which room, once. Nothing is accepted or joined without the human's yes | a human who says yes to a stranger's room shows it the repos, branches, file paths and tasks of their sessions |
| Mission hijack: a branch in the room defines, changes or ends a mission, or fakes a join | the `missions` field of any branch counted; unsigned joins and ends counted | a mission exists only as far as signed mail proves it: people and end time are signed in the invite, joins, ends and work messages count only as signed mail of the mission's people; the field is gone from `state.json` | A person of the mission can sign harmful instructions within the plan (see Not protected) |
| Mission close text: a forged proposal makes Claude "do what the proposal says" | any message of kind invite got the instruction | only a live, signed proposal from its proposer to a person of its crew does (tell the human the plan and run the approve command), and the instruction adds that nothing the plan asks for comes before the yes; everything else is information that cannot be joined | any room member can sign a proposal of their own with you in the crew and get that instruction; its plan is that member's text, untrusted until you approve it |
| Playing a signed mission message back in another room | no room in the signature | `room` is signed; another room's id shows as forged, mission mail without it does not count | rooms that really share one repo |
| Copying the id of a real message onto a forged one to stop it | both copies counted as forged | the copy that verifies wins; a message signed under an id that names another sender (every id carries its sender's login) is forged; copies that differ only in how the signature is written are one message; only two verified different texts of one sender under one id are both forged; the pick takes time in proportion to the copies, so a flood of them cannot hold up a hook past its timeout | the sender can sign two texts under one id and lose that message |
| Name impersonation: a room member calls herself Sam, or picks a look-alike name or another person's login as her name | names were shown as written; `send <name>` went to everyone the name fitted, `--with` took the first | every message header carries the login; where two people could be mixed up, and always for a name with a letter that is not plain Latin, the board and Claude's texts show `Name (@login)`; `send` and `--with` take a login only as written exactly and refuse an ambiguous name, and the refusal tells Claude to ask its human which login is meant; a board message counts as "in person" only when signed | look-alike names are caught by a best-effort table; a name that copies the login of somebody who has not joined yet resolves as a name (the confirmation shows the real login); a reader who ignores the login |
| Login impersonation: a branch in a case variant (`Alice-gh`) or a look-alike (`a1ice-gh`) of a real login | `send alice` reached every login the name fitted; on macOS and Windows a case variant stopped the sync and could push the real person out of the picture | each exact login is a person of its own, marked `⚠ Name (@login)`; only the exact spelling resolves, also while the real login has no branch yet; unsigned mail in another case of a login that signs is forged; every branch is fetched into an escaped ref of its own (`refs/syn-in/`), and refs of 0.5 that cannot be deleted never stop the sync | the look-alike table is best effort; a look-alike account with a valid key of its own signs its own mail, which shows under its own marked login |
| A machine deletes branches in the room (clean-up of dead branches) | nothing was ever deleted; dead branches stayed, were read by every poll and took part in the names | a machine deletes only `syn/<own login>/<other machine>` for an exact, validated login and machine name, only when the commit of the branch is more than 30 days old and still is the one that was seen (`--force-with-lease`), at most 20 per start, never the branch it runs on; the content of a branch never picks a deletion; dead branches of others are only left out of the state; a failed delete is ignored | a room member with write access can already overwrite or delete any branch; a branch with a forged old commit date is skipped by everybody, and one in a login of mine is deleted by me. A machine that was off for more than 30 days is forgotten until its next start, when it pushes again |
| Unsigned state steers Claude: a branch writes a task or file names that read like instructions, close the quotes of a situation line, fill Claude's context, or hold a shell command or hidden characters | file and claim names were any one-line text of up to 300 characters, the task 200 characters as written, a session's line as long as its repos and claims | file and claim names count only if they look like a path inside a repo, otherwise they are left out; a task reaches Claude as one line of at most 120 characters that cannot close its quotes; the line about a session shows at most six claims and 400 characters of repos, branches and claims; the skill counts tasks, file names and claims of others as information, not instructions | a short task can still ask for something, and a branch, file or claim name can read like an instruction when its words are joined with `_`, `-` or `/` (`ignore_all_previous_instructions`); that Claude does not follow them rests on the skill and the marking, which lowers the risk but does not remove it. Many sessions and branches each bring a line of their own |
| Trust marks that mislead: forged mail in `syn status` and in the terminal, the board's view of mail between others, of copied ids and of mail in a branch of your own login | `syn status` and the line for the human printed forged mail like real mail; the board showed signed mail between two others as unsigned, of two messages under one id the one read last, and every message in a branch of your login as your own | `syn status` and the line for the human mark mail to you `[forged]` or `[unsigned]`, and `status` indents the further lines of a message; the board picks one message per id as the hooks do (a forged copy that is a mission message shows as forged instead of hiding the real one), marks unsigned mail, marks signed mail between two others "not checked" in the same colour (whether a message carries a signature is the writer's choice), and shows only mail written on this machine as yours | the board does not check the signatures of mail between two others (it is not an action surface); every value but ok and forged counts as unsigned |
| Chaining onto the human gate: `mission approve <id> && <anything>` gets the human's yes for the whole line | the prompt came for any command that contained `mission approve`, and the yes let the rest of the line run | the prompt comes only when `syn mission approve <id>` is the whole command; a longer command that runs the gate in one of its parts is refused, and nothing is approved | none known for chaining itself; see the next rows for the gate reached in other ways |
| Indirect invocation of the gate: through a variable, `bash -c`, `eval`, `xargs`, a wrapper (`env`, `sudo`, `timeout`, ...), a here-document or a script written for it | only the literal words `mission approve <id>` were looked for: written out anywhere in the line they got the prompt for all of it, hidden (quoted apart, in a script) they ran without one | the command is read the way a shell reads it (quotes, escapes, `$'..'`, `${..}`, `$IFS`, `{a,b}`, command substitutions, here-documents, `sh -c`, `eval`, `env -S`, `find -exec`, the shell calls of a `python -c`); refused are a part that executes and mentions `mission` and `approve` (what its `$(..)` prints counts as its words), a call of syn whose subcommand is only known at run time, a part whose program is only known at run time and mentions either word, a script it runs that mentions the gate and that git does not know unchanged (untracked, changed, outside a repo), and a command that runs code while variables it sets, or text that a plain tool prints into a file or a program, name the gate. Plain text and search tools and `git` take their words as data | a program that builds the call at run time from parts that never show together (string joins in `python -c`, a file read at run time), a script reached through a folder only known at run time (`cd "$DIR"`), a tracked script edited and committed earlier or replaced by a copy or a link in the same command, a script over 64 KB, `make` and `npm` scripts, an alias of git or gh defined in an earlier command. None of these gets the prompt, so the digest of the next row still decides |
| A program of its own named syn: `./syn mission approve <id>`, written for it, runs anything once the human says yes | the prompt came for any program whose name ended in `syn` | the prompt comes only when syn itself runs the gate: the launcher `~/.synchronauts/syn` by its path (`~`, `$HOME`, quoted) or bare where PATH leads to it, or `syn.py` through python; any other program is refused | the launcher and `syn.py` themselves can be changed by a program that runs as the user (see Not protected) |
| Forging the approval: Claude writes the `approving` record of its session file, which the hook after the call checks | the record held only the mission id and the call id, and the hook after every Bash call took it as the yes: whoever wrote it with the id of a running call started the mission | the record holds an HMAC over session, tool call, mission, signed invite and what the prompt showed, keyed with `approve.key`, a secret of this machine (mode 0600, made on first use); a record written by hand or copied to another call starts nothing, and the files in `~/.synchronauts` are guarded (rows below) | a program that runs as the user can read the key (see Not protected) |
| Forging a mission record: Claude writes a draft or a joined mission into `missions.json` | syn took the file as written: a draft with another plan or crew could be approved, and a record with this session in it counted as a joined mission, without any prompt | syn seals each record it writes with an HMAC keyed with `approve.key` and reads only records whose seal fits; one written in another way, or changed after, counts for nothing. Records from before 0.6 carry no seal and count for nothing either | a program that runs as the user can read the key (see Not protected) |
| Claude's tools on the state of syn: an edit of `missions.json`, `sessions/`, `config.json` or another file in `~/.synchronauts`, a read of `approve.key`, of the signing key that `syn key` made (`signing-key`) or of the board's pairing code, also through `syn ui --pair`, which prints the code | not guarded | refused: Edit, Write, MultiEdit, NotebookEdit and Codex patches under `~/.synchronauts` (paths resolved, links followed, case folded on macOS and Windows); shell commands that write there (redirects, `tee`, `cp`, `mv`, `ln` and hard links, `install`, `rsync`, `scp`, `tar x`, `unzip`, `curl -o`, `wget`, `sort -o`, `sed -i`, `perl -i`, `rm`, `shred`, `touch`, `truncate`, `dd`, `find -delete` and `-exec`, `git checkout` and `restore`, a write in `python -c`, `node -e`, `perl -e` or `awk`, a folder above it that `rm -r`, `mv` or a recursive copy takes along, any of these through a link that the same command makes (`ln -s`, also into a folder that the command removes, replaces or makes first, or with BSD `ln -F`; a link copied with `cp -P`, `-d`, `-a` or `-R`, `mv` or `rsync -l`, also one the command made itself or one from a path only known at run time; links of links; a link to a glob) or through an old link that stays where `ln` without `-f` fails, `git` where it may change files there or in a working tree that holds the folder (`-C`, `--git-dir`, `--work-tree`, `GIT_DIR` or `GIT_WORK_TREE` set anywhere in the command: before `git`, before a shell that runs it, by an assignment (also `+=`), `export`, `declare -x`, a nameref, `read` or `printf -v`, or by a name the command builds at run time; `core.worktree`, `init`, `clone`, `worktree add`, `submodule add`, a `.git` written into a folder above it), a folder mounted into a container (`docker` or `podman` `-v`, `--mount`, `docker cp`), a target or code only known at run time (`eval "$x"`, `sh -c "$x"`) in a command that names the folder, runs in it or may get there by a `cd` (along `CDPATH` or `cdable_vars` from the first part of the command that may set them on, in all of it when it has a loop or a function: spelled quoted, `$'..'`, escaped, as zsh's `cdpath` or `-T` (`set`, `setopt`, `zsh`), as option names such as `c_dablevars` for `shopt`, `setopt`, `set -o`, `zsh -o` or zsh's `options[..]`, or as a variable or option whose name the command builds at run time from its own text (`${n}PATH`, `printf -v`, `read <<<`, `for`, `eval "${n}..."`, `$(printf ..)`); a relative folder that runs along its path, zsh's `cd old new`, a `cd` that fails while the command is in it)); reading `approve.key` or the pairing code with a shell command (by a path, a glob, `{a,b}`, or a folder read whole: `grep -r`, `rg`, `cp -r`, `tar`, `find -exec`, also through a link the command makes), Read, Grep or Glob; a read under the folder whose file only the run names (a variable or a `$(..)` in the path, or any such word in a command that runs in the folder), since nobody can tell before whether it is a log or the key; a command that names the folder and runs a program whose way with files the check does not know (`sed` with a script, `patch`, `yq`, `ruby`, `php`, an editor: anything but the plain readers, the writers above, shells and the interpreters whose code is read), or sets a variable that makes a tool run a program (`GIT_PAGER`, `GIT_EXTERNAL_DIFF`, `GIT_SSH_COMMAND`, `GIT_CONFIG_*`, `PAGER`, `EDITOR`, `LESSOPEN`, `BASH_ENV`, `NODE_OPTIONS`, `LD_PRELOAD` and their kind), or hands files to one (`git grep -O`); running `syn ui --pair` (bare, by its path, through python or a shell, chained, nested, with `--pair` from a variable or `xargs`, or echoed into a shell), which is for the human's own terminal | the shell check is a heuristic over the words of a command, not a model of every program: a program that writes there on its own (a script, a tool that gets there without the folder in its words, a path computed at run time or reached through a variable set in an earlier command or in a file the command sources, or whose name comes from a file, stdin, the environment or a program's output at run time (also `CDPATH`, `cdable_vars`, `GIT_DIR`, `GIT_WORK_TREE`: `export $(cat .env \| xargs)`, `read` from a file, `eval "$(tool init)"`), a `cd -` or `popd` back into it), a link or a `.git` that an archive, a clone, a recursive copy or a program makes in the same command, a repository whose own configuration moves its working tree there (`core.worktree` in its config file, `GIT_CONFIG_*`), a program that writes by its own files or options (a compose file), a recursive search or copy from a folder above `~/.synchronauts`; a script written in an earlier command that reads the code file or runs `syn ui --pair`, and code that calls syn's own functions (`new_pair_code()`), still get a pairing code: with it a page can pair and write on the board as the human, which teammates see as "in person"; Read, Grep and Glob are refused by the path or pattern they are given (Claude Code runs them through the PreToolUse hook); a Grep in `~/.synchronauts` is refused, and one from a folder above it unless a glob or a type keeps it to files that are no secret (its pattern is not looked at: a refusal that depends on a match would tell the key bit by bit), and so is a Glob whose pattern names one; Codex has no such tools |
| Exhausting the checks: a command so long, so nested or so slow to read (deep `${..}`, many scripts or globs) that the hook fails or runs past its timeout; a PreToolUse hook that fails or times out does not stop the tool call | a nest of a few hundred `${..}` crashed the reader, and the call ran; long commands, globs and scripts that run each other could keep the hook past its 10 seconds | the checks of one command share a budget (3 seconds, 16 levels of `${..}`, 64 scripts, 24 git calls, 5000 folder entries, and commands up to 256 KB and 6 levels of nesting read in full) and refuse what they cannot read within it; a check, or the PreToolUse hook as a whole, that fails for another reason refuses a call that names the gate, `~/.synchronauts` or `ui --pair`, and writes the error to `hook.log`; refusals are printed in ASCII, so that no character of a path in them (a lone surrogate) can keep them from being printed: a hook that prints nothing lets the call run | a command that names none of them passes when a check fails; parts nested deeper than 6 levels are not read, they count only by the words of the gate and as writes to a place only the run knows |
| The human gate is a hook | the same | the gate and the guards above are PreToolUse hooks of Claude Code; missions still need auto mode, whose classifier holds back risky actions | a Claude that runs code outside these hooks (Codex without them, hooks turned off) or through a tool they do not match can bypass them; the HMAC, the seal and the path checks raise the bar, they are not a sandbox |
| Mail of somebody whose SSH key is not a plain file: a key that only an ssh-agent holds (1Password, Secretive) or a key on a security key | only `id_ed25519`, `id_ecdsa` and `id_rsa` in `~/.ssh` signed; such people's mail went out unsigned, so they could not take part in missions and a forgery in their name looked like their real mail | setup finds a key file, then a key that an ssh-agent holds (through `SSH_AUTH_SOCK` or the `IdentityAgent` of `~/.ssh/config`; the agent it notes is asked only while its socket is one of this user's), then a key on a security key, and `SYN_SIGNING_KEY` may name a `.pub`. Such a key may wait for an unlock or a touch, and a hook has seconds, so no hook waits for a key: in a hook only a key file signs, read without asking any agent; what the yes of a mission sends with another key waits in `~/.synchronauts/outbox` (mode 0600, each record sealed with `approve.key`) until the watcher has signed it, and is dropped once its mission has ended or is past its end time, at the latest after 24 hours; a command waits at most `SYN_SIGN_WAIT` seconds and says so; `mission end` and Stop end the mission here at once and queue the end in the same step, before the key is asked, so it waits in the outbox when the key does not sign it and when the command is interrupted or killed while it waits | a queued invite, join or end reaches the others only once the human unlocks or touches the key, so until then they still see the mission running; a plain message whose key did not sign in time still goes out unsigned (the command says so), and teammates who know the signature see it as forged; a security key that needs a PIN cannot sign |
| Stealing the board's key: from a file, the browser's storage, an address in the history or a `Referer`, the command line that opens the browser, or a `BROWSER` variable that prints the address | one key for good, kept in `~/.synchronauts/ui-key` and in the browser's `localStorage`, and handed over in the address (`#k=`) that `open` or `xdg-open` got in its command line | the key is new at every start of the board's server and lives only there and in the tab that paired (`sessionStorage`): no file, no lasting browser storage, never in an address. A tab pairs with a one-time code (16 characters of 32, valid once and for two minutes, in `ui-pair.json`, mode 0600) that the page posts to the server and removes from the address at once; the page and the server send no `Referer`, and `ui.log` gets neither code nor key. `syn ui` hands the address to the system's own opener named by its path (`open`, `xdg-open` in a system folder, the Windows shell), never through `BROWSER` as Python's `webbrowser` did (`BROWSER=echo syn ui` printed the code), and nothing the opener prints reaches the terminal | a program that runs as the user can read the code file and pair (see Not protected); while `syn ui` opens the browser, the code is in the command line of the program that opens it (`open`, `xdg-open` or the browser itself), where other users of the machine can see it (`ps`) until the page has used it: on a shared machine `syn ui --pair` prints the address to open by hand. `xdg-open` follows the desktop's settings for web addresses, which a program of the user can change. A tab that paired keeps its key until the server stops |
| Guessing the pairing code, or locking its owner out with wrong ones | no pairing; the key was long and fixed | the code has 80 bits and works once, for two minutes: a program that tries ten thousand codes a second finds it with a chance of about one in 10^18. So a wrong code locks nothing, and neither another user of the machine nor a website can keep the owner from pairing (a website can make the board's own page post a wrong code, by opening its address with one); a request with a foreign `Host` (DNS rebinding) or `Origin` (another website) is refused, and nothing ends a pairing that succeeded | a program on the machine can flood the board's server with requests, as it can any local server |
| Details in the board's errors: a traceback, an HTML page that repeats the request, the Python version in the `Server` header | a failure inside the server closed the connection and wrote a traceback with values to `ui.log`; Python's HTML error page repeated a broken request line; the `Server` header named Python and its version | a failure answers 500 `internal error`, and `ui.log` gets the method, the path, the kind of failure and where, no values; the server's own refusals (a broken request, another method) are short JSON without anything of the request; the `Server` header says `Synchronauts` | the page itself, which holds no secret, can be fetched by any program on the machine |
| Hidden characters on the board: a message with bidi overrides or zero-width characters that shows another text than it holds | the text of a message reached the board, `syn state` and `syn line` as written, because it is signed and must stay as it was | the board, `syn state` and `syn line` get every string without hidden and control characters, keys included; `others.json` keeps the signed text, so its signature still checks | letters of other scripts that look alike stay |

### Not protected

- A malicious room member who is also approved in a mission can send harmful signed instructions within the plan: the
  human approved that plan.
- Anyone who can run programs as the user can read the SSH keys, the board's pairing code (and so pair with the board)
  and everything in `~/.synchronauts`, `approve.key` included. That includes a Claude that runs code past the hooks (a
  script of its own, syn's own functions): paired, it can write on the board as the human, and teammates see such a
  message as written by the human in person.
- The human gate of missions is a hook, not a sandbox. A Claude that runs code outside the hooks, or a program that
  builds the approve call at run time, reaches the command without the prompt and can write into `~/.synchronauts`
  past the shell check (a script, a tool it does not know, a path computed at run time). Without `approve.key` such
  code can neither make a digest that fits nor seal a mission record, but code that runs as the user can read the key,
  and then it can do both. The files of the plugin itself (`syn.py`, the hooks, the launcher) are not guarded either:
  whoever changes them changes the gate.
- Size caps are the only protection against a room member who fills the room with data. Each line about a session is
  short, but a room member can write many sessions and branches, and their lines can push a warning or a message past
  what Claude Code shows of a hook's output.

### Known limits

Things that work as designed or as far as tested, so that nobody counts on more than there is:

- The check of unsigned mail against GitHub's record of pushes has been measured with the owner of a room: a push,
  forced or not, was in the record within two seconds, with the right account. Whether GitHub shows the record of a
  private room to an invited member is not tested yet; where it does not, setup says "Not signed yet" and names
  `syn key`.

- Look-alike names and logins are caught only by a best-effort table (case, accents, common Cyrillic and Greek
  letters, 1/l/I, 0/o, rn/m, vv/w); other look-alikes are not marked.
- File names in a conflict warning come straight from git's merge of a teammate's pushed commit and are not checked or
  shortened like the file names in a teammate's state.
- If the keys URL cannot be reached when a message is first checked, a message signed with a key that the sender added
  since syn last fetched their keys shows as forged for as long as it is kept (up to about a week).
- When your key does not sign a message sent from the board in time, the board does not tell you that it went out
  unsigned (`syn send` does), and teammates who know your signature see it as forged.
- Signing with keys held by 1Password, Secretive, the Windows OpenSSH agent or Git for Windows' agent, and with a touch
  on a security key, has been tested only with stand-ins, not with the real products.
- While `syn ui` opens the browser, the one-time pairing code is briefly visible to other users of the machine in the
  opener's command line; on a shared machine run `syn ui --pair` and open the address yourself.
- Edits made through Bash (a script, `sed -i`, a build tool) are seen only after the command, from a `git status`
  before and after it (1.5 s each; slower, or more than 3000 changed files: not tracked). A claimed file cannot be asked
  about beforehand, Claude is told afterwards. Ignored files, a command that changes into another repo and changes that
  arrive committed (`git pull`) are not seen. Only paths go to the room.
- The conflict check writes objects (a snapshot commit and merge results, referenced by no branch) into the `.git`
  folder of the work repository; they are unreferenced and removed by Git's own garbage collection.
- There is no `leave` or `uninstall` command yet. See the guide for removing the plugin by hand.

## Hardening checklist for a room

- Use a private repo and invite only people you trust; turn on two-factor authentication for every member.
- Keep the SSH key that signs for you on a hardware key or in an agent (syn finds a key that only an ssh-agent holds,
  and `~/.ssh/id_ed25519_sk`), and remove keys you no longer use from your account.
- `syn notify` tells you about forged mail and mission proposals even when the board is closed.
- On a machine that other people use too, run `syn ui --pair` in your own terminal and open the address it prints:
  `syn ui` hands the one-time code to the program that opens the browser, whose command line other users can see until
  the page has used the code.
- Do not put secrets in tasks or messages.

## Past advisories

None yet for 0.6.x.
