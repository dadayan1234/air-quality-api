from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pytz
import pandas as pd

from influxdb_client.rest import ApiException
from influxdb_client.client.influxdb_client import InfluxDBClient 
from influxdb_client.client.write.point import Point
from influxdb_client.domain.write_precision import WritePrecision
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

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

def _ensure_df(result):
    # query_data_frame may return list of DataFrames or DataFrame
    if isinstance(result, list):
        df = pd.concat(result, ignore_index=True)
    else:
        df = result
    if df.empty:
        return df
    # Normalize column names: Influx pivot returns _time as timestamp
    if "_time" in df.columns:
        df = df.rename(columns={"_time": "time"})
    # Reset index for clean iteration
    return df.reset_index(drop=True)

def write_raw(sensor):
    """
    sensor: pydantic model (SensorData) or object with attributes
    Writes to measurement 'raw_readings'
    """
    try:
        ts = sensor.timestamp
        # make timezone-aware UTC
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=pytz.UTC)
        else:
            ts = ts.astimezone(pytz.UTC)

        p = (
            Point("raw_readings")
            .tag("device_id", sensor.device_id)
            .tag("lat", f"{sensor.lat:.6f}")
            .tag("lon", f"{sensor.lon:.6f}")
            .field("pm_raw", float(sensor.pm_raw))
            .field("co2_raw", float(sensor.co2_raw))
        )
        if sensor.temp is not None:
            p = p.field("temp", float(sensor.temp))
        if sensor.hum is not None:
            p = p.field("hum", float(sensor.hum))

        p = p.time(int(ts.timestamp() * 1e9), WritePrecision.NS)
        write_api.write(bucket=BUCKET, org=ORG, record=p)
    except ApiException as e:
        raise RuntimeError(f"InfluxDB write error: {e.body}")
    except Exception as e:
        raise

def write_reference_point(device_id: str, lat: float, lon: float, pm25_ref: float | None,
                          co_ref: float | None, timestamp):
    """Write a reference_readings point (from AQICN) associated to a device_id and time"""
    try:
        ts = timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=pytz.UTC)
        else:
            ts = ts.astimezone(pytz.UTC)

        p = (
            Point("reference_readings")
            .tag("device_id", device_id)
            .tag("lat", f"{lat:.6f}")
            .tag("lon", f"{lon:.6f}")
        )
        if pm25_ref is not None:
            p = p.field("pm25_ref", float(pm25_ref))
        if co_ref is not None:
            p = p.field("co_ref", float(co_ref))
        p = p.time(int(ts.timestamp() * 1e9), WritePrecision.NS)
        write_api.write(bucket=BUCKET, org=ORG, record=p)
    except Exception as e:
        raise

def query_tabular(measurement: str, start: str = "-1h"):
    """
    Returns a pandas.DataFrame pivoted so fields become columns.
    'start' is Flux range spec like '-1h' or '2025-09-01T00:00:00Z'
    """
    q = f'''
    from(bucket:"{BUCKET}")
    |> range(start: {start})
    |> filter(fn: (r) => r._measurement == "{measurement}")
    |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
    '''
    df = query_api.query_data_frame(org=ORG, query=q)
    return _ensure_df(df)

