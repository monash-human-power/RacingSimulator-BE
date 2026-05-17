"""BLE engine service — FTMS trainer connection and live telemetry."""

from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from bluetooth import BLEManager
from bluetooth.kickr import is_kickr
from engine import Engine
from websocket.routes import manager as websocket_manager
from websocket.routes import router as websocket_router

import os

manager = BLEManager()
engine = Engine()
engine.websocket_manager = websocket_manager
manager.set_bike_data_callback(engine.on_bike_data)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _serialize(obj: Any) -> Any:
    if obj is None:
        return None
    if is_dataclass(obj):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if hasattr(obj, "value"):  # IntEnum
        return obj.value
    return obj


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await manager.start()
    yield
    await manager.stop()


app = FastAPI(title="Racing Simulator Engine", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(websocket_router)


class ConnectBody(BaseModel):
    address: Optional[str] = None


class TargetPowerBody(BaseModel):
    watts: int = Field(ge=0, le=4000)


class TargetResistanceBody(BaseModel):
    level: int


class SimulationBody(BaseModel):
    grade_pct: float = 0.0
    wind_speed_ms: float = 0.0
    crr: float = 0.004
    cda: float = 0.51


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/state")
def get_state():
    ble = _serialize(manager.state)
    eng = _serialize(engine.state)
    return {
        "connected": manager.is_connected,
        "ble": ble,
        "engine": eng,
    }


@app.get("/scan")
async def scan_devices():
    from bleak import BleakScanner

    devices = await BleakScanner.discover(timeout=10.0)
    return [
        {
            "name": d.name or "Unknown",
            "address": d.address,
            "isTrainer": is_kickr(d.name),
        }
        for d in devices
    ]


@app.post("/connect")
async def connect_device(body: ConnectBody):
    ok = await manager.connect(body.address)
    if not ok:
        raise HTTPException(status_code=404, detail="No compatible trainer found")
    return {"connected": True, "device": _serialize(manager.state)}


@app.post("/disconnect")
async def disconnect_device():
    await manager.stop()
    await manager.start()
    return {"connected": False}


@app.post("/control/target-power")
async def set_target_power(body: TargetPowerBody):
    resp = await manager.set_target_power(body.watts)
    return {"ok": resp.ok, "status": int(resp.status), "targetPowerW": body.watts}


@app.post("/control/target-resistance")
async def set_target_resistance(body: TargetResistanceBody):
    resp = await manager.set_target_resistance(body.level)
    return {"ok": resp.ok, "status": int(resp.status), "targetResistanceLevel": body.level}


@app.post("/control/simulation")
async def set_simulation(body: SimulationBody):
    resp = await manager.set_simulation(
        grade_pct=body.grade_pct,
        wind_speed_ms=body.wind_speed_ms,
        crr=body.crr,
        cda=body.cda,
    )
    return {"ok": resp.ok, "status": int(resp.status), "gradePct": body.grade_pct}
