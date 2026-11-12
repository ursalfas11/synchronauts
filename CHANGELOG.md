# Changelog

All notable changes to Synchronauts. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This file is in English only; the README and the guide exist in English and German.

## [Unreleased]

## [0.6.0] - unreleased

### Security

- Missions are built from signed data only. The people and the end time are part of the signed invite (two new signed
  fields, `crew` and `until`; the end is capped at 7.5 hours after the invite was sent), and joins, ends and work
  messages count only as signed messages from the people of the mission. A branch in the room can no longer change or
  end a mission, fake that somebody joined, or put a mission in someone else's name. `state.json` no longer carries
  `missions`.
- A command can no longer slow the check of the hooks down until Claude Code's time limit lets it run unchecked. A row
  of backslashes in a string of code without its closing quote (`python3 -c 'system("\\\\…'`) doubled the time with
  every backslash, and a long word of globs before a `/` took the square of its length. Both are read in a time that
  grows with the length only.
- Only a valid signed proposal gets the instruction "Do what the proposal says" (tell the human the plan and run the
  approve command), which now adds that nothing the plan asks for comes before the yes. An unsigned, forged, expired,
  foreign or 0.5-style proposal is shown as information that cannot be joined, and only a signed message of the
  mission's people ends it or counts as work.
- A command can no longer pick the session a `syn` command works for. `syn send`, `task`, `claim` and `mission end`
  take it from `CLAUDE_CODE_SESSION_ID` (Codex: `CODEX_THREAD_ID`), so `CLAUDE_CODE_SESSION_ID=<id> syn send …` wrote
  as another session of the same human, with the mission mark of a session that joined one. The hooks now refuse a
  Bash command that sets either variable; reading it, or naming it as text, passes.
- A signed message names the room it was written for (new signed field `room`), on all mission mail; plain mail carries
  no room, so 0.5 peers still verify it. A copy played back in another room is shown as forged, and mission mail
  without a room does not count. The room id is the same for the https, ssh and scp form of one repo (on Azure DevOps too), an
  `insteadOf` rewrite and an ssh alias, fits any remote (a space or another character an id cannot carry is escaped),
  and survives a rename on GitHub (`syn rooms --refresh`, and the watcher once a day; a running watcher and board take
  the new id over at once).
- Copying the id of a real message onto a forged one cannot stop it any more: the copy whose signature verifies wins,
  the others never count. A message signed under an id that names another sender is forged, and copies that only write
  the signature differently are one message. Only when one sender signed two different texts under one id are both
  shown as forged.
- Four ways past the guard of `~/.synchronauts` are closed. A read whose file only the run names
  (`cat ~/.synchronauts/$(echo approve).key`) is refused, with a line that says to name the file in full. A Grep from a
  folder above it is refused unless a glob or a type keeps it to other files; before, only a glob that named a secret
  was. A command that names the folder and sets a variable that makes a tool run a program (`GIT_PAGER`,
  `GIT_EXTERNAL_DIFF`, `PAGER`, `BASH_ENV` and their kind) or uses `git grep -O` is refused. So is a program whose
  way with files the check does not know (`sed` with a script, `patch`, `yq -i`, `ruby -e`, an editor) when its words
  name the folder. Reading the logs and the state with `cat`, `tail`, `jq` or `wc` works as before.
- A mission proposal dated ahead of the clock of the machine that reads it (by more than five minutes) cannot be
  joined, and says why. The cap of 7.5 hours counts from the time in the invite, which its sender writes: dated a
  year ahead, the mission would have run a year. A time of another year is shown with its year.
- `syn status` marks the mail it lists as information, not instructions, and shows the first 300 characters of each
  message; the full text came with the message itself.
- The approval prompt of a mission is bound to what it showed: if plan, people or end time change between the prompt and
  the yes, the mission is not started.
- `mission approve` gets Claude Code's prompt only as the whole command, and only when syn itself runs it: the launcher `~/.synchronauts/syn` (by its path, or bare where PATH leads to it) or
  `syn.py`. Before, any command that contained the words got the prompt, and the yes let the rest of the line run too,
  or a program of its own named `syn`. Chained with another command, or hidden in a variable, `bash -c`, `eval`,
  `xargs`, a wrapper like `env` or `sudo`, a here-document or a script that git does not know unchanged, the command is
  now refused with the hint to run `syn mission approve <id>` alone. Plain text tools (`grep`, `cat`, `echo`,
  `git commit -m`, ...) may still name it unless what they print goes on into a file or a program, and a committed
  script may contain it.
