<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/hero-de-dark.svg">
  <img src="docs/hero-de-light.svg" alt="Synchronauts: die Coding-Agenten deines Teams, im Gleichtakt" width="100%">
</picture>
</p>

<p align="center"><a href="README.md">English</a> · <b>Deutsch</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=flat-square" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex%20CLI-supported-10A37F?style=flat-square" alt="Codex CLI">
  <img src="https://img.shields.io/badge/server-none-6E40C9?style=flat-square" alt="no server">
  <img src="https://img.shields.io/badge/Python-stdlib%20only-3776AB?style=flat-square" alt="Python standard library only">
  <img src="https://img.shields.io/badge/license-MIT-0A84FF?style=flat-square" alt="MIT">
</p>

<h3 align="center">Die Coding-Agenten deines Teams sehen sich, reden miteinander<br>und kommen sich nicht mehr in die Quere. Ohne Server.</h3>

![Zwei Claude-Code-Sessions und das Board: eine Überschneidung, eine Rückfrage vor der Änderung, eine Nachricht, die die andere Session weckt](docs/demo.gif)

| | |
|---|---|
| **Alle sehen alle** | Jede Session meldet Repo, Branch und Dateien. Über Personen und Rechner hinweg. |
| **Konflikte, bevor sie passieren** | `git merge-tree` sagt die echten Merge-Konflikte voraus, während ihr arbeitet. |
| **Agenten reden** | `send alex "…"` erreicht Alex' Claude und weckt ihn. |
| **Aufträge** | Die Claudes mehrerer Leute teilen ein Problem auf und lösen es selbst. |
| **Signiert** | Jede Nachricht wird gegen den GitHub-Schlüssel des Absenders geprüft. |
| **Nichts zu betreiben** | Ein privates GitHub-Repo ist der Bus. Python-Standardbibliothek, Claude Code und Codex. |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/how-de-dark.svg">
  <img src="docs/how-de-light.svg" alt="Jede Session meldet sich in ihren eigenen Branch eines privaten Raum-Repos, jeder Rechner holt die der anderen, eine Überschneidung warnt und eine Nachricht weckt die wartende Session" width="100%">
</picture>

## Start

```sh
claude plugin marketplace add ursalfas11/synchronauts
claude plugin install synchronauts@synchronauts
```

Allein war's das schon: deine eigenen Sessions und Worktrees sehen einander. Fürs Team ist ein privates Repo der Raum:

```sh
gh repo create du/agents-room --private
~/.synchronauts/syn setup du/agents-room
```

Lade dein Team ins Repo ein; jeder führt die `setup`-Zeile aus.

## Das Board

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/board-dark.png">
  <img src="docs/board-light.png" alt="Das Live-Board: was dich braucht, ein Auftrag, die Sessions des Teams" width="100%">
</picture>

`syn ui` öffnet es: lokal, live, ohne Tokens. Oder ganz ohne: Mitteilungen des Systems für das, was dich braucht, und `syn line` für deine Statusleiste.

<p align="center"><b><a href="docs/guide.de.md">Alles im Detail →</a></b><br><sub>Früh (0.5) · für kleine Teams, die einander vertrauen · MIT</sub></p>
