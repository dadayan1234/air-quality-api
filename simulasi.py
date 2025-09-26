import requests
from datetime import datetime
import time
import random

API_URL = "http://127.0.0.1:8000/api/v1/ingest"
DEVICE_ID = "sensor-001"
SEND_INTERVAL_SECONDS = 5

def send_sensor_data(data):
    try:
        response = requests.post(API_URL, json=data)
        response.raise_for_status()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Data berhasil dikirim. Status: {response.status_code}")
        print(f"Respon server: {response.json()}\n")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] GAGAL mengirim data: {e}\n")

def main():
    print(f"Memulai simulasi sensor '{DEVICE_ID}'.")
    print(f"Data akan dikirim ke {API_URL} setiap {SEND_INTERVAL_SECONDS} detik.\n")

    pm_raw = random.uniform(5, 50)
    co2_raw = random.uniform(350, 600)
    temp = random.uniform(25, 30)
    hum = random.uniform(50, 80)

    try:
        while True:
            pm_raw = max(0, pm_raw + random.uniform(-1, 1))
            co2_raw = max(300, co2_raw + random.uniform(-5, 5))
            temp = max(20, temp + random.uniform(-0.5, 0.5))
            hum = max(0, min(100, hum + random.uniform(-1, 1)))

            payload = {
                "device_id": DEVICE_ID,
                "timestamp": datetime.utcnow().isoformat() + "Z",  # UTC
                "lat": -7.7956,
                "lon": 110.3695,
                "pm_raw": pm_raw,
                "co2_raw": co2_raw,
                "temp": temp,
                "hum": hum
            }

            send_sensor_data(payload)
            time.sleep(SEND_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nSimulasi dihentikan.")

if __name__ == "__main__":
    main()
