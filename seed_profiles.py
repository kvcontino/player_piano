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
]

if __name__ == "__main__":
    for p in PROFILES:
        pid = upsert_profile(p["name"], p["description"], p["traits"])
        print(f"Upserted profile {pid}: {p['name']}")
