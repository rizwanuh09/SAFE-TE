# SAFE-TE Road-Safety Scoring

A geospatial pipeline that derives a context-aware **safe speed** and a composite
**road-safety risk score** for road network links, combining OpenStreetMap
(Geofabrik) amenity and land-use data with speed telemetry. Built around a
Maharashtra road network (Overture links) for the ADB Innovation Challenge.

For every link the pipeline answers three questions:

1. How exposed is this link to vulnerable road users (schools, colleges,
   kindergartens, residential frontage)?
2. What speed is appropriate given the link's road class and surrounding
   context, and how far does observed speed exceed it?
3. Can we predict the 85th-percentile speed (V85) from the link's features?

## Methodology

The analysis runs in three stages.

**Stage 1 - OSM spatial features** (`src/osm_features.py`)
For each education category (school / college / university / kindergarten),
raw OSM points and polygon centroids are buffered by 50 m, overlapping buffers
are dissolved into clusters, each cluster centroid is re-buffered by 200 m, and
the pipeline counts how many of those 200 m zones each link intersects. This
deduplicates dense amenity clusters so a single campus isn't counted many times.
Residential land-use polygons are intersected with links to produce a per-link
count and total area. Output is written to `links_with_counts.gpkg` / `.geojson`.

**Stage 2 - exposure indices and safe speed** (`src/exposure.py`, `src/risk_score.py`)
Counts are converted to per-length densities, min-max standardized, and combined
into three exposure indices:

- **VRU exposure** - education + residential densities.
- **Speed exposure** - the gap between observed 85th-percentile speed and the
  context-aware safe speed, floored at zero.
- **Traffic exposure** - standardized weighted sample volume.

Safe speed starts from a road-class base (motorway 100 → secondary 70) and is
capped down in urban, school, and residential contexts. The three exposure
indices are then blended into a 0-100 **risk score** using entropy weights, so
the more discriminating an index is across the network, the more it counts.

**Stage 3 - V85 model** (`src/model.py`)
A sample-weighted `GradientBoostingRegressor` predicts the 85th-percentile speed
from road class, land use, geometry, and exposure features, reporting R²/MAE and
feature importances.

## Project structure

```
osm-road-safety-scoring/
├── main.py                 # runs all three stages end to end
├── requirements.txt
├── src/
│   ├── config.py           # paths, CRS, categories, speed caps, weights
│   ├── osm_features.py      # stage 1: spatial feature extraction
│   ├── exposure.py          # stage 2: densities, standardization, safe speed
│   ├── risk_score.py        # stage 2: entropy weights + composite score
│   └── model.py             # stage 3: V85 gradient boosting model
├── notebooks/
│   └── Data_from_OSM.ipynb  # original exploratory notebook
├── data/                    # input data (not committed - see below)
├── LICENSE
└── .gitignore
```

## Data

Input data is **not** included in the repository. You need to supply:

- A road-network links file with results (referenced as
  `ADB_Innovation_Maharashtra.geojson` in `config.py`), containing at least the
  columns the pipeline reads: `Shape_Length`, `RoadClass`, `LandUse`,
  `SampleSize_avg`, `SpeedLimit`, `F85thPercentileSpeed`, `WeightedSample`,
  `Sample_Size_Total`, `PercentOverLimit`.
- A Geofabrik OSM extract (`western-zone.gpkg`) with the `gis_osm_pois_free`,
  `gis_osm_pois_a_free`, and `gis_osm_landuse_a_free` layers.

Update the paths at the top of `src/config.py` to point at your files.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

GeoPandas pulls in GDAL/GEOS/PROJ. If `pip` struggles to build them on your
platform, `conda install -c conda-forge geopandas` is the smoother route.

## Usage

Run the full pipeline:

```bash
python main.py
```

Or use the stages individually:

```python
import geopandas as gpd
from src import config, osm_features, exposure, risk_score, model

osm_features.build_osm_features()                

gdf = gpd.read_file(config.OUT_GPKG)
gdf = gdf[gdf["SampleSize_avg"] > 0].copy()
gdf = exposure.add_density_features(gdf)
gdf = exposure.standardize_density(gdf)
gdf = exposure.add_vru_exposure(gdf)
gdf = exposure.add_safe_context_speed(gdf)
gdf = exposure.add_traffic_exposure(gdf)
gdf = risk_score.add_risk_score(gdf)              

model.train_v85_model(gdf)
```


