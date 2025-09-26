from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pytz
import pandas as pd

from influxdb_client.rest import ApiException
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Konfigurasi InfluxDB ---
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "FQCPt1ZITiPc5nk5Nbx2aPv8tkbce1GWElL_9qca0XKBFcqWetIvdn948xBOGiYxx6PRDHssWYId9Jn_nSZfPw=="
ORG = "sesa"
BUCKET = "air-quality"

# --- Init FastAPI ---
app = FastAPI()

# --- Client ---
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

# --- Model Data Sensor ---
class SensorData(BaseModel):
    device_id: str
    timestamp: datetime
    lat: float
    lon: float
    pm_raw: float
    co2_raw: float
    temp: Optional[float] = None
    hum: Optional[float] = None

# --- Fungsi Menulis Data ---
def write_raw(sensor: SensorData):
    """
    Menulis data sensor ke InfluxDB (bucket air-quality)
    """
    try:
        # Pastikan timestamp UTC aware
        ts_utc = sensor.timestamp
        if ts_utc.tzinfo is None:
            ts_utc = ts_utc.replace(tzinfo=pytz.UTC)
        else:
            ts_utc = ts_utc.astimezone(pytz.UTC)

        # Buat point
        p = (
            Point("raw_readings")
            .tag("device_id", sensor.device_id)
            .tag("lat", str(sensor.lat))  # tag karena jarang berubah
            .tag("lon", str(sensor.lon))
            .field("pm_raw", float(sensor.pm_raw))
            .field("co2_raw", float(sensor.co2_raw))
        )

        if sensor.temp is not None:
            p = p.field("temp", float(sensor.temp))
        if sensor.hum is not None:
            p = p.field("hum", float(sensor.hum))

        # Timestamp dengan presisi nanosecond
        p = p.time(int(ts_utc.timestamp() * 1e9), WritePrecision.NS)

        # Debug: lihat line protocol
        print("[DEBUG] Line Protocol:", p.to_line_protocol())

        # Tulis ke InfluxDB
        write_api.write(bucket=BUCKET, org=ORG, record=p)
        print(f"[{datetime.now()}] [WRITE] Data berhasil disimpan!")

    except ApiException as e:
        print(f"[{datetime.now()}] [WRITE] Gagal menulis ke InfluxDB: {e.body}")
        raise HTTPException(status_code=500, detail=f"Gagal menulis ke database: {e.body}")

    except Exception as e:
        print(f"[{datetime.now()}] [WRITE] Error umum saat memproses data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saat memproses data: {str(e)}")

def query_tabular(measurement: str, start: str = "-1h"):
    """
    Query data dari Influx, pivot supaya _field jadi kolom.
    """
    q = f'''
    from(bucket:"{BUCKET}")
    |> range(start: {start})
    |> filter(fn:(r) => r._measurement == "{measurement}")
    |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
    '''
    df = query_api.query_data_frame(org=ORG, query=q)

    if isinstance(df, list):
        df = pd.concat(df)

    if not df.empty:
        df = df.reset_index(drop=True)

    return df

