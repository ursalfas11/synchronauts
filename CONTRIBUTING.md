# Contributing

Thank you for helping. Synchronauts is small on purpose: one script, no dependencies, no server.

## Run the tests

```sh
bash test/e2e.sh
```

It needs `git`, OpenSSH (`ssh-keygen`), Python 3.9 or newer and `bash`; on Windows run it in Git Bash. It plays two people
and a second machine through with a local bare repo instead of GitHub. Output is one `ok` line per check; the first
`FAIL` stops it and prints what it saw. `KEEP=1` keeps the temp folder, `TIMES=1` prints how long each block took.

Two shards exist for slow CI runners: `SHARD=a bash test/e2e.sh` and `SHARD=b bash test/e2e.sh` together run everything,
and the document and repo checks run in both. The CI runs the whole suite unless a job gets slow (more than 12 minutes).
A new test block says in its first line which shard it belongs to (`if block a 'title'; then`), and a block that does
not depend on the others goes to the lighter shard.

No fixed `sleep` in a test: wait with `until_ok`. Every forged branch is deleted again with `git update-ref -d`. On
Windows avoid `touch -d`, `kill -0` on foreign processes and `sed -i`; pass JSON through Python, wrap captured output in
`crlf_safe`, and run every check on file modes or process ids through `posix_only`, which prints a stable
`ok skipped:` line there.

## The token budget

Hooks write text into Claude's context, and every token of it is paid for in every session. `test/measure.py` plays the
typical flows and prints how many characters each one costs; `test/budget.json` holds the ceiling per flow.

```sh
python3 test/measure.py --check test/budget.json syn.py skills/synchronauts/SKILL.md
```

fails when a flow is over its ceiling, when a flow has no entry or when an entry has no flow. The labels in
`measure.py` are stable names: do not reword one without changing the budget file. Raise a ceiling only with a reason in
its `why` field, in the pull request that needs it. `SKILL.md` has one allowance for the whole release (`skill_md`).

## Rules for the code

- Python standard library only, and Python 3.9 syntax: no `match`, no `X | Y` types at runtime, no walrus, no
  `zip(strict=)`, no `datetime.fromisoformat` except inside `parse()` (it rejects a trailing `Z` before 3.11).
- It runs on macOS, Linux and Windows (Git Bash): bytes to git, `python` on Windows and `python3` elsewhere, UTF-8 on
  every stream, never `os.kill(pid, 0)` on Windows.
- Everything from the room is untrusted. New code that reads other people's state goes through `tidy()`; a new signed
  field is added to `SIGNED`, to the mail whitelist of `tidy()` and is covered by `seal()` in the same change.
- Text that hooks write is English and as short as it can be.
- Folders under HOME are made with `private_dir()`, secrets are written with `private_write()`.
- Example names are `sam`, `alex`, `jule`, `kim`, `acme`, and `mal-gh` for an attacker. No company data and no e-mail
  address anywhere in the tree; a test looks for them.

## Documents

The README and the guide exist in English and German and must stay in step: the same headings, the same commands, the
same `SYN_` variables. A test checks that, and that every link and anchor resolves. `CHANGELOG.md`, `SECURITY.md` and
this file are English only. Every change a user can see gets one bullet in the `[Unreleased]` or current section of the
changelog, and every new `SYN_` variable goes into the Settings section of both guides.

## Pull requests

Describe what changes and why, paste the output of the budget check if a hook text changed, and tick the list in the
template. Security problems go to `SECURITY.md`, not to an issue.

## Release checklist

1. Version in `syn.py`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the footers of both READMEs, the
   status line of both guides and the heading in `CHANGELOG.md`; the e2e test checks that they agree.
2. `bash test/e2e.sh` green on the whole CI matrix, budget check green.
3. Screenshots and the demo GIF checked against the board.
4. Tag `v<version>` and publish the release by hand.

## Ideas not done

A `bin/` wrapper for the Bash tool's PATH (the fixed `~/.synchronauts/syn` path is in every hook text), a release
workflow, CodeQL.
