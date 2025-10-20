# app/main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import SensorData
from .influx import write_raw, write_reference_point, query_tabular
from .aqicn import fetch_aqicn, fetch_aqicn_station
from .calibration import fit_linear_calibration
from datetime import timezone
import pandas as pd
from math import radians, sin, cos, sqrt, atan2

app = FastAPI(title="AQI Calibration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Utilities ----------
def haversine_m(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/lon points."""
    R = 6371000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2.0)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2.0)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# ---------- Endpoints ----------
@app.post("/api/v1/ingest")
def ingest(sensor: SensorData):
    """
    Ingest raw sensor data, write to Influx, then fetch QC reference from AQICN
    and store as reference_readings (tagged by device_id and lat/lon).
    """
    try:
        # 1) store raw
        write_raw(sensor)

        # 2) try fetch AQICN for that lat/lon (graceful if fails)
        try:
            ref = fetch_aqicn(sensor.lat, sensor.lon)
        except HTTPException:
            ref = None

        if ref and ref.get("pm25") is not None:
            # timestamp of reference use ref time if present, else sensor timestamp
            time_utc = None
            if ref.get("time", {}).get("utc"):
                # isoformat string -> parse
                time_utc = pd.to_datetime(ref["time"]["utc"], utc=True).to_pydatetime()
            else:
                time_utc = sensor.timestamp
                if time_utc.tzinfo is None:
                    time_utc = time_utc.replace(tzinfo=timezone.utc)

            write_reference_point(
                device_id=sensor.device_id,
                lat=sensor.lat,
                lon=sensor.lon,
                pm25_ref=ref.get("pm25"),
                co_ref=ref.get("co"),
                timestamp=time_utc
            )

        return {"status": "ok", "message": "ingest successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/aqicn")
def get_aqicn(lat: float, lon: float):
    return fetch_aqicn(lat, lon)

@app.get("/api/v1/aqicn/sleman")
def get_aqicn_sleman():
    return fetch_aqicn_station(13653)

@app.post("/api/v1/calibrate/{device_id}")
def calibrate(device_id: str, start: str = "-7d", max_distance_m: int = 1000):
    """
    Calibrate device by pairing raw_readings with reference_readings.
    - start: flux range for querying (e.g. '-7d', '-1d', '-24h')
    - max_distance_m: maximum distance (meters) allowed for pairing (default 1000 m)
    Returns calibration params and pairing metadata.
    """
    try:
        df_raw = query_tabular("raw_readings", start)
        df_ref = query_tabular("reference_readings", start)

        if df_raw.empty or df_ref.empty:
            return {"status": "error", "message": "Tidak cukup data (raw or reference empty)"}

        # Filter device raw
        df_dev = df_raw[df_raw["device_id"] == device_id].copy()
        if df_dev.empty:
            return {"status": "error", "message": "Tidak ada data raw untuk device ini"}

        # Ensure datetime columns
        df_dev["time"] = pd.to_datetime(df_dev["time"], utc=True)
        df_ref["time"] = pd.to_datetime(df_ref["time"], utc=True)

        # Merge_asof: pair sensor -> nearest reference in time (tolerance 30m by default)
        df_dev_sorted = df_dev.sort_values("time").reset_index(drop=True)
        df_ref_sorted = df_ref.sort_values("time").reset_index(drop=True)

        df_pair = pd.merge_asof(
            left=df_dev_sorted,
            right=df_ref_sorted,
            on="time",
            suffixes=("_raw", "_ref"),
            direction="nearest",
            tolerance=pd.Timedelta("30m")
        )

        # drop rows with missing paired reference fields
        df_pair = df_pair.dropna(subset=["pm25_ref"])

        if df_pair.empty:
            return {"status": "error", "message": "Tidak ada pasangan valid (time tolerance) atau referensi null"}

        # compute spatial distance between device coords and reference coords (use tags lat/lon)
        def parse_coord(x):
            try:
                return float(x)
            except Exception:
                return None

        df_pair["lat_raw"] = df_pair["lat_raw"].astype(float)
        df_pair["lon_raw"] = df_pair["lon_raw"].astype(float)
        # reference might be stored as tags lat_ref/lon_ref or as fields - handle both
        if "lat_ref" in df_pair.columns and "lon_ref" in df_pair.columns:
            df_pair["lat_ref"] = df_pair["lat_ref"].astype(float)
            df_pair["lon_ref"] = df_pair["lon_ref"].astype(float)
        else:
            # fallback: use device lat/lon for both (distance 0)
            df_pair["lat_ref"] = df_pair["lat_raw"]
            df_pair["lon_ref"] = df_pair["lon_raw"]

        df_pair["distance_m"] = df_pair.apply(
            lambda r: haversine_m(r["lat_raw"], r["lon_raw"], r["lat_ref"], r["lon_ref"]),
            axis=1
        )

        # Filter by spatial threshold
        df_pair = df_pair[df_pair["distance_m"] <= max_distance_m]

        if df_pair.empty:
            return {"status": "error", "message": f"Tidak ada pasangan dalam radius {max_distance_m} m"}

        # Fit linear calibration for PM2.5
        a_pm, b_pm, rmse_pm = fit_linear_calibration(df_pair["pm_raw"], df_pair["pm25_ref"])
        # Fit for CO (if present)
        co_pairs = df_pair.dropna(subset=["co_ref", "co2_raw"]) if "co2_raw" in df_pair.columns else df_pair.dropna(subset=["co_ref"])
        if not co_pairs.empty and "co2_raw" in df_pair.columns:
            a_co, b_co, rmse_co = fit_linear_calibration(co_pairs["co2_raw"], co_pairs["co_ref"])
        else:
            a_co = b_co = rmse_co = None

        # Save calibration meta to Influx (calibration_params measurement)
        from influxdb_client.client.write.point import Point
        from influxdb_client.domain.write_precision import WritePrecision
        from .influx import write_api, ORG, BUCKET  # type: ignore

        p = Point("calibration_params").tag("device_id", device_id).field("slope_pm", float(a_pm)).field("intercept_pm", float(b_pm)).field("rmse_pm", float(rmse_pm)).field("n_samples", int(len(df_pair))).field("avg_distance_m", float(df_pair["distance_m"].mean()))
        if a_co is not None:
            p = p.field("slope_co", float(a_co)).field("intercept_co", float(b_co)).field("rmse_co", float(rmse_co))
        p = p.time(int(pd.Timestamp.now(tz="UTC").timestamp() * 1e9), WritePrecision.NS)
        write_api.write(bucket=BUCKET, org=ORG, record=p)

        return {
            "status": "ok",
            "message": "Kalibrasi berhasil",
            "params": {
                "pm": {"a": a_pm, "b": b_pm, "rmse": rmse_pm},
                "co": {"a": a_co, "b": b_co, "rmse": rmse_co} if a_co is not None else None
            },
            "meta": {
                "n_samples": int(len(df_pair)),
                "avg_distance_m": float(df_pair["distance_m"].mean()),
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/readings")
def get_readings(measurement: str = "raw_readings", start: str = "-1h"):
    try:
        df = query_tabular(measurement, start)
        if df.empty:
            return {"status": "ok", "data": []}
        # map fields for client
        out = []
        for _, r in df.iterrows():
            out.append({
                "device_id": r.get("device_id"),
                "pm_raw": r.get("pm_raw"),
                "co2_raw": r.get("co2_raw"),
                "temperature": r.get("temp"),
                "humidity": r.get("hum"),
                "time": r.get("time"),
                "lat": r.get("lat"),
                "lon": r.get("lon")
            })
        return {"status": "ok", "data": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/aqicn/sleman")
def get_aqicn_sleman():
    return fetch_aqicn_station(13653)
