"""Pipeline ETL: Carga, validación Pydantic, cruce relacional y enriquecimiento físico.

Paso 1 del pipeline de AeroMap:
- Ingesta y validación estricta con Pydantic v2.
- Cruce relacional de estaciones meteorológicas y telemetría horaria.
- Transformaciones físicas obligatorias (km/h -> m/s, hPa -> Pa).
- Indexación espacial con teselas Web Mercator (EPSG:3857).
- Persistencia optimizada en formato Apache Parquet.
"""

from __future__ import annotations

import json
import logging
import time
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union

# Permitir ejecución directa como script (python src/etl/loader.py) además de como módulo (-m)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
from pydantic import TypeAdapter

from src.etl.geo_utils import wgs84_to_tile
from src.etl.schemas import EnrichedTelemetryRecord, StationSchema, TelemetrySchema


# Configuración del registrador de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AeroMap.ETL")

# Rutas por defecto en el repositorio
DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_ZOOM_LEVEL = 16


def resolve_stations_path(raw_dir: Union[Path, str] = DEFAULT_RAW_DIR) -> Path:
    """Resuelve la ruta al archivo de estaciones soportando diferentes nomenclaturas.

    Prioridad:
    1. aruba_stations.json
    2. stations.json
    """
    raw_path = Path(raw_dir)
    candidates = ["aruba_stations.json", "stations.json"]
    for name in candidates:
        candidate = raw_path / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"No se encontró archivo de estaciones en '{raw_path}'. Buscados: {candidates}"
    )


def resolve_telemetry_path(raw_dir: Union[Path, str] = DEFAULT_RAW_DIR) -> Path:
    """Resuelve la ruta al archivo de telemetría soportando diferentes nomenclaturas.

    Prioridad:
    1. train_aruba_lecturas.json
    2. telemetry.json
    """
    raw_path = Path(raw_dir)
    candidates = ["train_aruba_lecturas.json", "telemetry.json"]
    for name in candidates:
        candidate = raw_path / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"No se encontró archivo de telemetría en '{raw_path}'. Buscados: {candidates}"
    )


