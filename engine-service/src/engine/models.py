from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class EngineOutput:
    speed_ms: float
    power_w: float
    cadence_rpm: Optional[float] = None
    heart_rate_bpm: Optional[int] = None
    resistance_level: Optional[int] = None
    average_power_w: Optional[int] = None
    total_distance_m: Optional[int] = None
    connected: bool = False
    device_name: Optional[str] = None

    def to_message(self) -> dict:
        return {"type": "engine_output", "data": asdict(self)}
