import json
import random
import time
from pathlib import Path

from db import insert_phrase, start_session, end_session, get_profile
from midi import make_midi_out
from music import scale_pitches, text_repr

MOOD_PATH = Path(__file__).parent / "current_mood.json"
PROFILE_PATH = Path(__file__).parent / "current_profile.json"
HOST = "laptop"


def load_mood() -> dict:
    return json.loads(MOOD_PATH.read_text())


def load_profile() -> tuple[int | None, dict]:
    """Returns (profile_id, traits) — empty traits dict if no profile active."""
    if not PROFILE_PATH.exists():
        return None, {}
    data = json.loads(PROFILE_PATH.read_text())
    name = data.get("name")
    if not name:
        return None, {}
    profile = get_profile(name)
    if profile is None:
        print(f"[warning: profile '{name}' not found in DB — run seed_profiles.py]", flush=True)
        return None, {}
    return profile["id"], profile["traits"]


def merge_traits(mood: dict, traits: dict) -> dict:
    """Overlay profile traits onto mood. Profile wins on every key it defines."""
    params = dict(mood)
    for key, val in traits.items():
        if key == "scales":
            params["scale"] = random.choice(val)  # pick one scale per phrase
        elif key == "voices":
            params["voice"] = random.choice(val)  # pick one voice per phrase
        elif key == "root" and val is not None:
            params["root"] = val
        else:
            params[key] = val
    return params


def pick_note(pool: list[int], prev: int | None, leap_prob: float) -> int:
    """Pick next pitch, biased toward leaps (>3 semitones) at rate leap_prob."""
    if prev is None or leap_prob <= 0:
        return random.choice(pool)
    near = [p for p in pool if abs(p - prev) <= 3]
    leap = [p for p in pool if abs(p - prev) > 3]
    if near and leap:
        return random.choice(leap if random.random() < leap_prob else near)
    return random.choice(pool)


def play_phrase(
    midi_out, mood: dict, traits: dict, session_id: int, profile_id: int | None
) -> int:
    params = merge_traits(mood, traits)

    voice = params.get("voice")
    if voice is not None:
        midi_out.set_voice(voice)

    pitches_pool = scale_pitches(params["scale"], params["root"], tuple(params["octave_range"]))
    leap_prob = params.get("interval_leap_prob", 0.0)
    n_notes_range = params.get("n_notes_range", [8, 12])

    n_notes = random.randint(*n_notes_range)
    note_events: list[dict] = []
    pitches: list[int] = []
    phrase_start = time.monotonic()
    prev_pitch: int | None = None

    for _ in range(n_notes):
        pitch = pick_note(pitches_pool, prev_pitch, leap_prob)
        velocity = random.randint(*params["velocity_range"])
        duration = random.uniform(*params["note_duration_range"])
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
        prev_pitch = pitch
        time.sleep(random.uniform(*params["gap_range"]))

    phrase_params = {
        "n_notes": n_notes,
        "scale": params["scale"],
        "root": params["root"],
        "voice": voice,
        "interval_leap_prob": leap_prob,
    }
    return insert_phrase(
        session_id=session_id,
        notes=note_events,
        params=phrase_params,
        mood=mood,
        text_repr=text_repr(pitches),
        profile_id=profile_id,
    )


def main() -> None:
    midi_out = make_midi_out()
    session_id = start_session(HOST)
    print(f"[session {session_id} started]", flush=True)
    try:
        while True:
            mood = load_mood()
            profile_id, traits = load_profile()
            phrase_id = play_phrase(midi_out, mood, traits, session_id, profile_id)
            print(f"[phrase {phrase_id} logged]", flush=True)
    except KeyboardInterrupt:
        print("\n[stopped]", flush=True)
    finally:
        end_session(session_id)
        midi_out.close()


if __name__ == "__main__":
    main()
