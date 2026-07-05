"""Stage 3 - gradient-boosted regression for 85th-percentile speed (V85)."""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import pickle
from . import config

def train_v85_model(gdf_valid):
    """Train a sample-weighted GBR to predict F85thPercentileSpeed.

    Returns the fitted model and the sorted feature-importance Series.
    """
    w = np.log1p(gdf_valid["Sample_Size_Total"])
    gdf1 = pd.get_dummies(
        gdf_valid[["Stand_Traffic_Exposure", "Stand_VRU_Exposure",
                   "RoadClass", "LandUse", "Shape_Length", "F85thPercentileSpeed",
                   "PercentOverLimit", "Sample_Size_Total"]],
        columns=["RoadClass", "LandUse"], drop_first=False)

    X_v85 = gdf1.drop(columns=["F85thPercentileSpeed", "PercentOverLimit", "Sample_Size_Total"])
    target_v85 = gdf1["F85thPercentileSpeed"]
    weights_v85 = np.log1p(gdf1["Sample_Size_Total"])

    X_train_v85, X_test_v85, y_train_v85, y_test_v85, weight_train_v85, weight_test_v85 = train_test_split(
        X_v85, target_v85, weights_v85, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42)
    model.fit(X_train_v85, y_train_v85, sample_weight=weight_train_v85)
    pred_train_v85 = model.predict(X_train_v85)
    pred_test_v85 = model.predict(X_test_v85)
    print(f"Training: R2={r2_score(y_train_v85, pred_train_v85):.3f}  "
          f"MAE={mean_absolute_error(y_train_v85, pred_train_v85):.1f} km/h")
    print(f"Testing : R2={r2_score(y_test_v85, pred_test_v85):.3f}  "
          f"MAE={mean_absolute_error(y_test_v85, pred_test_v85):.1f} km/h")
    imp_v85 = pd.Series(model.feature_importances_, index=X_v85.columns).sort_values(ascending=False)
    print("Top features:", imp_v85.head(5).round(3).to_dict())
    return model, imp_v85

def save_model(model):
    with open(config.MODEL_PKL, "wb") as file:
        pickle.dump(model, file)
