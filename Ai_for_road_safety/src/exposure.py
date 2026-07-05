"""Stage 2 - exposure indices and context-aware safe speed.

Each function takes a GeoDataFrame of valid links (SampleSize_avg > 0) and
returns it with new columns added. Logic is unchanged from the notebook.
"""

from . import config

# Per-length amenity/residential densities, standardized downstream.
DENSITY_COLS = ["d_school", "d_kindergarten", "d_coll_uni", "d_res_count", "d_res_area"]


def add_density_features(gdf):
    """Per-link densities = raw counts / link length."""
    gdf["d_school"]        = gdf["n_school"] / gdf["Shape_Length"]
    gdf["d_kindergarten"]  = gdf["n_kindergarten"] / gdf["Shape_Length"]
    gdf["d_coll_uni"]      = gdf["n_college_university"] / gdf["Shape_Length"]
    gdf["d_res_count"]     = gdf["res_area_count"] / gdf["Shape_Length"]
    gdf["d_res_area"]      = gdf["res_area_sum"] / gdf["Shape_Length"]
    return gdf


def standardize_density(gdf):
    """Min-max standardize each density column into stand_<col>."""
    gdf[DENSITY_COLS] = gdf[DENSITY_COLS].fillna(0)
    for col in DENSITY_COLS:
        gdf[f"stand_{col}"] = (gdf[col] - gdf[col].min()) / (gdf[col].max() - gdf[col].min())
    return gdf


def add_vru_exposure(gdf):
    """Vulnerable-road-user exposure from education + residential densities."""
    gdf["VRU_Exposure"] = ((gdf["stand_d_school"]
                          + gdf["stand_d_coll_uni"]
                          + gdf["stand_d_kindergarten"])
                          + ((gdf["stand_d_res_count"] + gdf["stand_d_res_area"]) / 2)) / 2

    gdf["Stand_VRU_Exposure"] = (gdf["VRU_Exposure"] - gdf["VRU_Exposure"].min()) / (
        gdf["VRU_Exposure"].max() - gdf["VRU_Exposure"].min())
    return gdf


def add_safe_context_speed(gdf):
    """Context-aware safe speed (road-class base, capped by urban / school /
    residential context) plus the derived speed-exposure columns."""
    gdf["Safe_Context_Speed"] = gdf["RoadClass"].map(config.ROAD_CLASS_BASE_SPEED)

    urban = gdf["LandUse"].eq("URBAN")
    sch_present = (gdf["d_school"] + gdf["d_kindergarten"] + gdf["d_coll_uni"]) > 0
    res_thresh = gdf.loc[gdf["d_res_count"] > 0, "d_res_count"].median()
    res_frontage = gdf["d_res_count"] >= res_thresh

    gdf.loc[urban, "Safe_Context_Speed"] = (gdf.loc[urban, "Safe_Context_Speed"].clip(upper=config.URBAN_CAP))
    gdf.loc[sch_present, "Safe_Context_Speed"] = (gdf.loc[sch_present, "Safe_Context_Speed"].clip(upper=config.SCHOOL_CAP))

    res_condition = res_frontage & ~urban & ~sch_present
    gdf.loc[res_condition, "Safe_Context_Speed"] = (gdf.loc[res_condition, "Safe_Context_Speed"].clip(upper=config.RESIDENTIAL_CAP))

    gdf["School_Zone_Flag"] = sch_present
    gdf["SpeedLimit"] = pd.to_numeric(gdf["SpeedLimit"],errors="coerce").fillna(55)
    gdf["Limit_Verified"] = gdf["SpeedLimit"] % 10 == 0
    gdf["Recommended_Limit"] = gdf["Safe_Context_Speed"].astype(int)

    gdf["Risk_gap"] = gdf["F85thPercentileSpeed"] - gdf["Safe_Context_Speed"]
    gdf["Speed_Exposure"] = gdf["Risk_gap"].clip(lower=0)

    gdf["Stand_Speed_Exposure"] = (gdf["Speed_Exposure"] - gdf["Speed_Exposure"].min()) / (
        gdf["Speed_Exposure"].max() - gdf["Speed_Exposure"].min())
    return gdf


def add_traffic_exposure(gdf):
    """Min-max standardized traffic exposure from WeightedSample."""
    gdf["Stand_Traffic_Exposure"] = (gdf["WeightedSample"] - gdf["WeightedSample"].min()) / (
        gdf["WeightedSample"].max() - gdf["WeightedSample"].min())
    return gdf
