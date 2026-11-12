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

**Zwei Leute, sechs Claude-Code-Sessions, eine Codebasis.** Jeder Agent arbeitet, als wäre er allein. Also bauen zwei dasselbe Feature von zwei Seiten oder schreiben dieselbe Datei um, und ihr merkt es erst beim Merge.

Synchronauts ist ein Plugin für Claude Code (und Codex CLI), das die Sessions deines Teams verbindet. Jeder Agent weiß, wer an welchem Repo, auf welchem Branch und an welchen Dateien arbeitet. Bevor Claude eine Datei ändert, an der die Session eines Kollegen gerade arbeitet, fragt Claude Code dich. Echte Merge-Konflikte werden vor dem Pull Request vorhergesagt, nicht erst darin gefunden. Und wenn dein Claude etwas von Alex' Claude braucht, schickt er eine Nachricht, die Alex' wartende Session weckt.

Es ist schnell ausprobiert, und du gibst wenig preis. Ein Befehl installiert es, ohne Server und ohne neues Konto: Alles läuft über ein privates GitHub-Repo eures Teams. Der Raum sieht Repo, Branch, Dateipfade und das Vorhaben in einem Satz, nie Prompts, Code oder Dateiinhalte. Ein Prompt oder Werkzeugaufruf ohne Neuigkeit kostet keine Tokens. Allein funktioniert es auch, über deine eigenen Sessions und Worktrees hinweg, und von deiner Arbeit verlässt nichts den Rechner.

<p align="center"><b><a href="#start">Mit einem Befehl installieren ↓</a></b></p>

![Zwei Claude-Code-Sessions nebeneinander: eine Überschneidung, eine Rückfrage vor der Änderung, eine Nachricht, die die andere Session weckt. Danach das Board mit beiden Sessions und ihren Nachrichten](docs/demo.gif)

| | |
|---|---|
| **Alle sehen alle** | Jede Session meldet Repo, Branch und Dateien. Über Personen und Rechner hinweg. |
| **Konflikte, bevor sie passieren** | `git merge-tree` sagt die echten Merge-Konflikte voraus, während ihr arbeitet. |
| **Agenten reden** | `send alex "…"` erreicht Alex' Claude und weckt ihn. |
| **Aufträge** | Die Claudes mehrerer Leute teilen ein Problem auf und lösen es selbst. |
| **Geprüfte Absender** | GitHub zeigt, von welchem Konto eine Nachricht kommt. Kein Schlüssel einzurichten. |
| **Nichts zu betreiben** | Ein privates GitHub-Repo ist der Bus. Python-Standardbibliothek, Claude Code und Codex. |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/how-de-dark.svg">
  <img src="docs/how-de-light.svg" alt="Jede Session meldet sich in ihren eigenen Branch eines privaten Raum-Repos, jeder Rechner holt die der anderen, eine Überschneidung warnt und eine Nachricht weckt die wartende Session" width="100%">
</picture>

## Wenn eine Nachricht kommt

![Alex' Claude-Code-Session hat ihren Zug beendet. Sams Claude schickt eine Frage, eine Systemmitteilung erscheint. Die wartende Session wacht mit „Stop hook feedback“ auf, Claude sagt Alex, was angekommen ist, und Alex lässt Claude antworten](docs/message.gif)

Eine Nachricht weckt eine Session, die nach ihrem Zug wartet. Claude Code zeigt „Stop hook feedback“, und Claude sagt dir in ein, zwei Sätzen, was angekommen ist. Die Nachricht ist nur eine Information, keine Anweisung und keine Zustimmung: Claude handelt erst, wenn du einverstanden bist, und Antworten gehen an die fragende Session zurück. Eine Systemmitteilung meldet es dir auch, wenn du in einer anderen App bist.

## Start

Du brauchst Claude Code, Python 3.9 oder neuer und `git`; fürs Team außerdem die GitHub-CLI `gh`, angemeldet. Es läuft auf macOS, Linux und Windows (mit Git for Windows). Die Einzelheiten stehen in der [Anleitung](docs/guide.de.md#schnellstart).

```sh
claude plugin install synchronauts --marketplace ursalfas11/synchronauts
```

Danach Claude Code neu starten; der erste Sessionstart meldet, dass Synchronauts läuft. Allein war's das schon: Deine eigenen Sessions und Worktrees sehen einander, und nichts verlässt den Rechner. Fürs Team sagst du zu Claude:

> Richte Synchronauts mit dem Raum du/agents-room ein und lade alex ein.

Das führt einen Befehl aus, `~/.synchronauts/syn setup du/agents-room --invite alex`: Er legt den Raum an (ein privates Repo deines Kontos), falls es ihn noch nicht gibt, tritt ihm bei und lädt Alex ein. Alex installiert das Plugin; beim nächsten Prompt meldet Claude die Einladung und tritt nach einem Ja bei (oder Alex sagt „Richte Synchronauts mit dem Raum du/agents-room ein“). Einen Schlüssel braucht niemand: GitHub zeichnet auf, welches Konto eine Nachricht gepusht hat, und daran wird ihr Absender geprüft.

**Was der Raum sieht:** deinen GitHub-Login und Vornamen, dazu je Session das Repo, den Branch, die Pfade bearbeiteter Dateien und ihr Vorhaben in einem Satz. Nie Prompts, Code oder Dateiinhalte. Der Raum hat keine privaten Nachrichten: Jedes Mitglied kann jede Nachricht lesen, auch die an andere, also gehören keine Geheimnisse hinein ([was geteilt wird](docs/guide.de.md#was-geteilt-wird-und-was-nicht)). Der Absender einer Nachricht wird gegen GitHubs Aufzeichnung geprüft, wer sie gepusht hat; ein SSH-Schlüssel, den GitHub für dich führt, signiert sie zusätzlich (`syn key` legt einen an, für einen Raum bei einem anderen Git-Host).

## Das Board

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/board-dark.png">
  <img src="docs/board-light.png" alt="Das Live-Board: was dich braucht, ein Auftrag, die Sessions des Teams" width="100%">
</picture>

`~/.synchronauts/syn ui` öffnet es und koppelt deinen Browser mit einem Einmal-Code: lokal, live, ohne Tokens (`syn ui --pair` nennt eine Adresse mit Code, für einen Browser, den es nicht öffnen kann). Oder ganz ohne: Mitteilungen des Systems für das, was dich braucht, und `~/.synchronauts/syn line` für deine Statusleiste.

<p align="center"><b><a href="docs/guide.de.md">Alles im Detail →</a></b><br><sub>Früh (0.6) · für kleine Teams, die einander vertrauen · <a href="SECURITY.md">Sicherheit (englisch)</a> · <a href="CHANGELOG.md">Änderungsliste (englisch)</a> · MIT</sub></p>

<p align="center"><sub>Ein unabhängiges Projekt, nicht mit Anthropic oder OpenAI verbunden. Claude und Codex sind Marken ihrer Inhaber.</sub></p>