- The yes counts only with the digest the approval prompt writes: an HMAC over the session, the tool call, the mission,
  its signed invite and what the prompt showed, with a key of this machine (`approve.key`, mode 0600, made by the first
  draft or approval, so an updated 0.5 installation gets one too). An `approving` record written by hand, or copied to
  another call, starts nothing, and `mission approve` refuses it as well.
- syn seals every record it writes into `missions.json` with the same key, and reads only sealed ones: a draft or a
  mission written there in another way counts for nothing. Records from before 0.6 have no seal; a mission that runs
  while you update must be proposed again (missions need 0.6 on every side anyway).
- The hooks guard `~/.synchronauts`: an edit tool (Edit, Write, MultiEdit, NotebookEdit, a Codex patch) or a shell
  command that writes there (a redirect, `tee`, `cp`, `mv`, `ln`, `rsync`, `tar x`, `unzip`, `curl -o`, `sed -i`, `rm`,
  `shred`, `touch`, `find -delete`, a write in `python -c` and the like, also through a link that the same command
  makes or copies, into a folder it may remove or make first, or an old link that `ln` without `-f` leaves; `git` that
  may change files there, also from a working tree above it, with `GIT_DIR` or `GIT_WORK_TREE` exported earlier in the
  command, `git clone` or `worktree add` into it; a container that mounts it; a target or code only known at run time
  in a command that names the folder, runs in it or may get there by a `cd` after the command may set `CDPATH` or
  `cdable_vars`, spelled in any way or by a name it builds from its own text; a name read from a file at run time, as
  in `export $(cat .env | xargs)`, does not count) is refused, and so is reading
  `approve.key` or the board's pairing code with a shell command (also by a glob, `{a,b}`, `grep -r`, `cp -r` or `tar`
  of the folder, or by running `syn ui --pair`, which prints it), or with Claude Code's Read, Grep or Glob (hooks.json now
  routes them to PreToolUse). For these reads the hooks do not look into a script that Claude wrote and then runs, and code that calls syn's
  own functions can still make and read a code (SECURITY.md).
- The checks of these hooks run within a budget (3 seconds, 16 levels of `${..}`, 64 scripts, 24 git calls, 5000
  folder entries) and refuse a command they cannot read in it, with the hint to split it up: before, a deeply nested or
  very long command could make the hook fail or time out, and the tool call then ran. A check, or the PreToolUse hook
  as a whole, that fails refuses a call that names the gate, `~/.synchronauts` or `ui --pair` and writes the error to
  `hook.log`; refusals are printed in ASCII, so that no character of a path in them can keep them from reaching Claude
  Code.
