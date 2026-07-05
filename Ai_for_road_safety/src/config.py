"""Configuration constants for the OSM road-safety scoring pipeline.
"""

from pathlib import Path
# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULT_DIR = BASE_DIR / "results"
# --- OSM feature extraction -------------------------------------------------
LINKS_GPKG  = DATA_DIR/"ADB_Innovation_Maharashtra.geojson"
OSM_GPKG    = DATA_DIR/"western-zone.gpkg"
POI_LAYERS  = ["gis_osm_pois_free", "gis_osm_pois_a_free"]  # points + polygons
CATEGORIES  = ["school", "college", "university", "kindergarten"]
INNER_M, OUTER_M = 50, 200

RES_LAYER      = "gis_osm_landuse_a_free"                   # Geofabrik landuse polygons
RES_CATEGORIES = ["residential"]
OUT_GPKG    = "links_with_counts.gpkg"
FINAL_DATA = RESULT_DIR / "Maha_processed.geojson"



# --- Exposure / context-aware safe speed ------------------------------------
ROAD_CLASS_BASE_SPEED = {"motorway": 100, "trunk": 90, "primary": 80, "secondary": 70}

SCHOOL_CAP = 50
URBAN_CAP = 50
RESIDENTIAL_CAP = 60
VERIFIED_LIMITS = {20, 30, 40, 50, 60, 70, 80, 90, 100, 120}
RISK_GAP_UNSAFE = 20
NOT_SELF_ENFORCING = 5
OVERPOSTED = 10


MAP_HTML= RESULT_DIR /"Maharashtra_risk_score_map.html"
MODEL_PKL = RESULT_DIR /"Maharashtra_v85.pkl"

