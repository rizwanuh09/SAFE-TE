"""Stage 2 (cont.) - entropy weighting and composite risk score."""

import numpy as np

EXPOSURE_COLS = ("Stand_Speed_Exposure", "Stand_VRU_Exposure", "Stand_Traffic_Exposure")


def entropy_weights(df, cols=EXPOSURE_COLS, eps=1e-5):
    """Entropy-based objective weights for the exposure columns."""
    n = len(df)
    x = {}
    for col in cols:
        v = df[col] + eps
        x[col] = -(v * np.log(v)).sum() / n
    denom = sum(1 - xi for xi in x.values())
    return tuple((1 - xi) / denom for xi in x.values())


def add_risk_score(gdf):
    """Entropy-weighted 0-100 risk score across speed / VRU / traffic exposure."""
    weight_speed, weight_vru, weight_traffic = entropy_weights(gdf, cols=EXPOSURE_COLS)

    gdf["Stand_Risk_Score"] = round(100 * (weight_speed * gdf["Stand_Speed_Exposure"]
                                           + weight_vru * gdf["Stand_VRU_Exposure"]
                                           + weight_traffic * gdf["Stand_Traffic_Exposure"]), 2)
    return gdf
