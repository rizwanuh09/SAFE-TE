"""End-to-end pipeline: OSM features -> exposure/risk scoring -> V85 model.

Run: python main.py

Requires the input data files referenced in src/config.py to be present.
"""

import geopandas as gpd

from src import config, osm_features, exposure, risk_score, model, policy , viz


def run():
    
    # --- Stage 1: OSM spatial features -> writes links_with_counts.gpkg -----
    osm_features.build_osm_features()

    # --- Stage 2: exposure indices + risk score ----------------------------
    gdf = gpd.read_file(config.OUT_GPKG)
    gdf_valid = gdf[gdf["SampleSize_avg"] > 0].copy()

    gdf_valid = exposure.add_density_features(gdf_valid)
    gdf_valid = exposure.standardize_density(gdf_valid)
    gdf_valid = exposure.add_vru_exposure(gdf_valid)
    gdf_valid = exposure.add_safe_context_speed(gdf_valid)
    gdf_valid = exposure.add_traffic_exposure(gdf_valid)
    gdf_valid = risk_score.add_risk_score(gdf_valid)
    print(gdf_valid.columns)
    
    gdf_valid = policy.add_policy_outcomes(gdf_valid)
    
    gdf_valid.to_file(config.FINAL_DATA)
    

    # --- Stage 3: V85 gradient boosting model ------------------------------
    trained_model = model.train_v85_model(gdf_valid)
    model.save_model( trained_model)
    viz.build_map(gdf_valid, config.MAP_HTML)

    return gdf_valid


if __name__ == "__main__":
    print("DATA_DIR:", config.DATA_DIR)
    print("OSM_GPKG:", config.OSM_GPKG)
    print("Exists:", config.OSM_GPKG.exists())
    run()
