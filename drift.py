import time


def _lerp(a, b, t: float):
    """Interpolate a→b by factor t. Preserves int type for integer inputs."""
    if isinstance(a, list) and isinstance(b, list):
        return [_lerp(x, y, t) for x, y in zip(a, b)]
    result = a + (b - a) * t
    return int(round(result)) if isinstance(a, int) and isinstance(b, int) else result


class Drift:
    """
    Linearly interpolates numeric session parameters from their start values toward
    target values over a configured duration.

    Config format (inside current_layers.json under "drift"):
        {
          "duration_minutes": 45,
          "bpm":            {"from": 52, "to": 44},
          "velocity_range": {"from": [30, 55], "to": [20, 40]},
          "legato":         {"from": 0.92, "to": 0.97},
          "gap_range":      {"from": [0.3, 1.2], "to": [0.6, 2.5]},
          "chord_prob":     {"from": 0.2, "to": 0.05}
        }

    "from" is optional for any key except "bpm" — it falls back to the live param
    value at apply time, so you can specify only the target.

    Applied after merge_traits() so drift overrides both mood and profile values.
    """

    def __init__(self, config: dict, start_time: float, base_bpm: float = 88.0):
        self._duration_s = config.get("duration_minutes", 60) * 60
        self._start = start_time
        self._base_bpm = base_bpm
        self._specs: dict[str, dict] = {
            k: v for k, v in config.items() if k != "duration_minutes"
        }

    def factor(self) -> float:
        return min(1.0, (time.monotonic() - self._start) / self._duration_s)

    def apply_to_params(self, params: dict) -> dict:
        """Return a copy of params with drifted values interpolated in."""
        f = self.factor()
        result = dict(params)
        for key, spec in self._specs.items():
            if key == "bpm":
                continue
            src = spec.get("from", result.get(key))
            dst = spec.get("to")
            if src is None or dst is None:
                continue
            result[key] = _lerp(src, dst, f)
        return result

    def current_bpm(self) -> float:
        spec = self._specs.get("bpm")
        if spec is None:
            return self._base_bpm
        src = float(spec.get("from", self._base_bpm))
        return float(_lerp(src, float(spec["to"]), self.factor()))
