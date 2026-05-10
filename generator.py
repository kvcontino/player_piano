import random
import time

from midi import make_midi_out

# C major pentatonic across three octaves (C3, C4, C5)
PENTATONIC_C = [0, 2, 4, 7, 9]  # semitone offsets from C
SCALE_PITCHES = [
    base + offset
    for base in (48, 60, 72)
    for offset in PENTATONIC_C
]

VELOCITY_RANGE = (40, 90)         # mp to mf — keep it gentle
NOTE_DURATION_RANGE = (0.3, 1.2)  # seconds
GAP_RANGE = (0.05, 0.4)


def play_one_note(midi_out) -> None:
    pitch = random.choice(SCALE_PITCHES)
    velocity = random.randint(*VELOCITY_RANGE)
    duration = random.uniform(*NOTE_DURATION_RANGE)
    midi_out.note_on(pitch, velocity)
    try:
        time.sleep(duration)
    finally:
        midi_out.note_off(pitch)  # always release, even on KeyboardInterrupt
    time.sleep(random.uniform(*GAP_RANGE))


def main() -> None:
    midi_out = make_midi_out()
    try:
        while True:
            play_one_note(midi_out)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        midi_out.close()


if __name__ == "__main__":
    main()
