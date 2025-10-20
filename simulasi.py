import os
import requests
from datetime import datetime, timezone
import time
import random

# Konfigurasi
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/ingest")
DEVICE_ID = os.getenv("DEVICE_ID", "sensor-001")
SEND_INTERVAL_SECONDS = int(os.getenv("SEND_INTERVAL", "5"))

def send_sensor_data(data: dict):
    try:
        response = requests.post(API_URL, json=data, timeout=5)
        response.raise_for_status()
        resp_json = response.json()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Data terkirim.")
        print(f"Payload: pm={data['pm_raw']:.2f}, co2={data['co2_raw']:.1f}, temp={data['temp']:.1f}, hum={data['hum']:.1f}")
        print(f"Server response: {resp_json}\n")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Gagal kirim data: {e}\n")

def main():
    print(f"▶ Memulai simulasi sensor '{DEVICE_ID}'")
    print(f"   Endpoint: {API_URL}")
    print(f"   Interval: {SEND_INTERVAL_SECONDS} detik\n")

    # Inisialisasi nilai awal
    pm_raw = random.uniform(5, 50)
    co2_raw = random.uniform(350, 600)
    temp = random.uniform(25, 30)
    hum = random.uniform(50, 80)

    try:
        while True:
            # Simulasi fluktuasi
            pm_raw = max(0, pm_raw + random.uniform(-1, 1))
            co2_raw = max(300, co2_raw + random.uniform(-5, 5))
            temp = max(20, temp + random.uniform(-0.5, 0.5))
            hum = max(0, min(100, hum + random.uniform(-1, 1)))

            # Payload sesuai schema
            payload = {
                "device_id": DEVICE_ID,
                "timestamp": datetime.now(timezone.utc).isoformat(),  # UTC ISO8601
                "lat": -7.7956,   # Sleman/Yogyakarta
                "lon": 110.3695,
                "pm_raw": round(pm_raw, 2),
                "co2_raw": round(co2_raw, 2),
                "temp": round(temp, 2),
                "hum": round(hum, 2)
            }

            send_sensor_data(payload)
            time.sleep(SEND_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n⏹ Simulasi dihentikan oleh user.")

if __name__ == "__main__":
    main()
