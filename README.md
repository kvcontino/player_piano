# Player Piano

Self-playing ambient music system for the Yamaha DGX-505 (88 weighted keys, USB-MIDI), with persistent phrase memory and natural-language control via Claude.

## Architecture

Decoupled modules communicating via filesystem + SQLite:

- **Generator** — infinite loop reading `current_mood.json`, emits MIDI notes, logs phrases to DB
- **Agent** (Claude API) — interprets natural language, updates mood, searches memory, triggers replay
- **Feedback HTTP server** — like/tag the current phrase
- **Memory** — SQLite DB of phrases, feedback, musician profiles

The generator runs even if the agent fails. Phrases are atomic units (8-16 notes), logged with full parameters, profile linkage, and rateable later.

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
.venv/bin/python db.py             # initialize SQLite at data/phrases.db
.venv/bin/python seed_profiles.py  # insert musician profiles (Keith Emerson, etc.)
```

Fedora prerequisite: `sudo dnf install -y alsa-lib-devel` (needed for `python-rtmidi` to compile).

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

`current_mood.json` controls base generation parameters (scale, root, octave range, velocity, density). The generator re-reads it at the start of each phrase, so edits take effect within ~10 seconds.

## Profiles

`current_profile.json` activates a musician profile. Profiles overlay traits on top of the mood — they override scale selection, dynamics, octave range, note density, and interval behavior.

```json
{"name": "Keith Emerson"}
```

To deactivate a profile (raw mood only):
```json
{"name": null}
```

The profile is also re-read each phrase, so switching takes effect immediately.

**Keith Emerson** traits: harmonic minor / phrygian dominant / diminished scales; octave range 2-6; velocity 25-115; fast staccato runs to 2s held notes; 55% chance of interval leaps (>3 semitones), producing the dramatic jumps characteristic of ELP-era playing.

To add more profiles, add entries to `seed_profiles.py` and re-run it.
