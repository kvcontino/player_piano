# Player Piano

Self-playing ambient music system for the Yamaha DGX-505 (88 weighted keys, USB-MIDI), with persistent phrase memory and natural-language control via Claude.

## Architecture

Decoupled modules communicating via filesystem + SQLite:

- **Generator** — infinite loop reading `current_mood.json`, emits MIDI notes, logs phrases to DB
- **Agent** (Claude API) — interprets natural language, updates mood, searches memory, triggers replay
- **Feedback HTTP server** — like/tag the current phrase
- **Memory** — SQLite DB of phrases, feedback, musician profiles

The generator runs even if the agent fails. Phrases (8-12 notes each) are atomic units, logged with full parameters and rateable later.

## Stages

1. Basic generator (pentatonic, random) — verify MIDI connection
2. Phrase logging + feedback HTTP — build memory foundation
3. Musician profiles + biased generation — enable style reproduction
4. Claude agent with tools (search, replay, mood) — natural language control
5. Recall system: name/phrase → replay or style synthesis

## Dev vs deploy

| Component | Develop (laptop) | Deploy (kevadk) |
|---|---|---|
| Code, schema | local | git pull |
| MIDI output | mock backend (stdout) | real (USB → DGX-505) |
| SQLite DB | test data, gitignored | real data, gitignored |

The piano lives next to the server, so the generator runs on kevadk in production. The laptop is the dev environment; mock MIDI lets the full pipeline run without hardware.

## Setup

_TBD — Python deps (`mido`, `python-rtmidi`), MIDI backend env var, DB init script._