- A display name proves nothing: it is free text that anybody in the room can pick. Every message header now carries
  the sender's login (`Message from Sam's Claude (@sam-gh, from demo, 19:09)`), and wherever two people could be mixed
  up (the same or a look-alike name, a name that is another person's login, a name with a letter that is not plain
  Latin, from another script or like `ı` and `ø`) the board, `status` and Claude's texts show `Name (@login)`. A name
  written like a label stays plain text, and a login whose branches disagree about its name shows as the bare login.
  Claude reads a message from the board as written by the person ("in person") only when it is signed; the reply still
  goes back to the board.
- A login can be imitated in case or look: a branch in `Alice-gh` or `a1ice-gh` next to the real `alice-gh` is never
  merged with her. Each is a person of its own, marked `⚠ Alice (@a1ice-gh)`, its tasks and mail stay under its own
  login, and unsigned mail in another case of a login that signs is shown as forged. A person's line that a session
  has seen before such a clash comes again, marked.
- A branch in a case variant of a login could stop the sync on macOS and Windows, whose file systems ignore case, and
  push the real person out of the picture. Each branch is now fetched into a ref of its own (`refs/syn-in/`, every
  character but `a-z`, `0-9` and `-` escaped), and only when it changed; the refs of 0.5 under
  `refs/remotes/origin/syn/` are deleted, one by one where a pair that differs only in case cannot go in one step, and
  the room's remote has no fetch refspec any more, so a push no longer writes such a ref.
- File and claim names in someone else's state count only if they look like a path inside a repo: at most 240 characters
  of letters of any script (with their accents and marks), digits, at most four spaces and `. _ - + @ = , ~ # % ( ) [ ]
  $ /` (a claim also `* ?` and a final `/`), no `..`, no absolute path, drive letter or URL, no `~`, `-`, `$NAME` or
  `%NAME%` at the start, no `$(` or `${`, no hidden character. A name that does not fit is left out, not cleaned, also in
  the history; an own file with such a name is not published, so teammates do not see it and their sessions do not ask
  before editing it, and `syn claim` refuses such a name and says why, instead of a claim nobody else would see. Own file
  names are published with their accents composed (NFC), as another machine writes them. A teammate's task reaches
  Claude's context as one line of at most 120 characters (`status` shows 200) in which every `"` is written as `'`, so
  it cannot close its quotes, and the line about a teammate's session shows at most six claims and 400 characters of
  repos, branches and claims (`status` 1200), however many repos the session lists. The skill counts tasks, file names
  and claims of others as information, not instructions.
- `syn status` and the line about new mail that the human sees in the terminal mark mail to you whose signature does
  not check out `[forged]` and unsigned mail `[unsigned]`; `status` indents the further lines of a message, so a line
  break in it cannot start what looks like a line of its own.
- The board picks one message per id the way the hooks do: the copy that verifies wins, and differing copies without
  one are shown as forged, also when the copy that wins is a mission message; before, the branch read last won.
  Unsigned mail gets a mark, and signed mail between two others is marked "not checked" instead of unsigned, because
  the board does not check it. Only mail written on this machine shows as yours: mail in a branch of your login that
  somebody else wrote keeps its marks, the forged warning included.
- Hidden characters are stripped more completely from other people's texts: the soft hyphen, the combining grapheme
  joiner, the Arabic letter mark, the Hangul fillers (letters that show as nothing, so a branch or a name with them read
  like words with spaces), the invisible Khmer vowels, the Mongolian variation selectors and vowel separator and the
  line and paragraph separators are now removed together with the zero-width and direction characters; a branch or a
  file name with one is left out.
- The keys a keys URL publishes for a login are read with limits: at most 50 key lines, none longer than 1000
  characters, so a keys server cannot feed unbounded text into the signature check.
- An error message that quotes a URL with a user and password in it (`https://user:token@host`) loses them before it
  reaches `errors.json`, the watcher's log, the board, `status` or Claude's context. A keys URL that cannot even be
  read as one counts as a keys URL that cannot be asked, instead of stopping the check of all mail.
- Until the watcher has checked it, a copy that somebody changed under the id of a message you already have shows as
  forged if it is unsigned in the login of somebody who signs (the check finds the same), otherwise as unsigned; before,
  always as unsigned.
- Folders under `~/.synchronauts` are created with mode 0700 from the top down (`git/` and `sessions/` included), also
  when the first thing written is a file deep inside; before, only the last folder got that mode until the next command
  repaired it.
- The board's key is new at every start of its server and lives only there and in the tab that paired with it
  (`sessionStorage`): it is no longer kept in `~/.synchronauts/ui-key`, which `syn ui` removes, or in the browser's
  lasting storage, and it never appears in an address. `syn ui` pairs the browser with a one-time code (16
  characters, 80 bits, valid once and for two minutes, in `ui-pair.json`, mode 0600) that the page swaps for the key at
  `/api/pair` and removes from the address at once. A wrong code locks nothing, so neither another user of the machine
  nor a website can keep you from pairing; 80 bits are not guessed in two minutes. Requests with a foreign `Host` or
  `Origin` cannot pair. Boards opened before the update say "not paired" once: run `syn ui`.
- `syn ui` opens the browser with the system's own opener, named by its path (`open` on macOS, `xdg-open` from a system
  folder, the Windows shell), and no longer follows the `BROWSER` variable as Python's `webbrowser` did: a command
  could point it at a program that prints the address with its code (`BROWSER=echo syn ui`). Nothing the opener
  prints reaches the terminal. Where no browser opens (no display, or `xdg-open` only outside the system folders),
  `syn ui` says to run `syn ui --pair` in your own terminal.
- The board, `syn state` and `syn line` get everything without hidden and control characters, the text of messages
  included, which stays as it was signed in the room. A failure inside the board's server answers `internal error`
  without details (`ui.log` gets the request, the kind of failure and where, no values), the server's own refusals (a
  broken request, another method) are short JSON instead of an HTML page that repeated the request, the `Server`
  header no longer names the Python version, and the page sends no `Referer`.
