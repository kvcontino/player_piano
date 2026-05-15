import sqlite3
from db import insert_profile

PROFILES = [
    {
        "name": "Keith Emerson",
        "description": (
            "ELP-era prog rock: harmonic minor, phrygian dominant, and diminished scales. "
            "Dramatic interval leaps, wide dynamics (near-silent to fortissimo), fast runs "
            "to long held notes, full keyboard range. Angular and theatrical."
        ),
        "traits": {
            "scales": ["harmonic_minor", "phrygian_dominant", "diminished"],
            "octave_range": [2, 6],
            "velocity_range": [25, 115],
            "note_duration_range": [0.07, 2.0],
            "gap_range": [0.0, 0.2],
            "n_notes_range": [8, 16],
            "interval_leap_prob": 0.55,
        },
    },
]

if __name__ == "__main__":
    for p in PROFILES:
        try:
            pid = insert_profile(p["name"], p["description"], p["traits"])
            print(f"Inserted profile {pid}: {p['name']}")
        except sqlite3.IntegrityError:
            print(f"Profile '{p['name']}' already exists — skipped")
