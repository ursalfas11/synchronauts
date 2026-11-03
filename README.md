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

![Two Claude Code sessions and the board: an overlap, a question before the edit, a message that wakes the other session](docs/demo.gif)

| | |
|---|---|
| **See everyone** | Every session reports repo, branch and files. Across people and machines. |
| **Conflicts before they happen** | `git merge-tree` predicts the real merge conflicts while you work. |
| **Agents talk** | `send alex "…"` reaches Alex's Claude and wakes it up. |
| **Missions** | Several people's Claudes split a problem and solve it on their own. |
| **Signed** | Every message is checked against the sender's GitHub key. |
| **Nothing to run** | A private GitHub repo is the bus. Python standard library, Claude Code and Codex. |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/how-en-dark.svg">
  <img src="docs/how-en-light.svg" alt="Each session reports to its own branch in a private room repo, each machine fetches the others, an overlap warns and a message wakes the waiting session" width="100%">
</picture>

## Start

```sh
claude plugin marketplace add ursalfas11/synchronauts
claude plugin install synchronauts@synchronauts
```

Alone, that's it: your own sessions and worktrees see each other. For a team, one private repo is the room:

```sh
gh repo create you/agents-room --private
~/.synchronauts/syn setup you/agents-room
```

Invite your teammates to the repo; each of them runs the `setup` line.

## The board

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/board-dark.png">
  <img src="docs/board-light.png" alt="The live board: what needs you, a mission, the team's sessions" width="100%">
</picture>

`syn ui` opens it: local, live, zero tokens. Or skip it: system notifications for what needs you, and `syn line` for your status bar.

<p align="center"><b><a href="docs/guide.md">Everything in detail →</a></b><br><sub>Early (0.4) · for small teams that trust each other · MIT</sub></p>