- The guards of `~/.synchronauts` and of the mission gate also hold in runs without a human (`claude -p`, the SDK).
  Before, every hook was off there, so a session could start `claude -p` and have it read `approve.key` or rewrite the
  state. Such a run still reports nothing and gets no notices; `mission approve` is refused in it, since nobody can
  say yes.
- A login that signed once no longer makes unsigned mail in its name forged for good. `signers.json` keeps the time of
  each login's last good signature, and unsigned mail counts as forged only in the name of a login that signed within
  the last 30 days: somebody who moved to a machine without a key shows as unsigned again after that. While another
  machine of theirs still signs, it stays forged, in a room on GitHub the record of pushes decides before that, and
  `syn key` gives the machine a key. The price: 30 days after a login's last signature, a forged unsigned message in
  its name shows as unsigned, not as forged. The notification for forged mail no longer speaks of a signature that
  does not match, since unsigned mail has none.
- The keys URL is asked anew at most once per login in ten minutes; before, every message whose signature fitted no
  cached key asked it again. Until then such a message has no verdict (unsigned, checked again), which does not hold up
  the sender's other mail.

### Added

- Edits made through Bash are tracked. The hooks compare the changed files of the repo (`git status`, 1.5 s at most,
  read-only, ignored files left out) before and after each Bash command, and what the command changed counts like an
  Edit or Write: it enters the session's file list and the overlap warnings. A command cannot be asked about before it
  runs, so when it changed a file somebody claimed, Claude is told afterwards. Slow `git status` or more than 3000
  changed files: that call goes untracked silently, and the repo is left alone for ten minutes, so that in a huge repo
  one command waits and not every one. Not seen: other repos entered by `cd`, ignored files, committed changes, a
  command that runs in the background. Only paths go to the room.
- An invitation finds its way. On a machine without a room, a session start looks in the background (through `gh`, at
  most once an hour) whether GitHub holds an invitation to a room for the account, and the next prompt tells Claude
  and you who invites you to which room. Claude joins after your yes, never on its own: anybody on GitHub can send such
  an invitation, and a room sees what your sessions work on. `SYN_INVITES=off` turns the look off.
- No key is needed in a room on GitHub. GitHub records which account pushed what, forced pushes too, and a recipient
  now checks the sender of a message without a signature against that record: the message is the sender's when their
  account pushed it, and forged when another account did, which the warning names. Missions work that way as well,
  and a second machine without a key no longer makes its owner's mail show as forged. Setup says "No key needed"; it
  names `syn key` only for a room on another Git host, or when GitHub does not show the account the record.
  Signatures stay and count as before.
- One sentence sets a team up. `syn setup <owner/repo> --invite <login>` makes the room if it is a repo of your own
  account and not there yet, joins it, invites the teammates and says how they join; before, the room and each
  invitation were `gh` lines of their own. A room that is public is named with a warning.
- `syn key` makes a key of this machine for signing only (`~/.synchronauts/signing-key`) and adds it to your GitHub
  account as a signing key, which can sign and cannot log in. Setup now says when no key signs ("Not signed yet") and
  names that command; before, a machine without an SSH key on GitHub sent unsigned without a word. Keys that GitHub
  lists for signing only count like the ones that log in, for your own messages and for checking others'. The hooks
  keep Claude's tools away from the new key file like from the other secrets.
- `syn rooms [--refresh]` prints the room id that signed mission mail carries and finds it out again after the repo was
  renamed or moved.
- `syn ui --pair` prints the board's address with a one-time pairing code, for a browser that `syn ui` cannot open (on
  another machine through a port forwarded under the same number, `ssh -L 7962:127.0.0.1:7962` for the port it
  prints, since the board answers only to its own address; or on a shared machine, where the code should not pass
  through the command line of a browser launcher). It is for the human's own terminal: the hooks refuse it to Claude,
  since the key it leads to lets a page write as the human. Without a browser to open, `syn ui` points to it.
