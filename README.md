# 🌬️ Air Quality API

A robust backend service for monitoring air quality. This API collects data from sensors, stores it in a time-series database, and provides endpoints for data retrieval and analysis. It integrates with external services like AQICN for data enrichment and calibration.

---

## ✨ Core Features

-   **Data Ingestion**: Accepts data from various air quality sensors.
-   **Time-Series Storage**: Leverages InfluxDB for efficient, high-performance storage of sensor readings.
-   **RESTful Endpoints**: A clean API for querying historical and real-time air quality data.
-   **External Data Integration**: Connects to the [World Air Quality Index (AQICN)](https://aqicn.org/api/) to fetch referential data.
-   **Sensor Calibration**: Implements logic to calibrate and improve the accuracy of sensor readings.

---

## 🛠️ Tech Stack

-   **Language**: Python 3.11+
-   **Framework**: FastAPI
-   **Database**: InfluxDB
-   **Data Validation**: Pydantic
-   **ASGI Server**: Uvicorn

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.11 or newer
-   Access to an InfluxDB instance (v2.0+)
-   An API Token from [AQICN API](https://aqicn.org/api/)

### Installation & Setup

1.  **Clone the repository:**
    ```sh
    git clone https://your-repository-url/air-quality-api.git
    cd air-quality-api/backend
    ```

2.  **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```
    *(Note: You may need to create a `requirements.txt` file first)*
    ```sh
    pip freeze > requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the `backend` directory and populate it with your credentials. Use `.env.example` as a template.

    **.env.example**
    ```ini
    # InfluxDB Configuration
    INFLUXDB_URL=http://localhost:8086
    INFLUXDB_TOKEN=your-influxdb-api-token
    INFLUXDB_ORG=your-influxdb-organization
    INFLUXDB_BUCKET=air_quality

    # AQICN API Configuration
    AQICN_API_TOKEN=your-aqicn-api-token
    ```

### Running the Application

Launch the API using Uvicorn:

```sh
uvicorn backend.main:app --reload