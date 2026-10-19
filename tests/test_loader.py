"""Pruebas unitarias y de integración para el cargador y pipeline ETL (loader.py)."""

import json
from pathlib import Path
import uuid
import pandas as pd
import pytest

from src.etl.loader import (
    create_merged_dataset,
    export_processed_data,
    load_stations,
    load_telemetry,
    resolve_stations_path,
    resolve_telemetry_path,
    run_etl,
)
from src.etl.schemas import StationSchema, TelemetrySchema


@pytest.fixture
def sample_station_id():
    return str(uuid.uuid4())


@pytest.fixture
def mock_stations_file(tmp_path, sample_station_id):
    file = tmp_path / "stations.json"
    data = [
        {
            "id": sample_station_id,
            "name": "Test Station",
            "code": "WS-TST-01",
            "latitude": 12.5912,
            "longitude": -70.0374,
            "elevation_m": 25.0,
            "district": "Noord",
            "is_active": True,
        }
    ]
    file.write_text(json.dumps(data), encoding="utf-8")
    return file


@pytest.fixture
def mock_telemetry_file(tmp_path, sample_station_id):
    file = tmp_path / "telemetry.json"
    data = [
        {
            "id": str(uuid.uuid4()),
            "station_id": sample_station_id,
            "timestamp": "2026-03-31T22:00:00Z",
            "temperature_c": 30.0,
            "humidity_pct": 70.0,
            "wind_speed_kmh": 36.0,
            "wind_direction_deg": 45.0,
            "pressure_hpa": 1010.0,
            "precipitation_mm": 0.0,
            "visibility_km": 10.0,
            "uv_index": 0.0,
        },
        {
            "id": str(uuid.uuid4()),
            "station_id": str(uuid.uuid4()),  # Estación huérfana (debe ser descartada)
            "timestamp": "2026-03-31T23:00:00Z",
            "temperature_c": 28.0,
            "humidity_pct": 75.0,
            "wind_speed_kmh": 18.0,
            "wind_direction_deg": 90.0,
            "pressure_hpa": 1012.0,
            "precipitation_mm": 0.0,
            "visibility_km": 10.0,
            "uv_index": 0.0,
        },
    ]
    file.write_text(json.dumps(data), encoding="utf-8")
    return file


def test_resolve_paths_missing(tmp_path):
    """Lanza FileNotFoundError cuando no existen los archivos esperados."""
    with pytest.raises(FileNotFoundError):
        resolve_stations_path(tmp_path)
    with pytest.raises(FileNotFoundError):
        resolve_telemetry_path(tmp_path)


def test_resolve_paths_found(tmp_path):
    """Resuelve correctamente los nombres estándar o alternativos."""
    st_file = tmp_path / "aruba_stations.json"
    st_file.write_text("[]", encoding="utf-8")
    assert resolve_stations_path(tmp_path) == st_file

    tel_file = tmp_path / "train_aruba_lecturas.json"
    tel_file.write_text("[]", encoding="utf-8")
    assert resolve_telemetry_path(tmp_path) == tel_file


def test_load_stations(mock_stations_file):
    """Carga y valida estaciones desde JSON."""
    stations = load_stations(mock_stations_file)
    assert len(stations) == 1
    assert isinstance(stations[0], StationSchema)
    assert stations[0].name == "Test Station"


def test_load_telemetry(mock_telemetry_file):
    """Carga y valida telemetría, incluyendo el parámetro sample_size."""
    all_telemetry = load_telemetry(mock_telemetry_file)
    assert len(all_telemetry) == 2
    assert isinstance(all_telemetry[0], TelemetrySchema)

    sample = load_telemetry(mock_telemetry_file, sample_size=1)
    assert len(sample) == 1


def test_create_merged_dataset(mock_stations_file, mock_telemetry_file):
    """Comprueba el merge relacional, las conversiones físicas y la asignación de teselas."""
    stations = load_stations(mock_stations_file)
    telemetry = load_telemetry(mock_telemetry_file)

    df = create_merged_dataset(stations, telemetry, zoom=16)

    # El registro huérfano debió descartarse -> queda 1
    assert len(df) == 1

    row = df.iloc[0]
    # Consistencia física: 36.0 km/h = 10.0 m/s
    assert pytest.approx(row["wind_speed_ms"], 0.001) == 10.0
    # Consistencia física: 1010 hPa = 101000 Pa
    assert pytest.approx(row["pressure_pa"], 0.001) == 101000.0

    # Tesela espacial asignada
    assert row["tile_x"] == 20018
    assert row["tile_y"] == 30457
    assert row["tile_zoom"] == 16


def test_export_processed_data(tmp_path):
    """Verifica la exportación en Parquet."""
    df = pd.DataFrame(
        [
            {
                "telemetry_id": "test",
                "wind_speed_ms": 5.5,
                "pressure_pa": 101300.0,
            }
        ]
    )
    out_dir = tmp_path / "processed"
    parquet_path, _ = export_processed_data(df, output_dir=out_dir)

    assert parquet_path.exists()
    assert parquet_path.suffix == ".parquet"

    # Verificamos que se pueda leer de vuelta
    loaded_df = pd.read_parquet(parquet_path)
    assert len(loaded_df) == 1
    assert loaded_df["wind_speed_ms"].iloc[0] == 5.5


def test_run_etl_end_to_end(tmp_path, sample_station_id):
    """Prueba de integración end-to-end con datasets temporales."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir(parents=True)

    st_data = [
        {
            "id": sample_station_id,
            "name": "Integration Station",
            "code": "WS-INT-99",
            "latitude": 12.5,
            "longitude": -70.0,
            "elevation_m": 15.0,
            "district": "Oranjestad",
            "is_active": True,
        }
    ]
    tel_data = [
        {
            "id": str(uuid.uuid4()),
            "station_id": sample_station_id,
            "timestamp": "2026-03-31T12:00:00Z",
            "temperature_c": 31.0,
            "humidity_pct": 65.0,
            "wind_speed_kmh": 25.2,
            "wind_direction_deg": 45.0,
            "pressure_hpa": 1015.0,
            "precipitation_mm": 0.0,
            "visibility_km": 12.0,
            "uv_index": 5.0,
        }
    ]

    (raw_dir / "stations.json").write_text(json.dumps(st_data), encoding="utf-8")
    (raw_dir / "telemetry.json").write_text(json.dumps(tel_data), encoding="utf-8")

    df = run_etl(raw_dir=raw_dir, processed_dir=processed_dir, zoom=16)

    assert len(df) == 1
    assert (processed_dir / "telemetry_enriched.parquet").exists()