- Signing works with a key that only an ssh-agent holds (1Password, Secretive: the agent that `SSH_AUTH_SOCK` names, or
  the `IdentityAgent` that `~/.ssh/config` sets for github.com), with a key on a security key (`~/.ssh/id_ed25519_sk`,
  `id_ecdsa_sk`, a touch for every message) and with `SYN_SIGNING_KEY` naming the `.pub` file of a key in an agent.
  `setup` looks in that order, a key file first (it signs without asking), and notes the kind of key and its agent in
  `signing.json`; the noted agent is asked only while its socket is one of yours, and when it is gone or dead, syn asks
  the agents it finds now. An agent that cannot be asked right now does not lose the noted key. Such signatures verify
  on 0.5 peers as well.
- `SYN_SIGN_WAIT` (30 seconds, 1 to 300): how long a command, the board and the watcher wait for such a key to sign. A
  command prints "Waiting for your SSH key" before it waits, and `send` says when the key did not sign in time and the
  message went out unsigned, with what to do for that kind of key. When the watcher stops, a question to the key that
  it still waits for ends with it.
- `SECURITY.md` (supported versions, how to report a problem, threat model), `CONTRIBUTING.md`, this changelog, issue
  and pull request templates, Dependabot for the GitHub actions.
- Guide: a Settings section with every `SYN_*` variable (EN and DE), and the statement that the room has no private
  messages: every room member can read every message, also those addressed to someone else.
- A code of conduct (`CODE_OF_CONDUCT.md`), and a place for questions: the issue form links to the discussions.
- Development: `test/measure.py --check test/budget.json` fails when a hook text grows beyond its budget; the end-to-end
  test checks the documents (versions, English and German in step, links, settings, no company data, no hidden or
  direction character written as such in any file) and can run in two shards (`SHARD=a|b`).
- `syn --version` prints the installed version and `syn --help` the commands with a line each, both with exit code
  0 and without touching `~/.synchronauts`. The bug report form asks for the version that way.
- `syn leave` and `syn uninstall`. `leave` takes this machine out of its room: it deletes its own branch there (only
  at the commit it just read; when the room is out of reach it still leaves and says that the branch stays), stops the
  background service and the board, deletes the local copy of the room, drops the queued mail and says how many, and
  keeps the name and the signing key; the sessions here go on alone. A running mission stops it unless `--force`.
  `uninstall` leaves, removes the hooks `syn codex` wrote and the folder `~/.synchronauts`, and only a folder it can
  tell is its own: it refuses the root, your home folder, a link, a relative path, a folder with a file of someone
  else, and prints what is still yours to do (`claude plugin uninstall synchronauts`, the key on GitHub). Both ask in
  a terminal and need `--yes` elsewhere, and Claude Code asks before a Bash call of either.

- The room cleans itself up. A machine deletes the branches of its own login that no machine pushed to for 30 days
  (at setup and when the watcher starts; a machine that comes back simply pushes again), and never a branch of
  somebody else. Branches of other people that old no longer take part in the names, the look-alike check or the
  picture. When the room has more than 300 branches, those of the own login are read first, and the watcher reports
  how many were not read (`status`, the board) instead of dropping the logins late in the alphabet without a word. The
  room's git folder on each machine prunes the loose objects of every push after an hour, not after two weeks.

### Changed

- The install is one command, `claude plugin install synchronauts --marketplace ursalfas11/synchronauts` (Claude Code
  2.1.292 or newer; the guide keeps the two commands for an older one), and the first session start after it tells
  you in one line that Synchronauts is on and what a team does next. The line is for you, Claude gets none of it. If
  Python does not start or is older than 3.9, the session start says that instead of failing without a word.
- `setup` names the next step where it used to print git's words: without the GitHub CLI it says to install it and
  to log in, a room that is missing or that your account may not read gets the command its owner invites you with
  (GitHub answers "not found" for both), a git that cannot log in to GitHub gets `gh auth setup-git`, and a name that
  is no repo is told how a room is named.
- The README's Start section works as written: it names what you need, says to restart Claude Code and that
  `~/.synchronauts/syn` exists once a session has started, shows the line that invites a teammate, and says in three
  sentences what the room sees. Commands carry their full path, and a line says that the project is not affiliated
  with Anthropic or OpenAI.
- The conflict check no longer writes into your repo. Its snapshot and merge objects go into a temporary folder under
  `~/.synchronauts` that is deleted after each run, and the commits it fetches from teammates into
  `~/.synchronauts/conflict-objects` (emptied after a day or at 100 MB); no object and no ref is added to the work
  repository's `.git`. It also compares two separate clones of one repo on the same machine now, not only worktrees.
  Objects that earlier versions left in a repo stay there until `git gc` removes them.
