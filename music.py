NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

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


def text_repr(pitches: list[int]) -> str:
    notes = " ".join(pitch_name(p) for p in pitches)
    return f"notes: {notes} | intervals: {interval_sequence(pitches)} | parsons: {parsons_code(pitches)}"
