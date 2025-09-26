from fastapi import FastAPI, HTTPException
from .models import SensorData
from .influx import write_raw, query_tabular, write_api
from .aqicn import fetch_aqicn, fetch_aqicn_station
from .calibration import fit_linear_calibration
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess
from pathlib import Path

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Start InfluxDB process when the application starts
def start_influxdb():
    try:
        # Get the parent directory of the current directory
        parent_dir = str(Path(__file__).parent.parent)
        
        # Start influxd process
        subprocess.Popen(
            ["influxd"],
            cwd=parent_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except Exception as e:
        print(f"Error starting InfluxDB: {e}")

# Start InfluxDB when the application starts
start_influxdb()

@app.post("/api/v1/ingest")
def ingest(sensor: SensorData):
    write_raw(sensor) # type: ignore
    return {"status": "ok", "message": "Data berhasil disimpan"}


@app.get("/api/v1/aqicn")
def get_aqicn(lat: float, lon: float):
    # fetch_aqicn sudah raise HTTPException kalau error
    data = fetch_aqicn(lat, lon)
    return data

@app.get("/api/v1/aqicn/sleman")
def get_aqicn_sleman():
    # Station ID Sleman: 13653
    return fetch_aqicn_station(13653)

@app.post("/api/v1/calibrate/{device_id}")
def calibrate(device_id: str):
    try:
        df_raw = query_tabular("raw_readings")
        df_ref = query_tabular("reference_readings")

        df_device = df_raw[df_raw["device_id"] == device_id].copy()

        if df_device.empty or df_ref.empty:
            return {"status": "error", "message": "Data tidak cukup untuk kalibrasi"}

        df_device["time"] = pd.to_datetime(df_device["time"])
        df_ref["time"] = pd.to_datetime(df_ref["time"])

        df_pair = pd.merge_asof(
            df_device.sort_values("time"),
            df_ref.sort_values("time"),
            on="time",
            direction="nearest",
            tolerance=pd.Timedelta("1min")
        )

        if df_pair.dropna().empty:
            return {"status": "error", "message": "Tidak ada pasangan data raw vs referensi"}

        slope_pm, intercept_pm, r2_pm = fit_linear_calibration(df_pair["pm_raw"], df_pair["pm25_ref"])
        slope_co2, intercept_co2, r2_co2 = fit_linear_calibration(df_pair["co2_raw"], df_pair["co_ref"])

        write_api.write(
            bucket="calibration_params",
            record={
                "measurement": "calibration",
                "tags": {"device_id": device_id},
                "fields": {
                    "slope_pm": float(slope_pm),
                    "intercept_pm": float(intercept_pm),
                    "r2_pm": float(r2_pm),
                    "slope_co2": float(slope_co2),
                    "intercept_co2": float(intercept_co2),
                    "r2_co2": float(r2_co2),
                }
            }
        )

        return {
            "status": "ok",
            "message": "Kalibrasi berhasil",
            "params": {
                "pm": {"a": slope_pm, "b": intercept_pm, "r2": r2_pm},
                "co2": {"a": slope_co2, "b": intercept_co2, "r2": r2_co2}
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal kalibrasi: {str(e)}")

@app.get("/api/v1/readings")
def get_readings(measurement: str = "raw_readings", start: str = "-1h"):
    try:
        df = query_tabular(measurement, start)

        if df.empty:
            return {"status": "ok", "data": []}

        # Rename / map columns from Influx → Frontend
        mapped_data = []
        for _, row in df.iterrows():
            mapped_data.append({
                "device_id": row.get("device_id"),
                "pm_raw": row.get("pm_raw"),
                "co2_raw": row.get("co2_raw"),
                "temperature": row.get("temp"),   # temp → temperature
                "humidity": row.get("hum"),       # hum → humidity
                "time": row.get("_time"),         # _time → time
            })

        return {"status": "ok", "data": mapped_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal ambil data: {str(e)}")



@app.get("/api/v1/forecast/{device_id}")
def forecast(device_id: str):
    return {"status":"not_implemented","message":"Forecast belum diimplementasikan"}
