import json
import math
import random
import threading
import time
from pathlib import Path

from db import insert_phrase, start_session, end_session, get_profile
from midi import make_midi_out
from music import chord_pitches, scale_pitches, text_repr

MOOD_PATH = Path(__file__).parent / "current_mood.json"
PROFILE_PATH = Path(__file__).parent / "current_profile.json"
LAYERS_PATH = Path(__file__).parent / "current_layers.json"
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


def load_layers() -> dict | None:
    """Returns layers config dict, or None to use single-layer mode."""
    if not LAYERS_PATH.exists():
        return None
    return json.loads(LAYERS_PATH.read_text())


def merge_traits(mood: dict, traits: dict) -> dict:
    """Overlay profile traits onto mood. Profile wins on every key it defines."""
    params = dict(mood)
    for key, val in traits.items():
        if key == "scales":
            params["scale"] = random.choice(val)
        elif key == "voices":
            params["voice"] = random.choice(val)
        elif key == "time_sigs":
            params["time_sig"] = random.choice(val)
        elif key == "root" and val is not None:
            params["root"] = val
        else:
            params[key] = val
    return params


class BeatClock:
    """
    Absolute-time grid clock for synchronized multi-layer playback.

    Each layer calls wait_for_next_grid() after finishing a phrase. The target
    is computed from a fixed origin, so drift cannot accumulate across phrases.
    Layers with odd phrase lengths create natural rests and re-align on the
    next boundary — the irregularity is a feature, not a bug.
    """

    def __init__(self, bpm: float, grid_beats: int = 8):
        """
        bpm        — global tempo (overrides individual profile tempos)
        grid_beats — quarter-note beats per grid unit; 8 = two bars of 4/4
        """
        self.bpm = bpm
        self.grid_beats = grid_beats
        self._origin = time.monotonic()

    @property
    def beat_dur(self) -> float:
        return 60.0 / self.bpm

    @property
    def grid_dur(self) -> float:
        return self.beat_dur * self.grid_beats

    def wait_for_next_grid(self) -> None:
        elapsed = time.monotonic() - self._origin
        next_n = math.ceil(elapsed / self.grid_dur + 1e-9)
        target = self._origin + next_n * self.grid_dur
        wait = target - time.monotonic()
        if wait > 0:
            time.sleep(wait)


def build_slot_schedule(params: dict) -> list[tuple[float, float]]:
    """
    Returns [(note_dur, gap_dur), ...] for one metered phrase.
    Empty list means free-time mode (no tempo_bpm in params).

    Slots are sized so note_dur + gap_dur = slot_beats * beat_dur.
    legato controls what fraction of the slot the note sounds.
    """
    if "tempo_bpm" not in params:
        return []
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