- **Breaking:** the board's key is no longer in `~/.synchronauts/ui-key` (`syn ui` deletes the file) or in an address
  (`#k=`); a script that read it to call the board's API stops working. Use `syn state` for the board's data, and
  `syn ui` or `syn ui --pair` to pair a browser.
- **Breaking:** missions need 0.6 on every side. A 0.6 invite is shown as a forged message by 0.5, and 0.5 invites and
  mission messages are information only for 0.6; update everybody in the room. `state.json` no longer contains
  `missions`.
- The version is 0.6.0. The longest mission is one constant (7.5 hours) that the documents quote and a test checks.
- `send` and `mission propose --with` take a login only as written exactly (`@sam-gh` works too) and refuse a name
  that fits more than one person, or a login written in another case (the real one may not have joined yet), listing
  who it could be and telling Claude to ask its human which login is meant; before, `send` went to everyone the name
  fitted and `--with` took the first. The confirmation of `send`, the draft and the approval prompt of a mission name
  each person with the login (`Ready for Sam (@sam-gh)`, `Join Sam (@sam-gh)'s mission`). The skill tells Claude to
  ask its human when a name is ambiguous.
- No hook waits for a signing key any more. In a hook only a key file signs, within 3 seconds, read by `ssh-keygen`
  without asking any agent, so an agent in `SSH_AUTH_SOCK` that hangs cannot hold it up. With a key in an agent, on a
  security key or with a passphrase, the invite or the join that the yes of a mission sends waits in
  `~/.synchronauts/outbox` (mode 0600, each record sealed with `approve.key`) until the watcher has signed and posted
  it, and Claude is told that it is queued; while the key does not sign, the watcher asks it again a few seconds after
  each try. A record that syn did not seal, one whose mission has ended or is past its end time, and one not signed
  within 24 hours are dropped with a line in the watcher's log and in `outbox/dropped.log`, so a late invite cannot
  start an ended mission again. A session start that joins the room leaves the search for a key in an agent to the
  watcher.
- `mission end` and Stop on the board end the mission on your machine at once and put the end into the outbox in the
  same step, before the key is asked; it leaves the outbox once it is signed and posted. When a signing key does not
  sign the end in time, or `mission end` is interrupted or killed while it waits for the key (Ctrl-C, a closed
  terminal, a timeout), the end waits there like a queued invite and the watcher sends it; the command or the board
  says that the others learn it once the key signs. Before, the end went out unsigned, counted for nobody, and the
  mission was over on your side only.

- `send` says how the message arrives: "Waiting, will be woken" for a session that waits, "At work, gets it with the
  next step" for one that is working, and "Sees it at its next prompt" with the reason (Codex, wake window over, no
  open session) for the rest, so a Claude does not wait for an answer that cannot come. `status` marks each teammate's
  session the same way. The board and `send` decide it by one rule.
- `status` says when no room is set up, and shows mail that waits in the outbox for a signature and mail that was
  dropped in the last 3 days; `syn state` carries both as `outbox`.
- Exit codes: 2 for a wrong call (a missing argument, an unknown command, a value that is not allowed), with the usage
  of that command instead of the list of all, also before a room or a session is looked at, and 3 for `send` and
  `mission end` when the message is written but not uploaded yet; 1 stays for a call that could not be done. `--help`
  lists them.
- `claim` refuses a claim over the 30 a session may hold in a repo and says which ones, with exit code 1; it used to
  cut the list in alphabetical order without a word, which could drop a claim that was there. A task noted with `task`
  outside a session is taken only by a Bash hook in the same folder within 10 seconds, no longer by whichever session
  runs a command next.

### Fixed

- `syn codex --remove` no longer creates `~/.codex/hooks.json` when there is none and leaves a file without hooks of
  Synchronauts as it is; it says "No Synchronauts hooks in …". A hooks file that is valid JSON of another shape stops
  `syn codex` with a sentence instead of a traceback, and is not rewritten.
- On Windows a state file that another process replaced at that moment read as empty: a teammate's name fell back to
  the login, a session could miss from the picture for one hook. Such a read is tried again for up to half a second.
- A harmless command that names `mission` and `approve` (a `sed`, a `curl`, a script that holds both words) is still
  refused, since the guard cannot tell it from a hidden approval, but the refusal now says so and that the human can
  run it in their own terminal; before, it only said that `mission approve` must be the whole command.
