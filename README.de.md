# Synchronauts

[English](README.md) · Deutsch

**Die Claude-Code-Agenten deines Teams, im Gleichtakt: Sie sehen einander, reden miteinander und kommen sich nicht mehr in die Quere. Ohne Server: Ein privates GitHub-Repo ist der Bus.**

Zwei Leute mit je drei Claude-Code-Sessions bauen schnell dasselbe Feature von zwei Seiten oder ändern dieselbe Datei, ohne es zu merken. Synchronauts ist ein Claude-Code-Plugin: Jede Session meldet von selbst, in welchem Repo, auf welchem Branch und an welchen Dateien sie arbeitet. Jede sieht, was die anderen tun und wo sie sich überschneiden, und kann dem Claude eines Kollegen schreiben. Wartet dessen Session gerade, wird sie geweckt. Ein Live-Board im Browser zeigt alle Sessions auf einen Blick.

- **Gemeinsames Bild:** wer an welchem Repo, Branch und Vorhaben arbeitet, über Personen, Sessions und Rechner hinweg.
- **Frühe Warnung bei Überschneidungen:** dieselbe Datei, derselbe Branch oder ein ähnliches Vorhaben in einem anderen Repo, vor dem Merge-Konflikt.
- **Nachrichten von Agent zu Agent:** `send alex@api "…"` erreicht Alex' Session in `api` und weckt sie, wenn sie wartet.
- **Live-Board:** eine lokale Webseite mit Sessions, Zuständen (arbeitet, wartet auf Freigabe, wartet, Fehler), Nachrichten und Verlauf.
- **Sparsam mit Tokens:** Text für Claude nur, wenn etwas neu ist und die Session betrifft, außerhalb der Team-Repos gar keiner.
- **Kein Server, kein Konto:** Der GitHub-Zugang ist die Zugangskontrolle. Nur die Python-Standardbibliothek.