def apply_bend_style(
    midi_out, duration: float, style: str, semitones: float, channel: int = 0
) -> None:
    """Send pitch bend messages during a held note. Caller resets bend to 0 in finally."""
    units = int(semitones * 4096)  # assumes GM default ±2 semitone bend range
    steps = max(5, min(20, int(duration / 0.02)))  # ~50ms per step

    if style == "slide_in":
        step_time = duration / steps
        for i in range(steps):
            midi_out.set_pitch_bend(int(-units + units * i / (steps - 1)), channel=channel)
            time.sleep(step_time)

    elif style == "fall_off":
        time.sleep(duration * 0.75)
        step_time = (duration * 0.25) / steps
        for i in range(steps):
            midi_out.set_pitch_bend(int(-units * i / (steps - 1)), channel=channel)
            time.sleep(step_time)

    elif style == "vibrato":
        freq, amplitude = 5.0, units * 0.4
        step_time = 0.02
        elapsed = 0.0
        while elapsed < duration:
            midi_out.set_pitch_bend(
                int(amplitude * math.sin(2 * math.pi * freq * elapsed)), channel=channel
            )
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
    midi_out,
    mood: dict,
    traits: dict,
    session_id: int,
    profile_id: int | None,
    channel: int = 0,
    global_bpm: int | None = None,
) -> int:
    params = merge_traits(mood, traits)
    if global_bpm is not None:
        params["tempo_bpm"] = global_bpm

    voice = params.get("voice")
    if voice is not None:
        midi_out.set_voice(voice, channel=channel)

    pitches_pool = scale_pitches(params["scale"], params["root"], tuple(params["octave_range"]))
    leap_prob = params.get("interval_leap_prob", 0.0)
    n_notes_range = params.get("n_notes_range", [8, 12])
    sustain_prob = params.get("sustain_prob", 0.0)
    chord_prob = params.get("chord_prob", 0.0)
    chord_types = params.get("chord_types", ["octave"])
    bend_prob = params.get("bend_prob", 0.0)
    bend_styles = params.get("bend_styles", ["slide_in"])
    bend_semitones = params.get("bend_semitones", 1.0)

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
        midi_out.set_sustain(True, channel=channel)
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
                midi_out.set_pitch_bend(-int(bend_semitones * 4096), channel=channel)

            companion_vel = max(1, int(velocity * 0.8))
            for p in to_play:
                midi_out.note_on(p, velocity if p == pitch else companion_vel, channel=channel)
            try:
                if bend_style:
                    apply_bend_style(midi_out, note_dur, bend_style, bend_semitones, channel=channel)
                else:
                    time.sleep(note_dur)
            finally:
                if bend_style:
                    midi_out.set_pitch_bend(0, channel=channel)
                for p in to_play:
                    midi_out.note_off(p, channel=channel)

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
            midi_out.set_sustain(False, channel=channel)

    phrase_params = {
        "n_notes": len(note_events),
        "scale": params["scale"],
        "root": params["root"],
        "voice": voice,
        "channel": channel,
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


# ── Layer loop ─────────────────────────────────────────────────────────────────

def layer_loop(
    midi_out,
    clock: BeatClock,
    session_id: int,
    channel: int,
    profile_name: str | None,
    mood_overrides: dict,
    stop_event: threading.Event,
) -> None:
    """Continuous phrase loop for one layer. Waits for the grid after each phrase."""
    profile_id = None
    traits: dict = {}
    if profile_name:
        p = get_profile(profile_name)
        if p:
            profile_id, traits = p["id"], p["traits"]
        else:
            print(f"[warning: profile '{profile_name}' not found — run seed_profiles.py]", flush=True)

    while not stop_event.is_set():
        mood = {**load_mood(), **mood_overrides}
        try:
            phrase_id = play_phrase(
                midi_out, mood, traits, session_id, profile_id,
                channel=channel, global_bpm=clock.bpm,
            )
            print(f"[ch{channel} phrase {phrase_id}]", flush=True)
        except Exception as exc:
            print(f"[ch{channel} error: {exc}]", flush=True)
        clock.wait_for_next_grid()


# ── Entry points ───────────────────────────────────────────────────────────────

def _run_single(midi_out, session_id: int) -> None:
    """Original single-layer loop (no current_layers.json)."""
    while True:
        mood = load_mood()
        profile_id, traits = load_profile()
        phrase_id = play_phrase(midi_out, mood, traits, session_id, profile_id)
        print(f"[phrase {phrase_id} logged]", flush=True)


def _run_layered(midi_out, session_id: int, config: dict) -> None:
    """Multi-layer loop: one thread per layer, all locked to a shared BeatClock."""
    global_bpm = config.get("bpm", 88)
    grid_beats = config.get("grid_beats", 8)
    layer_specs = config["layers"]

    clock = BeatClock(global_bpm, grid_beats)
    stop_event = threading.Event()

    threads = [
        threading.Thread(
            target=layer_loop,
            args=(midi_out, clock, session_id,
                  spec["channel"], spec.get("profile"), spec.get("mood_overrides", {}),
                  stop_event),
            daemon=True,
            name=f"layer-ch{spec['channel']}",
        )
        for spec in layer_specs
    ]

    print(
        f"[{len(threads)} layers | {global_bpm} bpm | grid={grid_beats} beats]",
        flush=True,
    )
    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(0.5)
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=8.0)  # wait for current phrases to finish naturally


def main() -> None:
    midi_out = make_midi_out()
    session_id = start_session(HOST)
    print(f"[session {session_id} started]", flush=True)

    layers_config = load_layers()

    try:
        if layers_config:
            _run_layered(midi_out, session_id, layers_config)
        else:
            _run_single(midi_out, session_id)
    except KeyboardInterrupt:
        print("\n[stopped]", flush=True)
    finally:
        end_session(session_id)
        # Reset pitch bend and sustain on all channels that could have been used
        channels = (
            {spec["channel"] for spec in layers_config["layers"]}
            if layers_config else {0}
        )
        for ch in channels:
            midi_out.set_pitch_bend(0, channel=ch)
            midi_out.set_sustain(False, channel=ch)
        midi_out.close()


if __name__ == "__main__":
    main()
