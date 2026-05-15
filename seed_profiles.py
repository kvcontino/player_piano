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
        },
    },
]

if __name__ == "__main__":
    for p in PROFILES:
        pid = upsert_profile(p["name"], p["description"], p["traits"])
        print(f"Upserted profile {pid}: {p['name']}")
