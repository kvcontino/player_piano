from db import upsert_profile

PROFILES = [
    {
        "name": "Keith Emerson",
        "description": (
            "ELP-era prog rock: harmonic minor, phrygian dominant, and diminished scales. "
            "Dramatic interval leaps, wide dynamics (near-silent to fortissimo), fast runs "
            "to long held notes, full keyboard range. Angular and theatrical. "
            "Voices rotate across his four signature instruments."
        ),
        "traits": {
            "scales": ["harmonic_minor", "phrygian_dominant", "diminished"],
            "voices": [0, 16, 19, 81],  # Grand Piano, Drawbar Organ, Church Organ, Sawtooth Lead
            "octave_range": [2, 6],
            "velocity_range": [25, 115],
            "note_duration_range": [0.07, 2.0],
            "gap_range": [0.0, 0.2],
            "n_notes_range": [8, 16],
            "interval_leap_prob": 0.55,
            "sustain_prob": 0.7,
            "chord_prob": 0.45,
            "chord_types": ["octave", "fifth", "triad"],
            "bend_prob": 0.3,
            "bend_styles": ["slide_in", "fall_off"],
            "bend_semitones": 1.5,
            "tempo_bpm": 88,
            "time_sigs": [[4, 4], [5, 8], [7, 8], [5, 4], [7, 4], [6, 8], [11, 8], [3, 4]],
            "n_bars": 2,
            "note_values": [0.5, 0.5, 0.5, 1.0, 1.0, 2.0],
            "legato": 0.78,
        },
    },
    {
        "name": "Bass",
        "description": (
            "Simple supportive bass line. Root motion, fifths, and occasional octaves. "
            "Low register, long notes, sparse activity. Grounds whatever is above it. "
            "Works under any harmonic context — pentatonic keeps it neutral."
        ),
        "traits": {
            "scales": ["pentatonic_minor", "pentatonic_major"],
            "voices": [32, 33, 35],  # Acoustic Bass, Electric Bass Finger, Fretless Bass
            "octave_range": [1, 2],
            "velocity_range": [45, 75],
            "note_duration_range": [0.4, 2.0],
            "gap_range": [0.1, 0.6],
            "n_notes_range": [3, 6],
            "interval_leap_prob": 0.2,
            "sustain_prob": 0.3,
            "chord_prob": 0.15,
            "chord_types": ["octave", "fifth"],
            "bend_prob": 0.0,
            "tempo_bpm": 80,  # overridden by global clock in layered mode
            "time_sig": [4, 4],
            "n_bars": 2,
            "note_values": [1.0, 1.0, 2.0, 4.0],
            "legato": 0.65,
        },
    },
    {
        "name": "Gentle",
        "description": (
            "Slow, soft, consonant ambient. Pentatonic major, warm pad and string voices, "
            "mostly stepwise motion, light chords, heavy sustain. Low velocity throughout. "
            "Designed for background listening — or cats."
        ),
        "traits": {
            "scales": ["pentatonic_major", "pentatonic_minor"],
            "voices": [48, 88, 89],  # String Ensemble 1, Pad 1 (New Age), Pad 2 (Warm)
            "octave_range": [3, 5],
            "velocity_range": [20, 55],
            "note_duration_range": [0.5, 3.0],
            "gap_range": [0.3, 1.2],
            "n_notes_range": [6, 10],
            "interval_leap_prob": 0.1,
            "sustain_prob": 0.85,
            "chord_prob": 0.2,
            "chord_types": ["fifth", "octave"],
            "tempo_bpm": 52,
            "time_sig": [3, 4],
            "n_bars": 4,
            "note_values": [1.0, 1.0, 2.0, 3.0],
            "legato": 0.92,
        },
    },
    {
        "name": "Relax",
        "description": (
            "Near-silence made audible. Glacially slow, extremely soft, sparse single notes "
            "on evolving pad voices (Bowed Glass, Halo, Sweep). Whole-tone and pentatonic "
            "scales, almost no leaps, very long sustained notes with wide gaps. "
            "Dissolves into the room."
        ),
        "traits": {
            "scales": ["pentatonic_major", "whole_tone"],
            "voices": [92, 94, 95],  # Pad 5 (Bowed Glass), Pad 7 (Halo), Pad 8 (Sweep)
            "octave_range": [3, 5],
            "velocity_range": [8, 28],
            "note_duration_range": [1.5, 6.0],
            "gap_range": [1.0, 4.0],
            "n_notes_range": [3, 6],
            "interval_leap_prob": 0.05,
            "sustain_prob": 0.98,
            "chord_prob": 0.1,
            "chord_types": ["fifth"],
            "tempo_bpm": 38,
            "time_sig": [3, 4],
            "n_bars": 4,
            "note_values": [2.0, 3.0, 4.0],
            "legato": 0.97,
        },
    },
]

if __name__ == "__main__":
    for p in PROFILES:
        pid = upsert_profile(p["name"], p["description"], p["traits"])
        print(f"Upserted profile {pid}: {p['name']}")
