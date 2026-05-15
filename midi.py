from __future__ import annotations
import os
from abc import ABC, abstractmethod

from music import pitch_name, voice_name


class MidiOut(ABC):
    @abstractmethod
    def note_on(self, pitch: int, velocity: int, channel: int = 0) -> None: ...

    @abstractmethod
    def note_off(self, pitch: int, channel: int = 0) -> None: ...

    @abstractmethod
    def set_voice(self, program: int, channel: int = 0) -> None: ...

    @abstractmethod
    def set_pitch_bend(self, value: int, channel: int = 0) -> None: ...

    @abstractmethod
    def set_sustain(self, on: bool, channel: int = 0) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class MockMidiOut(MidiOut):
    def note_on(self, pitch: int, velocity: int, channel: int = 0) -> None:
        ch = f" ch{channel}" if channel else ""
        print(f"ON   {pitch_name(pitch):>4}  vel={velocity}{ch}", flush=True)

    def note_off(self, pitch: int, channel: int = 0) -> None:
        ch = f" ch{channel}" if channel else ""
        print(f"OFF  {pitch_name(pitch):>4}{ch}", flush=True)

    def set_voice(self, program: int, channel: int = 0) -> None:
        ch = f" ch{channel}" if channel else ""
        print(f"VOICE {program:3d}  {voice_name(program)}{ch}", flush=True)

    def set_pitch_bend(self, value: int, channel: int = 0) -> None:
        pass  # silent in mock — too noisy for 10-step ramps

    def set_sustain(self, on: bool, channel: int = 0) -> None:
        ch = f" ch{channel}" if channel else ""
        print(f"SUSTAIN {'ON ' if on else 'OFF'}{ch}", flush=True)

    def close(self) -> None:
        pass


class RealMidiOut(MidiOut):
    def __init__(self, port_name: str):
        import mido  # lazy: only required for the real backend
        self._port = mido.open_output(port_name)
        self._mido = mido

    def note_on(self, pitch: int, velocity: int, channel: int = 0) -> None:
        self._port.send(self._mido.Message("note_on", note=pitch, velocity=velocity, channel=channel))

    def note_off(self, pitch: int, channel: int = 0) -> None:
        self._port.send(self._mido.Message("note_off", note=pitch, channel=channel))

    def set_voice(self, program: int, channel: int = 0) -> None:
        self._port.send(self._mido.Message("program_change", channel=channel, program=program))

    def set_pitch_bend(self, value: int, channel: int = 0) -> None:
        self._port.send(self._mido.Message("pitchwheel", channel=channel, pitch=value))

    def set_sustain(self, on: bool, channel: int = 0) -> None:
        self._port.send(self._mido.Message(
            "control_change", channel=channel, control=64, value=127 if on else 0
        ))

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
