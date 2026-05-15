#!/usr/bin/env python3
"""
agent.py — natural language interface for the player piano.

Usage:
    python agent.py

Requires ANTHROPIC_API_KEY in the environment.
"""
import json
import os
import time
from pathlib import Path

import anthropic

from db import (
    get_phrase_by_id,
    search_phrases as db_search_phrases,
    rate_phrase as db_rate_phrase,
    tag_phrase as db_tag_phrase,
    latest_phrase,
    get_profile,
)
from midi import make_midi_out
from music import voice_name

MOOD_PATH = Path(__file__).parent / "current_mood.json"
PROFILE_PATH = Path(__file__).parent / "current_profile.json"
MODEL = "claude-haiku-4-5"

# ── System prompt (cached) ─────────────────────────────────────────────────────

SYSTEM = [
    {
        "type": "text",
        "text": (
            "You are the control interface for a self-playing piano system built on a Yamaha DGX-505. "
            "The piano generates music continuously; your job is to help the user shape what it plays.\n\n"
            "Available scales: pentatonic_major, pentatonic_minor, major, minor, dorian, "
            "harmonic_minor, phrygian, phrygian_dominant, diminished, whole_tone\n\n"
            "Musician profiles:\n"
            '- "Keith Emerson": ELP-era prog rock — dramatic, angular, full keyboard range, '
            "harmonic minor/phrygian dominant/diminished, odd time signatures (5/8, 7/8, 11/8…), "
            "wide dynamics, drawbar organ and sawtooth lead alongside grand piano\n"
            '- "Gentle": soft ambient — warm pads and strings, pentatonic, slow, consonant, '
            "low velocity, background listening\n\n"
            "GM voice numbers in use: 0=Acoustic Grand Piano, 1=Bright Piano, 4=Electric Piano 1, "
            "5=Electric Piano 2, 16=Drawbar Organ, 17=Percussive Organ, 18=Rock Organ, "
            "19=Church Organ, 40=Violin, 48=String Ensemble 1, 49=String Ensemble 2, "
            "52=Choir Aahs, 80=Lead 1 Square, 81=Lead 2 Sawtooth, 88=Pad 1 New Age, 89=Pad 2 Warm\n\n"
            "Respond conversationally and concisely. When changing something, call the tool then confirm "
            "what changed. When replaying a phrase, briefly describe what the user will hear."
        ),
        "cache_control": {"type": "ephemeral"},
    }
]

# ── Tool definitions ───────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_status",
        "description": "Returns current mood settings, active profile, and last played phrase.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "set_mood",
        "description": (
            "Update one or more mood parameters. Only provided keys change; omitted keys keep "
            "their current values. Takes effect on the next generated phrase."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scale": {
                    "type": "string",
                    "enum": [
                        "pentatonic_major", "pentatonic_minor", "major", "minor", "dorian",
                        "harmonic_minor", "phrygian", "phrygian_dominant", "diminished", "whole_tone",
                    ],
                },
                "root": {
                    "type": "string",
                    "enum": [
                        "C", "C#", "Db", "D", "D#", "Eb", "E", "F",
                        "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
                    ],
                },
                "octave_range": {
                    "type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2,
                },
                "velocity_range": {
                    "type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2,
                },
                "note_duration_range": {
                    "type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
                },
                "gap_range": {
                    "type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
                },
            },
            "required": [],
        },
    },
    {
        "name": "set_profile",
        "description": (
            "Switch to a musician profile by name, or clear the active profile. "
            "Known profiles: 'Keith Emerson', 'Gentle'. Pass null to go unbiased."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "description": "Profile name, or null to clear.",
                    "oneOf": [{"type": "string"}, {"type": "null"}],
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "search_phrases",
        "description": (
            "Search phrase history by text query, rating, tag, scale, or profile. "
            "Returns phrase IDs with metadata and text representations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Full-text search across note names, intervals, and Parsons code.",
                },
                "min_rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "tag": {"type": "string"},
                "scale": {"type": "string"},
                "profile": {"type": "string"},
                "limit": {"type": "integer", "description": "Max results (default 5, max 20)."},
            },
            "required": [],
        },
    },
    {
        "name": "replay_phrase",
        "description": "Replay a phrase by ID on the piano using its original timing and notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phrase_id": {"type": "integer"},
                "voice": {
                    "type": "integer",
                    "description": "Override GM instrument number (0-127). Omit to use original.",
                },
            },
            "required": ["phrase_id"],
        },
    },
    {
        "name": "rate_phrase",
        "description": "Rate a phrase 1-5 stars by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phrase_id": {"type": "integer"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "required": ["phrase_id", "rating"],
        },
    },
    {
        "name": "tag_phrase",
        "description": "Add or remove a tag on a phrase by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phrase_id": {"type": "integer"},
                "tag": {"type": "string"},
                "remove": {"type": "boolean", "description": "True to remove instead of add."},
            },
            "required": ["phrase_id", "tag"],
        },
        "cache_control": {"type": "ephemeral"},  # cache tools block after first request
    },
]

# ── Tool implementations ───────────────────────────────────────────────────────

def exec_get_status() -> dict:
    mood = json.loads(MOOD_PATH.read_text())
    profile_data = json.loads(PROFILE_PATH.read_text()) if PROFILE_PATH.exists() else {}
    last = latest_phrase()
    last_info = None
    if last:
        v = last["params"].get("voice")
        last_info = {
            "id": last["id"],
            "created_at": last["created_at"],
            "scale": last["params"].get("scale"),
            "root": last["params"].get("root"),
            "voice": v,
            "voice_name": voice_name(v) if v is not None else None,
            "tempo_bpm": last["params"].get("tempo_bpm"),
            "time_sig": last["params"].get("time_sig"),
            "rating": last.get("rating"),
            "tags": last.get("tags", []),
            "text_repr": last.get("text_repr"),
        }
    return {"mood": mood, "profile": profile_data.get("name"), "last_phrase": last_info}


