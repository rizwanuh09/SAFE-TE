"""Stage 4 - policy outcomes: speed-limit misalignment diagnosis per link.

Turns the exposure/safe-speed columns into a policy-facing diagnosis. The
Category answers "what is wrong here"; Recommended_Action answers "what kind
of remedy applies". Prioritization across links (which to fix first) is the
risk score's job, not this module's - the diagnosis stays exposure-free so
recommendations don't depend on traffic volume.

Requires columns from exposure.add_safe_context_speed().
"""

import numpy as np
import pandas as pd

from . import config

# Priority order matters: normative failure (limit above context-safe speed)
# outranks behavioral failure (unsafe observed speeds), which outranks
# compliance/credibility issues.
CATEGORIES = [
    "Limit too high for context",
    "Speeds unsafe for context",
    "Limit not self-enforcing",
    "Wrong Posted Speed",
    "Limit unverified",
]

ACTIONS = {
    "Limit too high for context": "Reduce posted  speed limit toward Recommended Limit; calming at VRU frontage",
    "Speeds unsafe for context": "Design Improvement such as Installing Traffic calming measures",
    "Limit not self-enforcing": "Engineering measures to make the posted limit credible",
    "Wrong Posted Speed": "Review posted limit against road function",
    "Limit unverified": "Field-validate posted limit; use Recommended_Limit as interim reference",
    "Aligned": "No action required",
}


def add_policy_outcomes(gdf):
    """Add Category and Recommended_Action columns."""
    
    gdf = gdf.copy()

    
    numeric_cols = ["SpeedLimit","Safe_Context_Speed"]

    for col in numeric_cols:
        gdf[col] = pd.to_numeric(gdf[col], errors="coerce")
        
    lv = gdf["Limit_Verified"]
    v85 = gdf["F85thPercentileSpeed"]
    conds = [
        lv & (gdf["SpeedLimit"] > gdf["Safe_Context_Speed"]),
        gdf["Risk_gap"] >= config.RISK_GAP_UNSAFE,
        lv & ((v85 - gdf["SpeedLimit"]) >= config.NOT_SELF_ENFORCING),
        lv & ((gdf["SpeedLimit"] - v85) >= config.OVERPOSTED),
        ~lv,
    ]
    gdf["Category"] = np.select(conds, CATEGORIES, default="Aligned")
    gdf["Recommended_Action"] = gdf["Category"].map(ACTIONS)
    return gdf
