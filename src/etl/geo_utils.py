"""Utilidades geoespaciales y conversor WGS84 a Slippy Map Tiles (EPSG:3857).

Implementa las fórmulas analíticas de proyección Web Mercator para downscaling
e indexación espacial de mosaicos satelitales según la especificación del proyecto.
"""

from __future__ import annotations

import math
from typing import Tuple, List

# Límite geográfico para la proyección Web Mercator (evita singularidades en los polos)
MAX_MERCATOR_LAT = 85.0511287798066


def wgs84_to_tile(lat: float, lon: float, zoom: int) -> Tuple[int, int]:
    """Convierte coordenadas geográficas WGS84 a índices de tesela Slippy Map (x, y).

    Fórmulas analíticas (README):
        x = floor( ((lon + 180) / 360) · 2^z )
        y = floor( (1 - ln(tan(lat_rad) + 1/cos(lat_rad)) / π) · 2^(z-1) )
    donde lat_rad = lat · (π / 180).

    Args:
        lat: Latitud en grados decimales (-85.05112878 a 85.05112878).
        lon: Longitud en grados decimales (-180.0 a 180.0).
        zoom: Nivel de zoom de la tesela (>= 0).

    Returns:
        Tuple[int, int]: Índices enteros de la tesela (tile_x, tile_y).

    Raises:
        ValueError: Si la latitud, longitud o zoom están fuera de rangos válidos.
    """
    if zoom < 0:
        raise ValueError(f"El nivel de zoom no puede ser negativo: {zoom}")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitud fuera de rango [-180, 180]: {lon}")
    if not (-MAX_MERCATOR_LAT <= lat <= MAX_MERCATOR_LAT):
        raise ValueError(
            f"Latitud fuera del rango Web Mercator [{-MAX_MERCATOR_LAT:.4f}, {MAX_MERCATOR_LAT:.4f}]: {lat}"
        )

    lat_rad = math.radians(lat)
    n = 2**zoom

    x = math.floor(((lon + 180.0) / 360.0) * n)
    # math.log(math.tan(rad) + 1 / math.cos(rad))
    sec_lat = 1.0 / math.cos(lat_rad)
    tan_lat = math.tan(lat_rad)
    y = math.floor((1.0 - math.log(tan_lat + sec_lat) / math.pi) * (2 ** (zoom - 1)))

    # Asegurar límites dentro de la cuadrícula [0, 2^zoom - 1]
    max_idx = n - 1
    x = max(0, min(x, max_idx))
    y = max(0, min(y, max_idx))

    return x, y


def tile_to_wgs84_bounds(x: int, y: int, zoom: int) -> Tuple[float, float, float, float]:
    """Calcula los límites geográficos WGS84 de una tesela (EPSG:3857).

    Args:
        x: Índice horizontal de la tesela.
        y: Índice vertical de la tesela.
        zoom: Nivel de zoom de la tesela.

    Returns:
        Tuple[float, float, float, float]: (west_lon, south_lat, east_lon, north_lat) en grados.
    """
    if zoom < 0:
        raise ValueError(f"El nivel de zoom no puede ser negativo: {zoom}")
    n = 2**zoom

    west_lon = (x / n) * 360.0 - 180.0
    east_lon = ((x + 1) / n) * 360.0 - 180.0

    north_lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    south_lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y + 1) / n)))

    north_lat = math.degrees(north_lat_rad)
    south_lat = math.degrees(south_lat_rad)

    return west_lon, south_lat, east_lon, north_lat


def get_tile_neighbors_3x3(
    center_x: int, center_y: int, zoom: int | None = None
) -> List[Tuple[int, int]]:
    """Calcula la matriz 3x3 de teselas contiguas centrada en (center_x, center_y).

    El orden devuelto es por filas (top-left a bottom-right):
        (-1, -1), (0, -1), (1, -1)
        (-1,  0), (0,  0), (1,  0)
        (-1,  1), (0,  1), (1,  1)

    Args:
        center_x: Índice x de la tesela central.
        center_y: Índice y de la tesela central.
        zoom: Opcional, nivel de zoom para validar bordes de cuadrícula [0, 2^zoom - 1].

    Returns:
        List[Tuple[int, int]]: Lista de 9 tuplas con los índices (x, y) de las teselas.
    """
    neighbors: List[Tuple[int, int]] = []
    max_idx = (2**zoom - 1) if zoom is not None else None

    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx = center_x + dx
            ny = center_y + dy
            if max_idx is not None:
                nx = max(0, min(nx, max_idx))
                ny = max(0, min(ny, max_idx))
            neighbors.append((nx, ny))

    return neighbors
