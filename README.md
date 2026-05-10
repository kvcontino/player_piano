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

```fish
cd ~/2_projects/player_piano
uv venv
uv pip install -r requirements.txt
.venv/bin/python db.py    # initialize SQLite at data/phrases.db
```

## Usage

**Run the generator** (mock backend by default — logs notes to stdout):
```fish
.venv/bin/python generator.py
```

**Real MIDI backend** (requires a connected MIDI device):
```fish
.venv/bin/python -c 'import mido; print(mido.get_output_names())'
set -x MIDI_BACKEND real
set -x MIDI_PORT_NAME '<port name from list above>'
.venv/bin/python generator.py
```

**Feedback HTTP server** (in a second terminal):
```fish
.venv/bin/python feedback.py
```

Send feedback on the most recent phrase:
```fish
curl -s    http://localhost:5050/current
curl -sX POST http://localhost:5050/rate -H 'Content-Type: application/json' -d '{"rating": 5}'
curl -sX POST http://localhost:5050/tag  -H 'Content-Type: application/json' -d '{"tag": "meditative"}'
curl -sX POST http://localhost:5050/tag  -H 'Content-Type: application/json' -d '{"tag": "meditative", "remove": true}'
```

## Mood

`current_mood.json` controls how the generator behaves (scale, root, octave range, velocity, density). The generator re-reads it at the start of each phrase, so edits take effect within ~10 seconds.
