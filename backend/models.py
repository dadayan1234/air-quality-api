from pydantic import BaseModel
from datetime import datetime

class SensorData(BaseModel):
    device_id: str
    timestamp: datetime   # Pydantic otomatis parse dari ISO8601
    lat: float
    lon: float
    pm_raw: float
    co2_raw: float
    temp: float | None = None
    hum: float | None = None