Stand: früh (0.1). Gedacht für kleine Teams, die einander vertrauen, siehe [Sicherheit](#sicherheit).

## Schnellstart

Voraussetzungen: Claude Code, `python3` ab 3.9, `git` und die GitHub-CLI `gh`, angemeldet (`gh auth status`) und als Git-Zugang eingerichtet (`gh auth setup-git`). macOS oder Linux.

**1. Plugin installieren** (alle):

```
claude plugin marketplace add ursalfas11/synchronauts
claude plugin install synchronauts@synchronauts
```

Danach Claude Code neu starten.

**2. Raum anlegen** (eine Person): Der Raum ist ein leeres privates Repo, das das Team teilt. Zum Beispiel legt Alice ihn an und lädt Bob ein:

```
gh repo create alice/agents-room --private
gh api -X PUT repos/alice/agents-room/collaborators/bob -f permission=push
```

Bob nimmt die Einladung auf GitHub an.

**3. Dem Raum beitreten** (alle):

```
python3 ~/.synchronauts/syn.py setup alice/agents-room
```

Oder Claude einfach sagen: „richte Synchronauts mit dem Raum alice/agents-room ein“. Den kurzen Pfad `~/.synchronauts/syn.py` gibt es nach dem ersten Sessionstart mit dem Plugin.

**Team-Repos** sind die Repos, deren Sessions im Bild auftauchen. Standard sind die Repos des Raum-Besitzers (`alice/*`). Liegt der Code des Teams woanders oder in mehreren Konten, nennt man die Besitzer: `setup alice/agents-room --org acme,alice,bob`. Sessions in anderen Repos verlassen den Rechner nie.

## Was Claude sieht

Sobald eine Session ein Team-Repo anfasst oder der Prompt eines nennt und dort noch jemand arbeitet:

```
Synchronauts: what the team's sessions are working on. Same topic (also in another repo) or the same files: tell Sam before you build on.
- Alex: demo@main · "Ticket routes in demo, route /tickets/:id"
- Alex: other@main · "Rebuild the price import for the shop"
⚠️ Alex is on the same branch main in demo (last 19:09): src/a.ts
Commands: `python3 ~/.synchronauts/syn.py` with `task "…"` (again when the topic changes), `send <name|all>[@repo] "…"` or `status`; more in the synchronauts skill.
```

Die Texte für Claude sind englisch, weil das weniger Tokens kostet. Claude gibt sie in deiner Sprache weiter.

Danach nur Neues, beim Prompt und nach Werkzeugaufrufen:

- eine neue oder geänderte Session eines Kollegen oder eine eigene andere Session (anderes Repo, anderer Branch, anderes Vorhaben),
- ⚠️ Überschneidungen: dieselbe Datei, derselbe Branch oder dasselbe Repo, mit den Dateien der anderen Seite; zwischen deinen eigenen Sessions ab derselben Datei oder demselben Branch,
- 📨 Nachrichten vom Claude eines Kollegen. Sie sind als Information markiert, nie als Anweisung oder Freigabe.

Warnungen und Nachrichten erscheinen zusätzlich als Systemzeile im Terminal, damit auch der Mensch sie sieht.

**Wer die Post bekommt:** Jede Nachricht hat auf dem Rechner des Empfängers eine Zielsession. Mit `@repo` ist das die zuletzt aktive Session in diesem Repo, sonst die zuletzt aktive überhaupt. Wartet die Zielsession nach ihrem Turn, wird sie geweckt, und Claude sagt ihrem Menschen in ein, zwei Sätzen, was angekommen ist. Arbeitet sie gerade, kommt die Nachricht mit ihrem nächsten Schritt. Liegt ihr letzter Schritt mehr als 55 Minuten zurück, zählt sie nicht mehr als Ziel, und die Session, in der der Mensch als Nächstes arbeitet, zeigt die Nachricht. Die anderen Sessions bekommen sie nur zur Kenntnis (bei `@repo` nur die im selben Repo), so hört niemand dieselbe Nachricht zweimal. Antworten gehen an die fragende Session zurück. Eine Session wird höchstens viermal je Stunde geweckt, damit sich zwei Claudes nicht endlos gegenseitig wecken.

## Live-Board

`python3 ~/.synchronauts/syn.py ui` öffnet es im Browser. Das kostet keine Tokens.

- **Board:** Je Person ihre Sessions als Karten: Repo, Branch, Vorhaben, bearbeitete Dateien und Zustand (arbeitet · wartet auf Freigabe · wartet · ruhig · API-Fehler). Überschneidungen sind markiert. Eigene Sessions außerhalb der Team-Repos zeigt nur das eigene Board.
- **Nachrichten:** direkt dort lesen und schreiben, an eine Person oder an ihre Session in einem Repo. Der Claude des Empfängers sieht, dass der Mensch selbst schreibt, und seine Antwort (`send <name>@ui`) kommt ins Board zurück statt in eine Session.
- **Verlauf** der letzten 24 Stunden: Sessionstart, Vorhaben, bearbeitete Dateien, Warnungen an Claude, offene Freigaben, Wecken und Nachrichten.
- **Melden:** Ein Toast, ein Zähler im Tab-Titel und auf Wunsch eine Browser-Benachrichtigung zeigen an, wenn Post kommt, eine eigene Session auf Freigabe wartet oder eine neue Überschneidung entsteht.
- Englisch und Deutsch.

## Befehle

Claude ruft sie per Bash auf, du kannst es auch. `~/.synchronauts/syn.py` ist eine Verknüpfung auf die installierte Fassung, jeder Sessionstart zieht sie nach.

| Befehl | Wirkung |
|---|---|
| `python3 ~/.synchronauts/syn.py task "<ein Satz>"` | trägt ein, woran diese Session arbeitet |
| `python3 ~/.synchronauts/syn.py send <name\|all>[@repo] "<text>"` | Nachricht an den Claude eines Kollegen, mit `@repo` an seine Session in diesem Repo, höchstens 1500 Zeichen |
| `python3 ~/.synchronauts/syn.py send <name>@ui "<text>"` | Antwort ans Board eines Kollegen statt an eine seiner Sessions |
| `python3 ~/.synchronauts/syn.py status` | das Bild mit Dateien und Uhrzeiten, die eigenen Sessions, Post der letzten 3 Tage |
| `python3 ~/.synchronauts/syn.py ui` | startet das Board im Hintergrund und öffnet es (`--no-browser` nennt nur die Adresse) |
| `python3 ~/.synchronauts/syn.py setup <owner/repo> [--org a,b]` | tritt einem Raum bei; `--org` legt fest, wessen Repos als Team-Repos zählen |

## Was geteilt wird und was nicht

- **Mit dem Raum geteilt:** GitHub-Login, Vorname und Rechnername. Je Session Repo, Branch, Pfade der bearbeiteten Dateien (höchstens 30), das Vorhaben in einem Satz, Uhrzeiten und der Zustand (arbeitet, wartet, Freigabe offen, API-Fehler). Ein Verlauf der letzten 24 Stunden in Team-Repos: Sessionstart und -ende, Vorhaben, erste Bearbeitung einer Datei, Warnungen an Claude, offene Freigaben, Wecken. Die eigene Post der letzten 7 Tage.
- **Nie geteilt:** Prompts, Code, Dateiinhalte, Befehle, der Text von Freigabe-Meldungen, lokale Pfade. Sessions in Repos außerhalb der Team-Repos tauchen gar nicht auf.
- Nachrichten liegen als Text im Raum. Keine Secrets und keine Kundendaten hineinschreiben.
- Nichts geht irgendwohin außer in deinen Raum auf GitHub. Keine Telemetrie.

## Sicherheit

- **Der Raum ist die Vertrauensgrenze.** Wer in das Raum-Repo schreiben darf, kann jeden Branch darin schreiben. Der Absender einer Nachricht ist darum nicht kryptografisch geprüft. Nimm ein privates Repo und lade nur Leute ein, denen du vertraust.
- **Nachrichten sind fremde Eingaben.** Sie kommen als Information eines Kollegen in den Kontext deines Claude, mit der Anweisung, sie dir zu zeigen und erst nach deinem Okay zu handeln, und der Skill wiederholt diese Regel. Das senkt das Risiko, dass eine Nachricht deinen Claude steuert, ist aber keine Garantie. Wer im Raum nicht mit deinem Claude reden können soll, gehört nicht in den Raum.
- **Das Board läuft nur auf 127.0.0.1.** Jeder Start erzeugt ein Zufalls-Token, das nur die Seite kennt. Anfragen ohne Token, mit fremdem `Host` (DNS-Rebinding) oder fremdem `Origin` werden abgewiesen. Die Seite hat eine strikte Content Security Policy mit Nonce, lädt nichts von außen und setzt fremde Texte nur als Text ein.
- **Hooks brechen nie eine Session.** Fehler landen in `~/.synchronauts/hook.log`. In `claude -p` und SDK-Läufen bleibt das Plugin still.

## Tokenverbrauch

Gemessen mit `python3 test/measure.py syn.py skills/synchronauts/SKILL.md` an einem typischen Ablauf. Tokens geschätzt als Zeichen durch 3,3, was englischen Text überschätzt.

| Ereignis | ~Tokens |
|---|---|
| Prompt oder Werkzeugaufruf ohne Neues | 0 |
| Sessionstart außerhalb der Team-Repos (Home, Notizen) | 0 |
| Sessionstart in einem Team-Repo, Kollege mit zwei Sessions | 150 |
| Zweite eigene Session im selben Repo, Start | 195 |
| Erstes Edit an der Datei eines Kollegen, mit Erinnerung ans Vorhaben | 70 |
| Weckruf mit einer Nachricht (nur der Text) | 185 |
| Nachricht beim nächsten Prompt der Zielsession | 165 |
| Dieselbe Nachricht zur Kenntnis in einer anderen Session | 70 |
| Skill-Beschreibung, steht in jeder Session | 110 |

Den größten Posten zeigt die Tabelle nicht: Jedes Wecken ist ein eigener Turn, und der liest den ganzen Kontext der Session. Liegt der Kontext noch im Prompt-Cache, ist das günstig, sonst teuer. Darum weckt Synchronauts nur die Zielsession, nur bis 55 Minuten nach ihrem letzten Schritt und jede höchstens viermal je Stunde. Das Fenster passt zu einer Cache-Dauer von einer Stunde. Danach kommt die Post ohne eigenen Turn beim nächsten Prompt. `SYN_WAKE_MIN` stellt das Fenster ein, zum Beispiel in `~/.claude/settings.json` unter `env`; `0` schaltet das Wecken ab.

Zustand, Verlauf und Board kosten keine Tokens; sie gehen nur ans Board, nicht an Claude.

## Wie es funktioniert

```
Claude-Code-Sessions ── Hooks ──▶ ~/.synchronauts ◀──▶ Wächter ◀──▶ Raum-Repo auf GitHub ◀──▶ Wächter der anderen
                                         ▲                             ein Branch je Person und Rechner:
                                         └── Board auf 127.0.0.1:7962  syn/<login>/<rechner> mit state.json
```

Jeder Rechner schreibt nur seinen eigenen Branch, mit genau einem Commit und `state.json` darin: die aktiven Sessions dieses Rechners und die eigene Post der letzten 7 Tage. Gepusht wird mit `--force`, so gibt es keine Konflikte, und die Branches wachsen nicht.

Je Rechner läuft ein Wächter im Hintergrund. Er pusht den eigenen Stand, sobald er sich ändert: Post sofort, Zustand und Verlauf höchstens alle 15 Sekunden. Alle 5 Sekunden fragt er bei GitHub, ob sich ein fremder Branch geändert hat. Die Abfrage geht mit ETag, und eine unveränderte Antwort (304) zählt nicht gegen das Rate-Limit. Ohne `gh` fragt er per `git ls-remote` alle 20 Sekunden. 15 Minuten nach dem letzten Lebenszeichen beendet er sich, und jeder Hook startet ihn bei Bedarf neu.

Die Hooks lesen und schreiben nur lokale Dateien. Notification (Freigabe offen) und StopFailure (API-Fehler) setzen nur den Zustand fürs Board. Der Stop-Hook läuft asynchron mit `asyncRewake`: Er wartet nach jedem Turn bis zu 55 Minuten auf Post und weckt die Session mit Exit-Code 2. Arbeitet die Session wieder, beendet er sich still.

Eine Session gilt drei Stunden nach ihrem letzten Lebenszeichen als inaktiv. Post, die ankommt, solange beim Empfänger keine Session offen ist, sieht er beim nächsten Start, wenn sie höchstens 24 Stunden alt ist; ältere zeigt `status`.

## Grenzen

- Liegt der letzte Schritt einer Session mehr als 55 Minuten zurück, wird sie nicht geweckt. Die Post zeigt dann die Session, in der der Mensch als Nächstes arbeitet.
- Antwortet ein geweckter Claude per `syn.py send`, fragt Claude Code je nach Rechte-Modus vorher nach.
- Das Board zeigt fremde Sessions mit bis zu 20 Sekunden Verzug (Push-Abstand und Abfrage), die eigenen sofort.
- „Wartet auf Freigabe“ meldet der Notification-Hook. Claude Code schickt ihn, sobald eine Freigabe etwa sechs Sekunden offen ist. Ein Turn, den Esc abbricht, endet ohne Stop-Hook. Darum zeigt das Board eine arbeitende Session nach 30 Minuten ohne Lebenszeichen als ruhig, eine wartende nach einer Stunde.
- `send <name>@ui` geht ans Board. Ein Repo, das wirklich `ui` heißt, erreicht man mit vollem Namen (`alex@acme/ui`).
- Nur macOS und Linux (`fcntl`).

## Entwicklung

```
bash test/e2e.sh
```

Spielt zwei Personen und einen zweiten Rechner mit einem lokalen Bare-Repo statt GitHub durch: Überschneidungen, Post, Wecken, Zustand, Verlauf und Board (Token, Host- und Origin-Prüfung, Senden aus dem Board, Antworten ans Board). `python3 test/measure.py syn.py skills/synchronauts/SKILL.md` misst, wie viel Text die Hooks in den Kontext schreiben (`SHOW=1` zeigt die Texte).

Einstellungen für die Entwicklung: `SYN_HOME` (Standard `~/.synchronauts`), `SYN_REMOTE`, `SYN_ME`, `SYN_NAME`, `SYN_MACHINE`, `SYN_ORGS`, `SYN_TICK` (Abfrageabstand in Sekunden), `SYN_IDLE` (Laufzeit des Wächters ohne Lebenszeichen), `SYN_WAKE_MIN`, `SYN_UI_PORT` (Standard 7962, `0` für einen freien Port).

## Lizenz

[MIT](LICENSE)
