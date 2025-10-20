from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SensorData(BaseModel):
    device_id: str
    timestamp: datetime   # ISO8601; Pydantic akan parsing
    lat: float
    lon: float
    pm_raw: float
    co2_raw: float
    temp: Optional[float] = None
    hum: Optional[float] = None
