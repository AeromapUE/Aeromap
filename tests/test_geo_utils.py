"""Pruebas unitarias para utilidades geoespaciales y conversor Slippy Map (geo_utils.py)."""

import math
import mercantile
import pytest

from src.etl.geo_utils import (
    MAX_MERCATOR_LAT,
    get_tile_neighbors_3x3,
    tile_to_wgs84_bounds,
    wgs84_to_tile,
)


def test_wgs84_to_tile_alto_vista():
    """Valida la conversión para la estación Alto Vista en Aruba."""
    lat, lon, zoom = 12.5912, -70.0374, 16
    x, y = wgs84_to_tile(lat, lon, zoom)
    merc = mercantile.tile(lon, lat, zoom)
    assert (x, y) == (merc.x, merc.y)
    assert x == 20018
    assert y == 30457


@pytest.mark.parametrize("zoom", [1, 5, 10, 14, 16, 18])
@pytest.mark.parametrize(
    "lat,lon",
    [
        (0.0, 0.0),
        (12.5042, -70.0031),  # Aeropuerto Reina Beatrix, Aruba
        (12.5204, -69.9992),  # Hooiberg, Aruba
        (40.4168, -3.7038),  # Madrid
        (-33.8688, 151.2093),  # Sydney
    ],
)
def test_wgs84_to_tile_cross_validation_with_mercantile(lat, lon, zoom):
    """Comprueba la equivalencia exacta de la fórmula analítica frente a mercantile."""
    x, y = wgs84_to_tile(lat, lon, zoom)
    merc = mercantile.tile(lon, lat, zoom)
    assert (x, y) == (merc.x, merc.y)


def test_wgs84_to_tile_invalid_inputs():
    """Verifica el rechazo de valores fuera de los rangos físicos y de proyección."""
    with pytest.raises(ValueError, match="zoom no puede ser negativo"):
        wgs84_to_tile(12.0, -70.0, -1)

    with pytest.raises(ValueError, match="Longitud fuera de rango"):
        wgs84_to_tile(12.0, -185.0, 16)

    with pytest.raises(ValueError, match="Longitud fuera de rango"):
        wgs84_to_tile(12.0, 185.0, 16)

    with pytest.raises(ValueError, match="Latitud fuera del rango Web Mercator"):
        wgs84_to_tile(88.0, 0.0, 16)

    with pytest.raises(ValueError, match="Latitud fuera del rango Web Mercator"):
        wgs84_to_tile(-89.0, 0.0, 16)


def test_tile_to_wgs84_bounds():
    """Comprueba que la estación queda contenida dentro del bounding box de su tesela."""
    lat, lon, zoom = 12.5912, -70.0374, 16
    x, y = wgs84_to_tile(lat, lon, zoom)

    west, south, east, north = tile_to_wgs84_bounds(x, y, zoom)
    assert west <= lon <= east
    assert south <= lat <= north

    # Error con zoom negativo
    with pytest.raises(ValueError, match="zoom no puede ser negativo"):
        tile_to_wgs84_bounds(x, y, -1)


def test_get_tile_neighbors_3x3_structure():
    """Comprueba el tamaño y orden de la matriz 3x3 de teselas contiguas."""
    center_x, center_y = 20018, 30457
    neighbors = get_tile_neighbors_3x3(center_x, center_y)

    assert len(neighbors) == 9
    # El elemento central (fila 1, col 1 -> índice 4) debe ser el centro
    assert neighbors[4] == (center_x, center_y)

    # Top-left
    assert neighbors[0] == (center_x - 1, center_y - 1)
    # Bottom-right
    assert neighbors[8] == (center_x + 1, center_y + 1)


def test_get_tile_neighbors_3x3_boundary_clamping():
    """Verifica que no se desborden los índices en los bordes de la cuadrícula global."""
    neighbors = get_tile_neighbors_3x3(0, 0, zoom=5)
    assert len(neighbors) == 9
    for x, y in neighbors:
        assert x >= 0
        assert y >= 0