- Two sessions with a detached HEAD in one repo no longer count as being on the same branch: git names every
  detached HEAD `HEAD`. A session in a repo without a commit shows up now, with the branch its first commit will be
  on; before, it did not show at all.
- The conflict check missed an edit made in the same second as the last `git add` or commit when it left the file's
  size as it was: the snapshot worked on a copy of the index with the time of the copy, and git then trusts the file's
  time and size instead of reading it. The copy keeps the index's time now.
- A clock that is off no longer makes mail vanish without a word. Mail dated up to a day ahead of the clock here is
  delivered with the note "dated ahead: a clock is off"; before, anything more than ten minutes ahead was left out.
  The machine whose clock is off learns it: the background service compares the clock with the time of GitHub's
  answers, and `syn send` and `syn status` say when it is more than five minutes off. A session stamp more than a day
  ahead counts as old, so a branch with a time in the far future no longer keeps a session active for good.
- Two machines of one person with the same host name no longer write the same branch. Each push is forced, so they
  overwrote each other every few seconds without an error. A machine name that setup takes from the host name now gets
  a short random ending when the room has a branch of that name already; the name is kept in `config.json`.
- The board says when a message went out unsigned, and why (no key on this machine, a security key nobody touched, an
  agent that is gone); it only said "Ready". `syn send` says it too on a machine without any key.
- An unsigned message from somebody who signs is still shown as suspicious, and now says what it is: no signature at
  all, which a forger leaves out and a second machine without a key does too (`syn key` there mends it). Before, the
  text spoke of a signature that does not check out.

- `hooks/hooks.json` routes Claude Code's Read, Grep and Glob to PreToolUse, so that the refusal of reads of
  `approve.key`, `ui-pair.json` and `ui-key` really happens (before, only a test that called the hook directly saw
  it). A read of any other path passes at once and prints nothing; PostToolUse is unchanged.
- The board's "Human" badge shows only on your own mail or on mail whose signature checks; before, any message with the
  field `source` set to `ui` got it, and any room member can set that field.
