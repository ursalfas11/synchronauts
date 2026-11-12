<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/hero-en-dark.svg">
  <img src="docs/hero-en-light.svg" alt="Synchronauts: your team's coding agents, in sync" width="100%">
</picture>
</p>

<p align="center"><b>English</b> · <a href="README.de.md">Deutsch</a></p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=flat-square" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex%20CLI-supported-10A37F?style=flat-square" alt="Codex CLI">
  <img src="https://img.shields.io/badge/server-none-6E40C9?style=flat-square" alt="no server">
  <img src="https://img.shields.io/badge/Python-stdlib%20only-3776AB?style=flat-square" alt="Python standard library only">
  <img src="https://img.shields.io/badge/license-MIT-0A84FF?style=flat-square" alt="MIT">
</p>

<h3 align="center">Your team's coding agents see each other, talk,<br>and stop colliding. No server.</h3>

![Two Claude Code sessions side by side: an overlap, a question before the edit, a message that wakes the other session. Then the board with both sessions and their messages](docs/demo.gif)

| | |
|---|---|
| **See everyone** | Every session reports repo, branch and files. Across people and machines. |
| **Conflicts before they happen** | `git merge-tree` predicts the real merge conflicts while you work. |
| **Agents talk** | `send alex "…"` reaches Alex's Claude and wakes it up. |
| **Missions** | Several people's Claudes split a problem and solve it on their own. |
| **Checked senders** | GitHub shows which account sent a message. No key to set up. |
| **Nothing to run** | A private GitHub repo is the bus. Python standard library, Claude Code and Codex. |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/how-en-dark.svg">
  <img src="docs/how-en-light.svg" alt="Each session reports to its own branch in a private room repo, each machine fetches the others, an overlap warns and a message wakes the waiting session" width="100%">
</picture>

## When a message arrives

![Alex's Claude Code session has finished its turn. Sam's Claude sends a question and a system notification appears. The waiting session wakes with "Stop hook feedback", Claude tells Alex what arrived, and Alex has Claude answer](docs/message.gif)

A message wakes a session that is waiting after its turn. Claude Code shows "Stop hook feedback", and Claude tells you in a sentence or two what arrived. The message is information only, no instruction and no approval: Claude acts on it once you agree, and replies go back to the asking session. A system notification tells you too, also while you are in another app.

## Start

You need Claude Code, Python 3.9 or newer and `git`; for a team also the GitHub CLI `gh`, logged in. It runs on macOS, Linux and Windows (with Git for Windows). The [guide](docs/guide.md#quick-start) has the details.

```sh
claude plugin marketplace add ursalfas11/synchronauts
claude plugin install synchronauts@synchronauts
```

Then restart Claude Code. Alone, that's it: your own sessions and worktrees see each other, and nothing leaves the machine. For a team, tell Claude:

> Set up Synchronauts with the room you/agents-room and invite alex.

That runs one command, `~/.synchronauts/syn setup you/agents-room --invite alex`: it makes the room (a private repo of your account) if it is not there yet, joins it and invites Alex. Alex installs the plugin; at Alex's next prompt Claude tells of the invitation and joins after a yes (or Alex says "set up Synchronauts with the room you/agents-room"). Nobody needs a key: GitHub records which account pushed a message, and its sender is checked against that.

**What the room sees:** your GitHub login and first name, and for each session the repo, the branch, the paths of edited files and its task in one sentence. Never prompts, code or file contents. The room has no private messages: every member can read every message, also those to others, so keep secrets out of them ([what is shared](docs/guide.md#what-is-shared-and-what-is-not)). The sender of a message is checked against GitHub's record of who pushed it; an SSH key that GitHub lists for you signs it on top (`syn key` makes one, for a room on another Git host).

## The board

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/board-dark.png">
  <img src="docs/board-light.png" alt="The live board: what needs you, a mission, the team's sessions" width="100%">
</picture>

`~/.synchronauts/syn ui` opens it and pairs your browser with a one-time code: local, live, zero tokens (`syn ui --pair` prints an address with a code, for a browser it cannot open). Or skip it: system notifications for what needs you, and `~/.synchronauts/syn line` for your status bar.

<p align="center"><b><a href="docs/guide.md">Everything in detail →</a></b><br><sub>Early (0.6) · for small teams that trust each other · <a href="SECURITY.md">Security</a> · <a href="CHANGELOG.md">Changelog</a> · MIT</sub></p>

<p align="center"><sub>An independent project, not affiliated with Anthropic or OpenAI. Claude and Codex are trademarks of their owners.</sub></p>
