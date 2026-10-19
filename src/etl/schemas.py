"""Modelos de datos y esquemas de validación Pydantic v2 para AeroMap.

Define los contratos para estaciones meteorológicas, telemetría sin procesar
y registros enriquecidos tras la ejecución del pipeline ETL.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StationSchema(BaseModel):
    """Esquema de validación para el catastro de estaciones meteorológicas."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: UUID
    name: str = Field(..., min_length=1, description="Nombre de la estación")
    code: str = Field(..., min_length=1, description="Código identificador único (ej. WS-ALT-11)")
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitud en grados decimales WGS84",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitud en grados decimales WGS84",
    )
    elevation_m: float = Field(
        ...,
        ge=-500.0,
        le=9000.0,
        description="Elevación sobre el nivel del mar en metros",
    )
    district: str = Field(..., min_length=1, description="Distrito o región administrativa")
    is_active: bool = Field(default=True, description="Estado operativo de la estación")


class TelemetrySchema(BaseModel):
    """Esquema de validación para registros individuales de telemetría meteorológica."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: UUID
    station_id: UUID
    timestamp: datetime = Field(..., description="Marca temporal en formato ISO 8601")
    temperature_c: float = Field(
        ...,
        ge=-50.0,
        le=70.0,
        description="Temperatura ambiente en grados Celsius",
    )
    humidity_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Humedad relativa porcentual [0, 100]",
    )
    wind_speed_kmh: float = Field(
        ...,
        ge=0.0,
        le=400.0,
        description="Velocidad del viento medida a 10m en km/h",
    )
    wind_direction_deg: float = Field(
        ...,
        ge=0.0,
        le=360.0,
        description="Dirección de procedencia del viento en grados azimutales [0, 360]",
    )
    pressure_hpa: float = Field(
        ...,
        ge=700.0,
        le=1150.0,
        description="Presión atmosférica a nivel de estación en hPa",
    )
    precipitation_mm: float = Field(
        default=0.0,
        ge=0.0,
        le=1000.0,
        description="Precipitación acumulada en milímetros",
    )
    visibility_km: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Visibilidad horizontal en kilómetros",
    )
    uv_index: float = Field(
        default=0.0,
        ge=0.0,
        le=30.0,
        description="Índice de radiación ultravioleta",
    )

    @field_validator("wind_direction_deg", mode="before")
    @classmethod
    def normalize_direction(cls, v: float | int) -> float:
        """Normaliza la dirección del viento al rango [0, 360)."""
        val = float(v)
        if val == 360.0:
            return 0.0
        return val


class EnrichedTelemetryRecord(BaseModel):
    """Esquema para un registro consolidado y enriquecido físicamente."""

    model_config = ConfigDict(extra="ignore")

    # Identificadores y marcas temporales
    telemetry_id: UUID
    station_id: UUID
    timestamp: datetime

    # Metadatos de la estación
    station_name: str
    station_code: str
    latitude: float
    longitude: float
    elevation_m: float
    district: str

    # Variables meteorológicas originales
    temperature_c: float
    humidity_pct: float
    wind_speed_kmh: float
    wind_direction_deg: float
    pressure_hpa: float
    precipitation_mm: float
    visibility_km: float
    uv_index: float

    # Variables convertidas a unidades SI (según reglas del README)
    wind_speed_ms: float = Field(
        ...,
        ge=0.0,
        description="Velocidad del viento en metros por segundo (v = kmh / 3.6)",
    )
    pressure_pa: float = Field(
        ...,
        ge=70000.0,
        le=115000.0,
        description="Presión atmosférica en Pascales (p = hPa * 100)",
    )

    # Coordenadas Slippy Map de la estación
    tile_x: int = Field(..., ge=0, description="Índice X de la tesela Web Mercator")
    tile_y: int = Field(..., ge=0, description="Índice Y de la tesela Web Mercator")
    tile_zoom: int = Field(..., ge=0, description="Nivel de zoom utilizado")