- Several writers of the same file at once (the board's threads, the signature checker) no longer collide on one temp
  file name: every writer has its own.
- The watcher finds its way back after trouble with GitHub. After a fetch that failed it asked with the old ETag, got
  "nothing changed" and left what the fetch missed missing until somebody pushed again; it now asks without the ETag.
  When the API says no (a token that ran out or has no SSO for the owner, the rate limit, a 5xx) it asks git itself
  with `ls-remote` and tries the API again five minutes later, instead of failing every five seconds. It asks for 100
  branches per answer instead of GitHub's 30, so a room with more than 30 branches keeps the cheap polls.
- `setup` no longer drops the other settings in `config.json` (for example `notify off`) when it rewrites the file.
- A setting that takes a number (`SYN_TICK`, `SYN_IDLE`, `SYN_WAKE_MIN`, `SYN_CONFLICT_TICK`, `SYN_UI_PORT`) and gets
  something else, such as `30s`, counts as its default; before, every hook and command stopped at start.
- A stamp without a time zone, or ending in `Z`, in someone else's state no longer breaks the comparison with the
  clock; it is read as UTC.
- A branch could stop the sync of the whole room with a lone surrogate (a `\ud800` escape) in a text, which cannot be
  written as UTF-8, and the hooks of everybody in a shared repo with a stamp of the year 9999 or 1, which local time
  cannot show. A text now loses such a character, a message that holds one is left out, a branch that still holds one
  is left out alone, and a stamp of someone else counts only between the years 2000 and 2100.
- Temp files of a writer that was killed half way are removed at the next session start.
- A real signed message no longer shows as forged because the signature could not be checked. An `ssh-keygen` that
  does not start or does not end in time (a machine under load) gives no verdict, and neither does one that says no
  to a known good signature too (older than OpenSSH 8.2): the message shows as unsigned and is checked again a
  minute later, and the board and `status` say that this machine checks no signatures. Before, such a message was
  kept as forged for eight days.
- Without a room, a session start no longer waits 5 seconds and `status` 8 seconds for a fresh poll of the watcher,
  which never runs without a room.
- Checking the signatures of new mail no longer holds up the sync. The watcher checks them in a thread of its own,
  outside the lock of the room's git folder, so a slow keys URL (GitHub or `SYN_KEYS_URL`) delays neither the push of
  your own messages nor the fetch of the others' branches, and a hook or command that asks for a fresh poll waits for
  the check of the mail it fetched three seconds at most; `setup` asks the keys URL outside that lock too. A keys URL
  that cannot be asked holds up a check once per sender, not once per message; such signed mail shows as unsigned and
  is checked again a minute later. A keys URL that answers 404 for a login (on GitHub: no such account) lists no keys
  for it, so signed mail under that login shows as forged at once instead of being asked about every minute. While the
  keys URL cannot be asked, the watcher looks for the own signing key again every hour, as it was meant to (before,
  only after a day).

- Fewer notes that nobody needs. Two machines on the default branch (the one `origin/HEAD` names, otherwise `main`
  or `master`) are in the same repo, no longer warned about "the same branch": everybody is on it. Two sessions of
  one machine there still are, they share a checkout. A teammate's change of task no longer puts a new line into
  every other session, and after the first picture a session hears only of sessions in the repos it works in or its
  prompt names; `status` and the board show the rest.
- A merge conflict is told to the session that touched one of its files: a file it edited, or one its checkout
  changed and has not pushed yet. Two branches that changed the same README weeks ago no longer warn every new
  session in the repo; the board keeps showing every conflict. System notifications follow the same rule. File names
  with letters outside ASCII show as they are, not as `\303\234`.
- A mission can be ended when the session that joined it is gone (closed, a crash, `/clear`). `mission end` works in a
  plain terminal for the one live mission of this machine, or with `mission end --id <id> "<result>"`; a Claude session
  that is not in the mission must name it, and may end it only when no session of this machine in it still runs. A
  shell of Claude Code without its session id is refused. Before, such a mission ran to its end time. `mission end`
  without a result or with `--id` alone is a wrong call (exit 2); exit 3 is unchanged.
- The others now learn that a person left a mission: when the last session of a person in it ends (also `/clear`), a
  signed `left` message goes out through the outbox, and the others' Claudes are told, so they stop sending mission mail
  to nobody; messages to that person are plain mail until a session joins again with `mission approve <id>` and the
  person's yes. That includes the proposer, who was refused before ("already approved"). Sessions of one machine count
  together: nothing is announced while another one is still in the mission.
- A lost, deleted or replaced `approve.key` no longer makes records vanish silently. `status` and the next session
  start say that mission records and queued messages cannot be verified, name the missions and why, and what to do;
  the records stay in `missions.json` (the old key brings them back), `mission propose` and `approve` say it too, and
  a mission of yours that the key no longer seals can still be ended with `mission end --id`. Before, the records
  counted for nothing without a word and the next mission erased them. Nothing without its seal is accepted.
- A session with a detached HEAD no longer reports the default branch at origin as the work it pushed.

### Compatibility

How 0.6 and 0.5 peers in one room get along.

| Feature | 0.6 sender to 0.5 receiver | 0.5 sender to 0.6 receiver |
|---|---|---|
| Presence, files, claims, plain mail, board data | works | works |
| Missions: invite, joined, end, mission work messages | 0.5 shows them as forged (it cannot verify `crew`, `until` and `room`) | information only: a 0.5 invite has no people and no end time, so it cannot be joined |
| Missions: `left` (the last session of a person ended) | 0.6 builds from before it drop `left` as an unknown kind: the person stays listed in the mission until its end; 0.5 shows it as forged like all mission mail | does not occur: 0.5 sends no missions |
| Mail signed with a key in an ssh-agent or on a security key | works: the signature is the same `ssh-keygen -Y sign` as from a key file | does not occur: 0.5 signs with key files only |
| File and claim names with a `:`, a quote, a shell sign, more than four spaces, over 240 characters or a start like `~`, `-` or `$NAME` | 0.6 does not publish them, and `syn claim` refuses them | 0.6 leaves them out: such files and claims of a 0.5 teammate do not show |

### Upgrade notes

- Missions need 0.6 on every side. Update everybody in the room before the next mission.
- Restart running Claude Code sessions after the update, so that the new hooks load.
- Open the board with `syn ui` once after the update: a tab or the installed app from before says "not paired". After
  every restart of the board (also the one after 30 minutes without a request), `syn ui` opens it paired again.

## [0.5.0] - 2026-11-03

Security fixes and the board as an installable app.
