#!/usr/bin/env bash
# Run the player piano generator against the real DGX-505.
# Works from fish, bash, or the kevadk server — shell-agnostic.
exec env \
  MIDI_BACKEND=real \
  MIDI_PORT_NAME="DGX-505:DGX-505 MIDI 1 24:0" \
  .venv/bin/python generator.py "$@"
