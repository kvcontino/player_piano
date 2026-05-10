import json
import random
import time
from pathlib import Path

from db import insert_phrase, start_session, end_session
from midi import make_midi_out
from music import scale_pitches, text_repr

MOOD_PATH = Path(__file__).parent / "current_mood.json"
HOST = "laptop"


def load_mood() -> dict:
    return json.loads(MOOD_PATH.read_text())


def play_phrase(midi_out, mood: dict, session_id: int) -> int:
    pitches_pool = scale_pitches(mood["scale"], mood["root"], tuple(mood["octave_range"]))
    velocity_range = mood["velocity_range"]
    note_duration_range = mood["note_duration_range"]
    gap_range = mood["gap_range"]

    n_notes = random.randint(8, 12)
    note_events: list[dict] = []
    pitches: list[int] = []
    phrase_start = time.monotonic()

    for _ in range(n_notes):
        pitch = random.choice(pitches_pool)
        velocity = random.randint(*velocity_range)
        duration = random.uniform(*note_duration_range)
        t_offset_ms = int((time.monotonic() - phrase_start) * 1000)

        midi_out.note_on(pitch, velocity)
        try:
            time.sleep(duration)
        finally:
            midi_out.note_off(pitch)

        note_events.append({
            "pitch": pitch,
            "velocity": velocity,
            "time_ms": t_offset_ms,
            "duration_ms": int(duration * 1000),
        })
        pitches.append(pitch)
        time.sleep(random.uniform(*gap_range))

    params = {"n_notes": n_notes, "scale": mood["scale"], "root": mood["root"]}
    return insert_phrase(
        session_id=session_id,
        notes=note_events,
        params=params,
        mood=mood,
        text_repr=text_repr(pitches),
    )


def main() -> None:
    midi_out = make_midi_out()
    session_id = start_session(HOST)
    print(f"[session {session_id} started]", flush=True)
    try:
        while True:
            mood = load_mood()  # re-read each phrase so edits take effect live
            phrase_id = play_phrase(midi_out, mood, session_id)
            print(f"[phrase {phrase_id} logged]", flush=True)
    except KeyboardInterrupt:
        print("\n[stopped]", flush=True)
    finally:
        end_session(session_id)
        midi_out.close()


if __name__ == "__main__":
    main()