def exec_set_mood(updates: dict) -> dict:
    mood = json.loads(MOOD_PATH.read_text())
    mood.update(updates)
    MOOD_PATH.write_text(json.dumps(mood, indent=2))
    return {"ok": True, "mood": mood}


def exec_set_profile(name: str | None) -> dict:
    if name is None:
        PROFILE_PATH.write_text(json.dumps({}))
        return {"ok": True, "profile": None}
    profile = get_profile(name)
    if profile is None:
        return {"ok": False, "error": f"Profile '{name}' not found. Run seed_profiles.py first."}
    PROFILE_PATH.write_text(json.dumps({"name": name}))
    return {"ok": True, "profile": name}


def exec_search_phrases(
    query: str = "",
    min_rating: int | None = None,
    tag: str | None = None,
    scale: str | None = None,
    profile: str | None = None,
    limit: int = 5,
) -> dict:
    limit = min(int(limit), 20)
    rows = db_search_phrases(
        query=query, min_rating=min_rating, tag=tag, scale=scale, profile=profile, limit=limit
    )
    results = []
    for r in rows:
        v = r["params"].get("voice")
        results.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "scale": r["params"].get("scale"),
            "root": r["params"].get("root"),
            "voice": v,
            "voice_name": voice_name(v) if v is not None else None,
            "rating": r.get("rating"),
            "tags": r.get("tags", []),
            "profile": r.get("profile_name"),
            "text_repr": r.get("text_repr", ""),
        })
    return {"count": len(results), "phrases": results}


def exec_replay_phrase(midi_out, phrase_id: int, voice: int | None = None) -> dict:
    phrase = get_phrase_by_id(phrase_id)
    if phrase is None:
        return {"ok": False, "error": f"Phrase {phrase_id} not found."}
    notes = phrase["notes"]
    actual_voice = voice if voice is not None else phrase["params"].get("voice")
    if actual_voice is not None:
        midi_out.set_voice(actual_voice)
    phrase_start = time.monotonic()
    for event in notes:
        target = phrase_start + event["time_ms"] / 1000.0
        wait = target - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        to_play = [event["pitch"]] + event.get("chord", [])
        for p in to_play:
            midi_out.note_on(p, event["velocity"])
        time.sleep(event["duration_ms"] / 1000.0)
        for p in to_play:
            midi_out.note_off(p)
    return {
        "ok": True,
        "phrase_id": phrase_id,
        "notes_played": len(notes),
        "voice": actual_voice,
        "voice_name": voice_name(actual_voice) if actual_voice is not None else None,
    }


def exec_rate_phrase(phrase_id: int, rating: int) -> dict:
    db_rate_phrase(phrase_id, rating)
    return {"ok": True, "phrase_id": phrase_id, "rating": rating}


def exec_tag_phrase(phrase_id: int, tag: str, remove: bool = False) -> dict:
    db_tag_phrase(phrase_id, tag, remove)
    return {"ok": True, "phrase_id": phrase_id, "tag": tag, "removed": remove}


# ── Agentic loop ───────────────────────────────────────────────────────────────

def dispatch_tool(name: str, inputs: dict, midi_out) -> str:
    try:
        if name == "get_status":
            result = exec_get_status()
        elif name == "set_mood":
            result = exec_set_mood(inputs)
        elif name == "set_profile":
            result = exec_set_profile(inputs.get("name"))
        elif name == "search_phrases":
            allowed = ("query", "min_rating", "tag", "scale", "profile", "limit")
            result = exec_search_phrases(**{k: v for k, v in inputs.items() if k in allowed})
        elif name == "replay_phrase":
            result = exec_replay_phrase(midi_out, inputs["phrase_id"], inputs.get("voice"))
        elif name == "rate_phrase":
            result = exec_rate_phrase(inputs["phrase_id"], inputs["rating"])
        elif name == "tag_phrase":
            result = exec_tag_phrase(inputs["phrase_id"], inputs["tag"], inputs.get("remove", False))
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        result = {"error": str(exc)}
    return json.dumps(result)


def run_turn(client: anthropic.Anthropic, history: list, midi_out) -> str:
    """Drive a single conversational turn, executing tools until Claude finishes."""
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=history,
        )
        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return "\n".join(
                b.text for b in response.content if hasattr(b, "text")
            )

        if response.stop_reason != "tool_use":
            return f"[unexpected stop_reason: {response.stop_reason}]"

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  [{block.name}]", flush=True)
            result_str = dispatch_tool(block.name, block.input, midi_out)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str,
            })

        history.append({"role": "user", "content": tool_results})


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — export it before running agent.py")

    client = anthropic.Anthropic(api_key=api_key)
    midi_out = make_midi_out()
    history: list = []

    print("Player Piano Agent  (Ctrl-C to quit)", flush=True)
    print('Try: "what\'s playing?", "switch to Keith Emerson", "find highly rated phrases"', flush=True)
    print()

    try:
        while True:
            try:
                user_input = input("> ").strip()
            except EOFError:
                break
            if not user_input:
                continue
            history.append({"role": "user", "content": user_input})
            reply = run_turn(client, history, midi_out)
            print(f"\n{reply}\n", flush=True)
    except KeyboardInterrupt:
        print("\n[stopped]", flush=True)
    finally:
        midi_out.set_pitch_bend(0)
        midi_out.close()


if __name__ == "__main__":
    main()
