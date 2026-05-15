#!/usr/bin/env python3
"""
Quick smoke test: sends one note to each channel and confirms the port opens.
Run with:  MIDI_BACKEND=real MIDI_PORT_NAME="..." .venv/bin/python test_midi.py
"""
import time
from midi import make_midi_out

midi = make_midi_out()
print(f"Backend: {midi.__class__.__name__}")

for ch in (0, 1):
    print(f"Channel {ch}: note on C4 (pitch 60) ...")
    midi.set_voice(0, channel=ch)   # Acoustic Grand Piano
    midi.note_on(60, 80, channel=ch)
    time.sleep(1.0)
    midi.note_off(60, channel=ch)
    time.sleep(0.3)

midi.close()
print("Done.")
