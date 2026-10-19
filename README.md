<div align="center">

# 🌬️ AeroMap

### *Downscaling de Viento y Potencial Eólico mediante Visión Artificial y Web Scraping Cartográfico*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Proyecto Fin de Grado en Informática | Universidad Europea de Madrid (Curso 2026/27)</b>
</p>

</div>

---

## 📑 Índice
- [📖 Sobre el Proyecto](#-sobre-el-proyecto)
- [✨ Características Principales](#-características-principales)
- [🏗️ Arquitectura y Pipeline](#️-arquitectura-y-pipeline)
- [📊 Datos de Entrada (Schemas)](#-datos-de-entrada-schemas)
- [🧠 Fundamentos Físicos y Matemáticos](#-fundamentos-físicos-y-matemáticos)
- [🛠️ Stack Tecnológico](#️-stack-tecnológico)
- [🚀 Instalación y Puesta en Marcha](#-instalación-y-puesta-en-marcha)
- [📁 Estructura del Repositorio](#-estructura-del-repositorio)
- [🎯 Roadmap e Hitos de Entrega](#-roadmap-e-hitos-de-entrega)
- [👥 Reglas de Contribución para Desarrolladores y Agentes](#-reglas-de-contribución-para-desarrolladores-y-agentes)
- [📄 Licencia](#-licencia)

---

## 📖 Sobre el Proyecto

Las estaciones meteorológicas convencionales miden la velocidad del viento a ras de suelo (**z = 10 m**), mientras que las turbinas eólicas comerciales operan con alturas de buje de **80 m a 120 m**. La fricción con el terreno frena las capas bajas de aire creando una **capa límite atmosférica**, cuya magnitud depende de la **longitud de rugosidad aerodinámica (z₀)**.

En regiones insulares como **Aruba**, donde predominan vientos alisios constantes pero conviven zonas costeras, llanuras desérticas, zonas urbanas y colinas rocosas, medir el viento solo a 10 m no permite proyectar la energía real. Como la **Densidad de Potencia Eólica (WPD)** es proporcional al cubo de la velocidad (**P ∝ v³**), un error mínimo en la rugosidad desvirtúa por completo la viabilidad del parque eólico.

**AeroMap** automatiza la estimación del potencial eólico real:
1. **Scrapea** mosaicos satelitales en alta resolución alrededor de las coordenadas de cada estación.
2. **Segmenta** la cobertura del suelo mediante *Deep Learning* (U-Net).
3. **Aísla el sector de barlovento** (origen del viento) para computar la rugosidad efectiva (**z₀,eff**).
4. **Calcula la densidad local del aire** y extrapola la velocidad a cotas de **80 m y 100 m** mediante la ley de Prandtl.

---

## ✨ Características Principales

* 🛰️ **Web Scraping Cartográfico Autónomo:** Conversor WGS84 a estándar *Slippy Map Tiles (XYZ)* con descarga y cosido de ortofotos satelitales en cuadrículas 3 × 3.
* 🔍 **Visión por Computador (U-Net):** Segmentación semántica multiclase orientada a la escala de rugosidad de **Davenport-Wieringa** (Agua, Terreno Abierto, Arbolado y Urbano).
* 🧭 **Ponderación Direccional (Barlovento):** Filtrado geométrico según `wind_direction_deg` (±30°) para analizar únicamente el terreno que ejerce frenado sobre el flujo entrante.
* ⚡ **Modelado Físico Termodinámico:** Corrección de la densidad del aire (ρ) con la ley del gas ideal y cálculo analítico de WPD (W/m²).
* 🗺️ **Dashboard Geoespacial:** Interfaz interactiva para visualizar las estaciones, las máscaras de suelo y el mapa de calor de potencia eólica.

---

## 🏗️ Arquitectura y Pipeline

```text
┌─────────────────┐       ┌──────────────────┐
│  stations.json  │       │  telemetry.json  │
└────────┬────────┘       └────────┬─────────┘
         │                         │
         └────────────┬────────────┘
                      ▼
            [ 1. Pipeline ETL ]
          Merge relacional por ID
                      ▼
         [ 2. Tile Scraping Engine ]
     WGS84 ──► XYZ Tiles ──► Mosaico 768x768
                      ▼
        [ 3. U-Net Segmentation ]
         Máscara 2D de clases (0-3)
                      ▼
       [ 4. Fetch & Roughness Engine ]
       Recorte barlovento (Ángulo ±30°)
           Cálculo de z0 efectiva
                      ▼
         [ 5. Atmospheric Physics ]
       Ecuación Gas Ideal + Ley Prandtl
                      ▼
     [ 6. Streamlit Geospatial Dashboard ]
```

---

## 📊 Datos de Entrada (Schemas)

El sistema procesa dos archivos JSON ubicados en `data/raw/`:

### A. Catastro de Estaciones (`stations.json`)
```json
[
  {
    "id": "4ca4c103-894d-4f59-a911-f3abb8077e3c",
    "name": "Alto Vista",
    "code": "WS-ALT-11",
    "latitude": 12.5912,
    "longitude": -70.0374,
    "elevation_m": 25,
    "district": "Noord",
    "is_active": true
  }
]
```

### B. Telemetría Meteorológica (`telemetry.json`)
```json
[
  {
    "id": "5b9f3e1c-e410-4bc7-a0f5-ef4752ddfee9",
    "station_id": "4ca4c103-894d-4f59-a911-f3abb8077e3c",
    "timestamp": "2026-03-31T22:00:00Z",
    "temperature_c": 30.4,
    "humidity_pct": 71.8,
    "wind_speed_kmh": 21.5,
    "wind_direction_deg": 45.6,
    "pressure_hpa": 1016,
    "precipitation_mm": 0,
    "visibility_km": 11.8,
    "uv_index": 0
  }
]
```

---

## 🧠 Fundamentos Físicos y Matemáticos

### 1. Conversión de Coordenadas a Teselas (Web Mercator EPSG:3857)
Para un nivel de zoom **z**, la transformación de longitud (**lon**) y latitud (**lat**) en grados decimales a índices enteros de tesela **(x, y)** se calcula como:

```text
x = floor( ((lon + 180) / 360) · 2ᶻ )

y = floor( (1 - ln(tan(lat_rad) + 1/cos(lat_rad)) / π) · 2^(z-1) )
```

> *Donde `lat_rad = lat · (π / 180)`. En Python:*  
> `math.log(math.tan(rad) + 1 / math.cos(rad))`

---

### 2. Densidad Real del Aire (ρ)
Calculada mediante la ecuación de estado del gas ideal seco a partir de la presión atmosférica absoluta **p** y la temperatura absoluta **T**:

```text
               p · 100
ρ = ─────────────────────────────   [kg/m³]
    R_aire · (T_celsius + 273.15)
```

* **R_aire = 287.058 J/(kg·K)** (constante específica del aire seco).
* **T = T_celsius + 273.15** (temperatura en Kelvin).
* **p = pressure_hpa** (se multiplica por 100 para convertir de hectopascales a Pascales).

---

### 3. Rugosidad de Davenport-Wieringa y Agregación Espacial
Clasificación de rugosidad aerodinámica según la cobertura del suelo:

| ID | Clase | Descripción del terreno | z₀ nominal |
| :-: | :--- | :--- | :-: |
| **0** | Agua / Costa | Superficie marina, lagunas costeras | 0.0002 m |
| **1** | Terreno abierto | Matorral bajo, arena o suelo árido | 0.0300 m |
| **2** | Arbolado | Bosque bajo o matorral denso | 0.1000 m |
| **3** | Urbano | Edificaciones e infraestructuras | 0.5000 m |

Para un paisaje heterogéneo en el sector de barlovento (**wind_direction_deg ± 30°**), la rugosidad efectiva se calcula mediante la **media logarítmica ponderada por área**:

```text
ln(z₀,eff) = Σ [ f_c · ln(z₀,c) ]   ===>   z₀,eff = exp( Σ [ f_c · ln(z₀,c) ] )
```

*Donde **f_c** es la proporción de píxeles pertenecientes a la clase **c** en el sector de barlovento (Σ f_c = 1).*

---

### 4. Perfil Logarítmico del Viento (Ley de Prandtl)
Extrapolación vertical de la velocidad desde la altura del sensor (**z_sensor = 10 m**) hasta la cota del buje de la turbina (**z_hub = 80 m**):

```text
                 ln(z_hub / z₀,eff)
v(z_hub) = v_sensor · ──────────────────────   [m/s]
                ln(z_sensor / z₀,eff)
```

> *Nota: Convertir previamente la telemetría a unidades del SI:*  
> `v_sensor = wind_speed_kmh / 3.6`

---

### 5. Densidad de Potencia Eólica (WPD)
Energía cinética disponible por metro cuadrado de área de barrido del rotor:

```text
WPD = 0.5 · ρ · (v_hub)³   [W/m²]
```

---

## 🛠 Stack Tecnológico

| Componente | Tecnologías |
| :--- | :--- |
| **Lenguaje Core** | Python 3.10+ |
| **ETL & Tipado** | Pandas, Pydantic v2 |
| **Web Scraping** | Requests, AioHTTP, Pillow |
| **Deep Learning** | PyTorch, Torchvision, Albumentations |
| **GIS & Geometría** | Shapely, NumPy, OpenCV |
| **Frontend & Mapas** | Streamlit, Folium, Leaflet |
| **DevOps & QA** | Pytest, Docker, GitHub Actions |

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
* Python 3.10 o superior instalado.
* Git.

```bash
# 1. Clonar el repositorio
git clone [https://github.com/usuario/aeromap.git](https://github.com/usuario/aeromap.git)
cd aeromap

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Ejecución del Pipeline

```bash
# Paso 1: Ejecutar ETL y validación de datos
python -m src.etl.loader

# Paso 2: Descargar teselas y armar mosaicos satelitales
python -m src.scraping.tile_scraper

# Paso 3: Segmentación y cálculo de potencial eólico
python -m src.physics.wind_profile

# Paso 4: Levantar el Dashboard interactivo
streamlit run src/app/main.py
```

---

## 📁 Estructura del Repositorio

```text
aeromap/
├── data/
│   ├── raw/                  # JSONs de origen (stations, telemetry)
│   ├── tiles/                # Teselas individuales descargadas (.png)
│   ├── processed/            # Mosaicos ensamblados y datasets procesados
│   └── models/               # Checkpoints y pesos del modelo (.pth)
├── src/
│   ├── etl/
│   │   ├── schemas.py        # Modelos Pydantic de validación
│   │   ├── loader.py         # Cruce relacional y limpieza
│   │   └── geo_utils.py      # Transformación WGS84 -> Slippy Map Tiles
│   ├── scraping/
│   │   └── tile_scraper.py   # Descargador concurrente y ensamblador Pillow
│   ├── vision/
│   │   ├── unet.py           # Arquitectura de segmentación semántica
│   │   ├── dataset.py        # PyTorch Dataset y transformaciones
│   │   └── inference.py      # Generación de máscaras de clases
│   ├── physics/
│   │   ├── roughness.py      # Sector de barlovento y cálculo de z0
│   │   └── wind_profile.py   # Ley de gas ideal, Prandtl y WPD
│   └── app/
│       └── main.py           # Aplicación visual interactiva (Streamlit)
├── tests/                    # Tests unitarios y de integración (pytest)
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🎯 Roadmap e Hitos de Entrega

- [x] **Hito 1: Anteproyecto - Plan de trabajo** `(04 oct - 23:59)`
  - [x] Formulación del problema, alcance y objetivos.
  - [x] Definición de requisitos funcionales y no funcionales.
  - [x] Cronograma WBS/Gantt y planificación.
- [ ] **Hito 2: ETL** `(08 nov - 23:59)`
  - [x] Validación de esquemas con Pydantic.
  - [x] Conversor geográfico WGS84 → Slippy Map Tiles.
  - [ ] Scraper concurrente de teselas satelitales y cosido de mosaicos 3 × 3.
- [ ] **Hito 3: Check 1** `(16 nov - 23:59)`
  - [ ] Control de calidad del dataset multimodal resultante.
  - [ ] Implementación del recorte por sector de barlovento (±30°).
  - [ ] Pipeline base para el entrenamiento de segmentación.
- [ ] **Hito 4: Check Modelo** `(15 dic - 23:59)`
  - [ ] Red U-Net entrenada con mIoU ≥ 0.75.
  - [ ] Inferencia de máscaras y cómputo de z₀,eff.
  - [ ] Extrapolación vertical de viento y cálculo de WPD (W/m²).
- [ ] **Hito 5: App y Memoria** `(12 ene - 23:59)`
  - [ ] Cuadro de mando interactivo en Streamlit/Folium.
  - [ ] Contenedorización con Docker.
  - [ ] Redacción final de la memoria académica.

---

## 👥 Reglas de Contribución para Desarrolladores y Agentes

1. **Tipado Estricto:** Toda función debe contener *Type Hints* completos y validaciones mediante esquemas Pydantic.
2. **Descarga Responsable:** El scraper debe incorporar cabeceras `User-Agent` descriptivas y reintentos automáticos con retroceso exponencial (*exponential backoff*).
3. **Consistencia Física:** 
   * Convertir siempre `wind_speed_kmh` a **m/s** dividiendo entre 3.6.
   * Multiplicar `pressure_hpa` por 100 para obtener Pascales antes de calcular ρ.
4. **Testing Obligatorio:** Todo nuevo módulo en `src/` debe incluir su correspondiente test en `tests/` con una cobertura mínima del 80%.

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.