def load_stations(file_path: Union[Path, str]) -> List[StationSchema]:
    """Carga y valida el catastro de estaciones meteorológicas con Pydantic v2.

    Args:
        file_path: Ruta al archivo JSON de estaciones.

    Returns:
        List[StationSchema]: Lista de estaciones validadas.
    """
    path = Path(file_path)
    logger.info(f"Cargando catálogo de estaciones desde: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    adapter = TypeAdapter(List[StationSchema])
    validated_stations = adapter.validate_python(raw_data)
    logger.info(f"Validación exitosa: {len(validated_stations)} estaciones procesadas.")
    return validated_stations


def load_telemetry(
    file_path: Union[Path, str],
    sample_size: Optional[int] = None,
) -> List[TelemetrySchema]:
    """Carga y valida los registros de telemetría con Pydantic v2.

    Args:
        file_path: Ruta al archivo JSON de telemetría.
        sample_size: Número opcional de registros a validar (None para todos).

    Returns:
        List[TelemetrySchema]: Lista de registros de telemetría validados.
    """
    path = Path(file_path)
    logger.info(f"Cargando registros de telemetría desde: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if sample_size is not None and sample_size > 0:
        raw_data = raw_data[:sample_size]
        logger.info(f"Modo muestra activo: limitando a {len(raw_data)} registros.")

    adapter = TypeAdapter(List[TelemetrySchema])
    validated_telemetry = adapter.validate_python(raw_data)
    logger.info(
        f"Validación exitosa: {len(validated_telemetry)} registros de telemetría procesados."
    )
    return validated_telemetry


def create_merged_dataset(
    stations: List[StationSchema],
    telemetry: List[TelemetrySchema],
    zoom: int = DEFAULT_ZOOM_LEVEL,
) -> pd.DataFrame:
    """Realiza el cruce relacional, cálculos físicos y cálculo de teselas espaciales.

    Reglas de negocio:
    1. Cruce relacional: telemetry.station_id == stations.id
    2. Consistencia física:
       - wind_speed_ms = wind_speed_kmh / 3.6
       - pressure_pa = pressure_hpa * 100.0
    3. Indexación espacial:
       - tile_x, tile_y calculados mediante wgs84_to_tile con el zoom dado.

    Args:
        stations: Lista de estaciones validadas.
        telemetry: Lista de lecturas validadas.
        zoom: Nivel de zoom Web Mercator para indexar teselas satelitales.

    Returns:
        pd.DataFrame: DataFrame consolidado y enriquecido.
    """
    logger.info("Iniciando cruce relacional y enriquecimiento físico...")

    # Mapeo de metadatos de estaciones indexados por station_id (str)
    station_lookup = {}
    for st in stations:
        tx, ty = wgs84_to_tile(st.latitude, st.longitude, zoom=zoom)
        station_lookup[str(st.id)] = {
            "station_id": str(st.id),
            "station_name": st.name,
            "station_code": st.code,
            "latitude": st.latitude,
            "longitude": st.longitude,
            "elevation_m": st.elevation_m,
            "district": st.district,
            "is_active": st.is_active,
            "tile_x": tx,
            "tile_y": ty,
            "tile_zoom": zoom,
        }

    # Conversión a registros tabulares planos
    records = []
    unmatched_count = 0

    for tel in telemetry:
        sid_str = str(tel.station_id)
        st_meta = station_lookup.get(sid_str)
        if st_meta is None:
            unmatched_count += 1
            continue

        # Conversiones físicas estrictas (según reglas del README)
        wind_speed_ms = tel.wind_speed_kmh / 3.6
        pressure_pa = tel.pressure_hpa * 100.0

        records.append(
            {
                "telemetry_id": str(tel.id),
                "station_id": sid_str,
                "timestamp": tel.timestamp,
                "station_name": st_meta["station_name"],
                "station_code": st_meta["station_code"],
                "latitude": st_meta["latitude"],
                "longitude": st_meta["longitude"],
                "elevation_m": st_meta["elevation_m"],
                "district": st_meta["district"],
                "temperature_c": tel.temperature_c,
                "humidity_pct": tel.humidity_pct,
                "wind_speed_kmh": tel.wind_speed_kmh,
                "wind_direction_deg": tel.wind_direction_deg,
                "pressure_hpa": tel.pressure_hpa,
                "precipitation_mm": tel.precipitation_mm,
                "visibility_km": tel.visibility_km,
                "uv_index": tel.uv_index,
                "wind_speed_ms": wind_speed_ms,
                "pressure_pa": pressure_pa,
                "tile_x": st_meta["tile_x"],
                "tile_y": st_meta["tile_y"],
                "tile_zoom": st_meta["tile_zoom"],
            }
        )

    if unmatched_count > 0:
        logger.warning(
            f"Se descartaron {unmatched_count} registros huérfanos sin estación asociada."
        )

    df = pd.DataFrame(records)
    logger.info(f"DataFrame consolidado generado con {len(df)} filas y {len(df.columns)} columnas.")
    return df


def export_processed_data(
    df: pd.DataFrame,
    output_dir: Union[Path, str] = DEFAULT_PROCESSED_DIR,
    base_name: str = "telemetry_enriched",
) -> Tuple[Path, Optional[Path]]:
    """Exporta el dataset procesado a formato Apache Parquet y opcionalmente CSV.

    Args:
        df: DataFrame enriquecido a exportar.
        output_dir: Carpeta de destino.
        base_name: Nombre base del archivo sin extensión.

    Returns:
        Tuple[Path, Optional[Path]]: Ruta al archivo Parquet generado y ruta CSV (si aplica).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = out_dir / f"{base_name}.parquet"
    logger.info(f"Guardando dataset en formato Parquet: {parquet_path}")
    df.to_parquet(parquet_path, engine="pyarrow", index=False)

    size_mb = parquet_path.stat().st_size / (1024 * 1024)
    logger.info(f"Archivo Parquet generado exitosamente. Tamaño: {size_mb:.2f} MB")

    return parquet_path, None


def run_etl(
    raw_dir: Union[Path, str] = DEFAULT_RAW_DIR,
    processed_dir: Union[Path, str] = DEFAULT_PROCESSED_DIR,
    zoom: int = DEFAULT_ZOOM_LEVEL,
    sample_size: Optional[int] = None,
) -> pd.DataFrame:
    """Ejecuta el pipeline ETL de principio a fin.

    Args:
        raw_dir: Directorio con los JSON brutos.
        processed_dir: Directorio destino para los datos procesados.
        zoom: Nivel de zoom Web Mercator para teselas.
        sample_size: Opcional, limitar número de lecturas para pruebas rápidas.

    Returns:
        pd.DataFrame: DataFrame procesado.
    """
    start_time = time.time()
    logger.info("=== INICIANDO PIPELINE ETL (AeroMap Hito 2) ===")

    stations_file = resolve_stations_path(raw_dir)
    telemetry_file = resolve_telemetry_path(raw_dir)

    stations = load_stations(stations_file)
    telemetry = load_telemetry(telemetry_file, sample_size=sample_size)

    df_merged = create_merged_dataset(stations, telemetry, zoom=zoom)
    export_processed_data(df_merged, output_dir=processed_dir)

    elapsed = time.time() - start_time
    logger.info(
        f"=== PIPELINE ETL COMPLETADO EXITOSAMENTE EN {elapsed:.2f} SEGUNDOS ({len(df_merged)} filas) ==="
    )
    return df_merged


if __name__ == "__main__":
    run_etl()
