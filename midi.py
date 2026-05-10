from __future__ import annotations
import os
from abc import ABC, abstractmethod


class MidiOut(ABC):
    @abstractmethod
    def note_on(self, pitch: int, velocity: int) -> None: ...

    @abstractmethod
    def note_off(self, pitch: int) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


def _pitch_name(pitch: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (pitch // 12) - 1  # MIDI 60 = C4 (middle C)
    return f"{names[pitch % 12]}{octave}"


class MockMidiOut(MidiOut):
    def note_on(self, pitch: int, velocity: int) -> None:
        print(f"ON   {_pitch_name(pitch):>4}  vel={velocity}", flush=True)

    def note_off(self, pitch: int) -> None:
        print(f"OFF  {_pitch_name(pitch):>4}", flush=True)

    def close(self) -> None:
        pass


class RealMidiOut(MidiOut):
    def __init__(self, port_name: str):
        import mido  # lazy: only required for the real backend
        self._port = mido.open_output(port_name)
        self._mido = mido

    def note_on(self, pitch: int, velocity: int) -> None:
        self._port.send(self._mido.Message("note_on", note=pitch, velocity=velocity))

    def note_off(self, pitch: int) -> None:
        self._port.send(self._mido.Message("note_off", note=pitch))

    def close(self) -> None:
        self._port.close()


def make_midi_out() -> MidiOut:
    backend = os.environ.get("MIDI_BACKEND", "mock").lower()
    if backend == "mock":
        return MockMidiOut()
    if backend == "real":
        port = os.environ.get("MIDI_PORT_NAME")
        if not port:
            raise RuntimeError(
                "MIDI_BACKEND=real requires MIDI_PORT_NAME. "
                "List ports: python -c 'import mido; print(mido.get_output_names())'"
            )
        return RealMidiOut(port)
    raise ValueError(f"Unknown MIDI_BACKEND: {backend!r}")
