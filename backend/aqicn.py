# import requests
# from fastapi import HTTPException
# from datetime import datetime, timedelta

# TOKEN = "f55d003153c26913f857345cf056344ba8d33341"

# def fetch_aqicn(lat: float, lon: float):
#     url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={TOKEN}"
#     try:
#         r = requests.get(url, timeout=10)
#         r.raise_for_status()
#         data = r.json()
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=503, detail=f"AQICN request failed: {str(e)}")

#     if data.get("status") != "ok":
#         err_msg = data.get("data", "Unknown error from AQICN")
#         raise HTTPException(status_code=400, detail=f"AQICN error: {err_msg}")

#     d = data["data"]
#     aqi = d.get("aqi")

#     # ambil komponen polutan
#     iaqi = d.get("iaqi", {})
#     pm25 = iaqi.get("pm25", {}).get("v")
#     co = iaqi.get("co", {}).get("v")
#     no2 = iaqi.get("no2", {}).get("v")
#     o3 = iaqi.get("o3", {}).get("v")
#     so2 = iaqi.get("so2", {}).get("v")

#     # ambil detail lokasi
#     city = d.get("city", {})
#     city_name = city.get("name")
#     geo_coords = city.get("geo")  # [lat, lon]

#     # waktu UTC (string dari API)
#     time_info = d.get("time", {})
#     time_str = time_info.get("s")
#     tz_offset_min = time_info.get("tz")  # misalnya "+07:00"
#     # konversi manual ke UTC+7 jika mau fix
#     dt_utc = None
#     dt_jakarta = None
#     if time_str:
#         # parse waktu original
#         try:
#             dt_utc = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
#             # force ke UTC, lalu tambahkan offset +7 jam
#             dt_jakarta = dt_utc + timedelta(hours=7)
#         except ValueError:
#             dt_utc = time_str

#     return {
#         "status": "ok",
#         "aqi": aqi,
#         "pm25": pm25,
#         "co": co,
#         "no2": no2,
#         "o3": o3,
#         "so2": so2,
#         "location": {
#             "name": city_name,
#             "coordinates": geo_coords
#         },
#         "time": {
#             "original": time_str,
#             "utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S") if isinstance(dt_utc, datetime) else dt_utc,
#             "jakarta": dt_jakarta.strftime("%Y-%m-%d %H:%M:%S") if isinstance(dt_jakarta, datetime) else dt_utc
#         }
#     }


# def fetch_aqicn_station(station_id: int):
#     url = f"https://api.waqi.info/feed/@{station_id}/?token={TOKEN}"
#     try:
#         r = requests.get(url, timeout=10)
#         r.raise_for_status()
#         data = r.json()
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=503, detail=f"AQICN request failed: {str(e)}")

#     if data.get("status") == "ok":
#         d = data["data"]
#         aqi = d.get("aqi")
#         iaqi = d.get("iaqi", {})

#         # Data pollutants
#         pm25 = iaqi.get("pm25", {}).get("v")
#         co = iaqi.get("co", {}).get("v")
#         no2 = iaqi.get("no2", {}).get("v")
#         o3 = iaqi.get("o3", {}).get("v")
#         so2 = iaqi.get("so2", {}).get("v")

#         # City info
#         city = d.get("city", {})
#         city_name = city.get("name")
#         geo_coords = city.get("geo")
#         city_url = city.get("url")

#         # Time conversion
#         original_time = d.get("time", {}).get("s")
#         utc_time = datetime.strptime(original_time, "%Y-%m-%d %H:%M:%S")
#         jakarta_time = utc_time + timedelta(hours=7)

#         return {
#             "status": "ok",
#             "aqi": aqi,
#             "pm25": pm25,
#             "co": co,
#             "no2": no2,
#             "o3": o3,
#             "so2": so2,
#             "location": {
#                 "name": city_name,
#                 "coordinates": geo_coords,
#                 "aqicn_station_url": city_url
#             },
#             "time": {
#                 "original": original_time,
#                 "utc": utc_time.strftime("%Y-%m-%d %H:%M:%S"),
#                 "jakarta": jakarta_time.strftime("%Y-%m-%d %H:%M:%S")
#             }
#         }
#     else:
#         err_msg = data.get("data", "Unknown error from AQICN")
#         raise HTTPException(status_code=400, detail=f"AQICN error: {err_msg}")

# app/aqicn.py
import os
import requests
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("AQICN_TOKEN", "f55d003153c26913f857345cf056344ba8d33341")
AQICN_BASE = "https://api.waqi.info"

def _parse_time_to_utc(time_str: str):
    # API typically returns "YYYY-MM-DD HH:MM:SS" in UTC — treat as UTC naive then set tz=UTC
    if not time_str:
        return None
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def fetch_aqicn(lat: float, lon: float):
    url = f"{AQICN_BASE}/feed/geo:{lat};{lon}/?token={TOKEN}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        js = r.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"AQICN request failed: {str(e)}")

    if js.get("status") != "ok":
        err = js.get("data", "unknown")
        raise HTTPException(status_code=400, detail=f"AQICN response not ok: {err}")

    d = js["data"]
    iaqi = d.get("iaqi", {})
    time_str = d.get("time", {}).get("s")
    ts_utc = _parse_time_to_utc(time_str)

    result = {
        "status": "ok",
        "aqi": d.get("aqi"),
        "pm25": iaqi.get("pm25", {}).get("v"),
        "co": iaqi.get("co", {}).get("v"),
        "no2": iaqi.get("no2", {}).get("v"),
        "o3": iaqi.get("o3", {}).get("v"),
        "so2": iaqi.get("so2", {}).get("v"),
        "location": {
            "name": d.get("city", {}).get("name"),
            "coordinates": d.get("city", {}).get("geo"),
            "station_url": d.get("city", {}).get("url")
        },
        "time": {
            "original": time_str,
            "utc": ts_utc.isoformat() if ts_utc else None,
            # Jakarta/UTC+7 string
            "jakarta": (ts_utc + timedelta(hours=7)).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S") if ts_utc else None
        }
    }
    return result

def fetch_aqicn_station(station_id: int):
    url = f"{AQICN_BASE}/feed/@{station_id}/?token={TOKEN}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        js = r.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"AQICN request failed: {str(e)}")
    if js.get("status") != "ok":
        raise HTTPException(status_code=400, detail=f"AQICN error: {js.get('data','unknown')}")
    d = js["data"]
    iaqi = d.get("iaqi", {})
    time_str = d.get("time", {}).get("s")
    ts_utc = _parse_time_to_utc(time_str)
    return {
        "status": "ok",
        "aqi": d.get("aqi"),
        "pm25": iaqi.get("pm25", {}).get("v"),
        "co": iaqi.get("co", {}).get("v"),
        "location": {
            "name": d.get("city", {}).get("name"),
            "coordinates": d.get("city", {}).get("geo"),
            "station_url": d.get("city", {}).get("url")
        },
        "time": {
            "original": time_str,
            "utc": ts_utc.isoformat() if ts_utc else None,
            "jakarta": (ts_utc + timedelta(hours=7)).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S") if ts_utc else None
        }
    }
