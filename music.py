NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Subset of General MIDI voice names (program numbers 0-indexed, as mido expects)
GM_VOICES = {
    0:  "Acoustic Grand Piano",
    1:  "Bright Acoustic Piano",
    4:  "Electric Piano 1",
    5:  "Electric Piano 2",
    16: "Drawbar Organ",       # Hammond B-3 style
    17: "Percussive Organ",
    18: "Rock Organ",
    19: "Church Organ",
    40: "Violin",
    48: "String Ensemble 1",
    49: "String Ensemble 2",
    52: "Choir Aahs",
    80: "Lead 1 (Square)",
    81: "Lead 2 (Sawtooth)",   # Moog-like
    88: "Pad 1 (New Age)",
    89: "Pad 2 (Warm)",
}


def voice_name(program: int) -> str:
    return GM_VOICES.get(program, f"Voice {program}")

ROOTS = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

SCALES = {
    "pentatonic_major":  [0, 2, 4, 7, 9],
    "pentatonic_minor":  [0, 3, 5, 7, 10],
    "major":             [0, 2, 4, 5, 7, 9, 11],
    "minor":             [0, 2, 3, 5, 7, 8, 10],
    "dorian":            [0, 2, 3, 5, 7, 9, 10],
    "harmonic_minor":    [0, 2, 3, 5, 7, 8, 11],   # natural minor + raised 7th
    "phrygian":          [0, 1, 3, 5, 7, 8, 10],   # b2 gives dark, Spanish character
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],   # phrygian + major 3rd; exotic
    "diminished":        [0, 2, 3, 5, 6, 8, 9, 11], # whole-half octatonic
    "whole_tone":        [0, 2, 4, 6, 8, 10],       # symmetric; dreamlike, unstable
}


def pitch_name(pitch: int) -> str:
    octave = (pitch // 12) - 1  # MIDI 60 = C4 (middle C)
    return f"{NOTE_NAMES[pitch % 12]}{octave}"


def scale_pitches(scale: str, root: str, octave_range: tuple[int, int]) -> list[int]:
    offsets = SCALES[scale]
    root_offset = ROOTS[root]
    pitches = []
    for octave in range(octave_range[0], octave_range[1] + 1):
        base = (octave + 1) * 12 + root_offset
        for offset in offsets:
            pitches.append(base + offset)
    return pitches


def parsons_code(pitches: list[int]) -> str:
    out = []
    for prev, curr in zip(pitches, pitches[1:]):
        if curr > prev:
            out.append("U")
        elif curr < prev:
            out.append("D")
        else:
            out.append("R")
    return "".join(out)


def interval_sequence(pitches: list[int]) -> str:
    return " ".join(f"{curr - prev:+d}" for prev, curr in zip(pitches, pitches[1:]))


def chord_pitches(primary: int, chord_type: str, pool: list[int]) -> list[int]:
    """Return pitches to sound simultaneously with primary. Falls back to [primary] if companions aren't in pool."""
    if chord_type == "octave":
        for offset in (12, -12, 24, -24):
            if primary + offset in pool:
                return [primary, primary + offset]
    elif chord_type == "fifth":
        if primary + 7 in pool:
            return [primary, primary + 7]
    elif chord_type == "triad":
        thirds = [p for p in pool if 3 <= p - primary <= 5]
        fifths = [p for p in pool if 6 <= p - primary <= 8]
        result = [primary]
        if thirds:
            result.append(min(thirds, key=lambda p: p - primary))
        if fifths:
            result.append(min(fifths, key=lambda p: p - primary))
        return result
    return [primary]


def text_repr(pitches: list[int]) -> str:
    notes = " ".join(pitch_name(p) for p in pitches)
    return f"notes: {notes} | intervals: {interval_sequence(pitches)} | parsons: {parsons_code(pitches)}"
