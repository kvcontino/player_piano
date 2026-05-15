import json
import math
import random
import time
from pathlib import Path

from db import insert_phrase, start_session, end_session, get_profile
from midi import make_midi_out
from music import chord_pitches, scale_pitches, text_repr

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
        elif key == "time_sigs":
            params["time_sig"] = random.choice(val)  # pick one time sig per phrase
        elif key == "root" and val is not None:
            params["root"] = val
        else:
            params[key] = val
    return params


def build_slot_schedule(params: dict) -> list[tuple[float, float]]:
    """
    Returns [(note_dur, gap_dur), ...] for one metered phrase.
    Empty list means free-time mode (no tempo_bpm in params).

    Slots are sized so note_dur + gap_dur = slot_beats * beat_dur.
    legato controls what fraction of the slot the note sounds.
    """
    if "tempo_bpm" not in params:
        return []
    # denominator tells us the beat unit: 4 = quarter, 8 = eighth, etc.
    beat_dur = (60.0 / params["tempo_bpm"]) * (4.0 / params["time_sig"][1])
    beats_per_bar = params["time_sig"][0]
    n_bars = params.get("n_bars", 2)
    budget = float(n_bars * beats_per_bar)
    note_values = params.get("note_values", [0.25, 0.5, 0.5, 1.0])
    legato = params.get("legato", 0.85)

    slots: list[tuple[float, float]] = []
    remaining = budget
    while remaining > 1e-9:
        choices = [v for v in note_values if v <= remaining + 1e-9]
        if not choices:
            break
        slot_beats = random.choice(choices)
        slot_secs = slot_beats * beat_dur
        slots.append((slot_secs * legato, slot_secs * (1.0 - legato)))
        remaining = round(remaining - slot_beats, 9)
    return slots


def apply_bend_style(midi_out, duration: float, style: str, semitones: float) -> None:
    """Send pitch bend messages during a held note. Caller resets bend to 0 in finally."""
    units = int(semitones * 4096)  # assumes GM default ±2 semitone bend range
    steps = max(5, min(20, int(duration / 0.02)))  # ~50ms per step

    if style == "slide_in":
        # note_on was sent with bend already at -units; ramp up to centre
        step_time = duration / steps
        for i in range(steps):
            midi_out.set_pitch_bend(int(-units + units * i / (steps - 1)))
            time.sleep(step_time)

    elif style == "fall_off":
        time.sleep(duration * 0.75)
        step_time = (duration * 0.25) / steps
        for i in range(steps):
            midi_out.set_pitch_bend(int(-units * i / (steps - 1)))
            time.sleep(step_time)

    elif style == "vibrato":
        freq, amplitude = 5.0, units * 0.4
        step_time = 0.02
        elapsed = 0.0
        while elapsed < duration:
            midi_out.set_pitch_bend(int(amplitude * math.sin(2 * math.pi * freq * elapsed)))
            time.sleep(step_time)
            elapsed += step_time

    else:
        time.sleep(duration)


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
    sustain_prob = params.get("sustain_prob", 0.0)
    chord_prob = params.get("chord_prob", 0.0)
    chord_types = params.get("chord_types", ["octave"])
    bend_prob = params.get("bend_prob", 0.0)
    bend_styles = params.get("bend_styles", ["slide_in"])
    bend_semitones = params.get("bend_semitones", 1.0)

    # Build timing schedule — metered if tempo_bpm present, otherwise free-time
    timing = build_slot_schedule(params)
    if not timing:
        n = random.randint(*n_notes_range)
        timing = [
            (random.uniform(*params["note_duration_range"]),
             random.uniform(*params["gap_range"]))
            for _ in range(n)
        ]

    note_events: list[dict] = []
    pitches: list[int] = []
    phrase_start = time.monotonic()
    prev_pitch: int | None = None

    use_sustain = random.random() < sustain_prob
    if use_sustain:
        midi_out.set_sustain(True)
    try:
        for note_dur, gap_dur in timing:
            pitch = pick_note(pitches_pool, prev_pitch, leap_prob)
            velocity = random.randint(*params["velocity_range"])
            t_offset_ms = int((time.monotonic() - phrase_start) * 1000)

            if chord_prob > 0 and random.random() < chord_prob:
                to_play = chord_pitches(pitch, random.choice(chord_types), pitches_pool)
            else:
                to_play = [pitch]

            bend_style = (
                random.choice(bend_styles)
                if bend_prob > 0 and random.random() < bend_prob
                else None
            )

            if bend_style == "slide_in":
                midi_out.set_pitch_bend(-int(bend_semitones * 4096))

            companion_vel = max(1, int(velocity * 0.8))
            for p in to_play:
                midi_out.note_on(p, velocity if p == pitch else companion_vel)
            try:
                if bend_style:
                    apply_bend_style(midi_out, note_dur, bend_style, bend_semitones)
                else:
                    time.sleep(note_dur)
            finally:
                if bend_style:
                    midi_out.set_pitch_bend(0)
                for p in to_play:
                    midi_out.note_off(p)

            event = {
                "pitch": pitch,
                "velocity": velocity,
                "time_ms": t_offset_ms,
                "duration_ms": int(note_dur * 1000),
            }
            if len(to_play) > 1:
                event["chord"] = to_play[1:]
            if bend_style:
                event["bend"] = bend_style
            note_events.append(event)
            pitches.append(pitch)
            prev_pitch = pitch
            time.sleep(gap_dur)
    finally:
        if use_sustain:
            midi_out.set_sustain(False)

    phrase_params = {
        "n_notes": len(note_events),
        "scale": params["scale"],
        "root": params["root"],
        "voice": voice,
        "interval_leap_prob": leap_prob,
        "sustain": use_sustain,
        "chord_prob": chord_prob,
        "bend_prob": bend_prob,
    }
    if "tempo_bpm" in params:
        phrase_params["tempo_bpm"] = params["tempo_bpm"]
        phrase_params["time_sig"] = params["time_sig"]
        phrase_params["n_bars"] = params.get("n_bars", 2)

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
        midi_out.set_pitch_bend(0)  # safety reset on any exit
        midi_out.close()


if __name__ == "__main__":
    main()
