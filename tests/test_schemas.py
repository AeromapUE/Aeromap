"""Pruebas unitarias para los esquemas Pydantic v2 (schemas.py)."""

from datetime import datetime
import uuid
import pytest
from pydantic import ValidationError

from src.etl.schemas import EnrichedTelemetryRecord, StationSchema, TelemetrySchema


def test_station_schema_valid():
    """Valida la creación correcta de una estación con datos válidos."""
    data = {
        "id": "4ca4c103-894d-4f59-a911-f3abb8077e3c",
        "name": "Alto Vista",
        "code": "WS-ALT-11",
        "latitude": 12.5912,
        "longitude": -70.0374,
        "elevation_m": 25,
        "district": "Noord",
        "is_active": True,
    }
    st = StationSchema(**data)
    assert str(st.id) == data["id"]
    assert st.name == "Alto Vista"
    assert st.latitude == 12.5912
    assert st.is_active is True


def test_station_schema_invalid_latitude():
    """Rechaza latitudes fuera del rango geográfico [-90, 90]."""
    with pytest.raises(ValidationError):
        StationSchema(
            id=uuid.uuid4(),
            name="Test",
            code="WS-TST-01",
            latitude=95.0,
            longitude=-70.0,
            elevation_m=10,
            district="Noord",
        )


def test_station_schema_invalid_elevation():
    """Rechaza elevaciones menores a -500m."""
    with pytest.raises(ValidationError):
        StationSchema(
            id=uuid.uuid4(),
            name="Test",
            code="WS-TST-01",
            latitude=12.0,
            longitude=-70.0,
            elevation_m=-600,
            district="Noord",
        )


def test_telemetry_schema_valid():
    """Valida la creación correcta de un registro de telemetría."""
    data = {
        "id": "5b9f3e1c-e410-4bc7-a0f5-ef4752ddfee9",
        "station_id": "4ca4c103-894d-4f59-a911-f3abb8077e3c",
        "timestamp": "2026-03-31T22:00:00Z",
        "temperature_c": 30.4,
        "humidity_pct": 71.8,
        "wind_speed_kmh": 21.5,
        "wind_direction_deg": 45.6,
        "pressure_hpa": 1016.0,
        "precipitation_mm": 0.0,
        "visibility_km": 11.8,
        "uv_index": 0.0,
    }
    rec = TelemetrySchema(**data)
    assert rec.temperature_c == 30.4
    assert rec.wind_speed_kmh == 21.5
    assert rec.wind_direction_deg == 45.6


def test_telemetry_schema_wind_direction_normalization():
    """Normaliza 360 grados azimutales a 0.0."""
    rec = TelemetrySchema(
        id=uuid.uuid4(),
        station_id=uuid.uuid4(),
        timestamp=datetime.now(),
        temperature_c=25.0,
        humidity_pct=50.0,
        wind_speed_kmh=10.0,
        wind_direction_deg=360.0,
        pressure_hpa=1013.25,
    )
    assert rec.wind_direction_deg == 0.0


def test_telemetry_schema_invalid_humidity():
    """Rechaza humedades relativas > 100% o < 0%."""
    with pytest.raises(ValidationError):
        TelemetrySchema(
            id=uuid.uuid4(),
            station_id=uuid.uuid4(),
            timestamp=datetime.now(),
            temperature_c=25.0,
            humidity_pct=105.0,
            wind_speed_kmh=10.0,
            wind_direction_deg=45.0,
            pressure_hpa=1013.0,
        )


def test_telemetry_schema_negative_wind_speed():
    """Rechaza velocidades de viento negativas."""
    with pytest.raises(ValidationError):
        TelemetrySchema(
            id=uuid.uuid4(),
            station_id=uuid.uuid4(),
            timestamp=datetime.now(),
            temperature_c=25.0,
            humidity_pct=50.0,
            wind_speed_kmh=-5.0,
            wind_direction_deg=45.0,
            pressure_hpa=1013.0,
        )


def test_enriched_record_schema():
    """Valida la creación de un registro enriquecido consolidado."""
    data = {
        "telemetry_id": uuid.uuid4(),
        "station_id": uuid.uuid4(),
        "timestamp": datetime.now(),
        "station_name": "Alto Vista",
        "station_code": "WS-ALT-11",
        "latitude": 12.5912,
        "longitude": -70.0374,
        "elevation_m": 25.0,
        "district": "Noord",
        "temperature_c": 30.0,
        "humidity_pct": 70.0,
        "wind_speed_kmh": 36.0,
        "wind_direction_deg": 90.0,
        "pressure_hpa": 1010.0,
        "precipitation_mm": 0.0,
        "visibility_km": 10.0,
        "uv_index": 2.0,
        "wind_speed_ms": 10.0,
        "pressure_pa": 101000.0,
        "tile_x": 20018,
        "tile_y": 30457,
        "tile_zoom": 16,
    }
    rec = EnrichedTelemetryRecord(**data)
    assert rec.wind_speed_ms == 10.0
    assert rec.pressure_pa == 101000.0
    assert rec.tile_x == 20018
