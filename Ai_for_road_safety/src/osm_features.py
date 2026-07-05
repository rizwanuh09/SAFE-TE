"""Stage 1 - OSM spatial feature extraction.

Count deduplicated OSM amenities (school / college / university / kindergarten)
within 200 m of each link, using Geofabrik-style data (fclass field).

Per category:
  1. buffer 50 m around each feature (points + polygons combined)
  2. dissolve overlapping buffers into clusters, take each cluster centroid
  3. buffer 200 m around each centroid
  4. count, per link, how many 200 m buffers it intersects

Residential zones (landuse polygons):
  - if a residential zone intersects a link, count it
  - res_area_count = number of residential zones intersecting the link
  - res_area_sum   = total area (m^2) of those residential zones

Requires: geopandas (>=0.13), shapely (>=2.0)
"""

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union
from shapely.geometry import MultiPolygon
import pyproj

from . import config


def dedup_centroid_buffers(subset, crs):
    """Steps 1-3: 50 m buffer -> dissolve -> centroid -> 200 m buffer."""
    merged = unary_union(subset.geometry.buffer(config.INNER_M).values)
    if merged.is_empty:
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    parts = list(merged.geoms) if isinstance(merged, MultiPolygon) else [merged]
    outer = [p.centroid.buffer(config.OUTER_M) for p in parts]
    return gpd.GeoDataFrame(geometry=outer, crs=crs)


def count_per_link(links, buffers, col):
    """Step 4: how many buffers each link intersects."""
    if len(buffers) == 0:
        links[col] = 0
        return links
    j = gpd.sjoin(links[["geometry"]], buffers, how="inner", predicate="intersects")
    links[col] = j.groupby(j.index).size().reindex(links.index, fill_value=0).astype(int)
    return links


def count_area_per_link(links, zones, count_col, area_col):
    """For each link: how many zones intersect it, and the total area (m^2) of
    those zones. Area is the full polygon area of each intersecting zone (a
    line-vs-polygon intersection has no area), summed per link."""
    if len(zones) == 0:
        links[count_col] = 0
        links[area_col] = 0.0
        return links
    zones = zones[["geometry"]].copy()
    zones["zone_area_m2"] = zones.geometry.area
    j = gpd.sjoin(links[["geometry"]], zones, how="inner", predicate="intersects")
    grp = j.groupby(j.index)
    links[count_col] = grp.size().reindex(links.index, fill_value=0).astype(int)
    links[area_col]  = grp["zone_area_m2"].sum().reindex(links.index, fill_value=0.0)
    return links

def pick_metric_crs(gdf, zone_span_deg=6.0):
    """Single projected CRS for metric distance/area work.
    ~one UTM zone -> best-fit UTM (auto-detected). Wide extent -> data-centred
    equal-area, so distortion stays bounded instead of blowing up at a zone edge."""
    g = gdf.to_crs(4326)                       # need lon/lat to reason about span
    minx, miny, maxx, maxy = g.total_bounds
    if (maxx - minx) <= zone_span_deg:
        return g.estimate_utm_crs()            # single best UTM zone
    lon0, lat0 = (minx + maxx) / 2, (miny + maxy) / 2
    return pyproj.CRS.from_proj4(
        f"+proj=laea +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs") 
 


def build_osm_features():
    """Run the full stage-1 pipeline and write OUT_GPKG / OUT_GEOJSON."""
    # --- Step 1: load + filter amenities, reproject to links' CRS ----------
    links = gpd.read_file(config.LINKS_GPKG).reset_index(drop=True)
    metric = pick_metric_crs(links)
    links = links.to_crs(metric)
    
    print(f"Links: {len(links)} features, CRS {metric.to_epsg()}")
    print(links.crs)   # expect EPSG:4326
    frames = []
    for layer in config.POI_LAYERS:
        g = gpd.read_file(config.OSM_GPKG, layer=layer)
        g = g[g["fclass"].isin(config.CATEGORIES)].to_crs(metric)
        # polygons -> centroids (in meters) so every 50 m buffer is a clean circle
        is_poly = g.geom_type.isin(["Polygon", "MultiPolygon"])
        g.loc[is_poly, "geometry"] = g.loc[is_poly, "geometry"].centroid
        frames.append(g[["fclass", "geometry"]])
    osm = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=metric)

    print("\nStep 1 - raw amenity counts (points + polygon centroids):")
    print(osm["fclass"].value_counts().reindex(config.CATEGORIES).to_string())

    # --- Steps 2-4: per category -------------------------------------------
    print("\nStep 2 - dedup (raw -> clusters):")
    for cat in config.CATEGORIES:
        subset = osm[osm["fclass"] == cat]
        buffers = dedup_centroid_buffers(subset, metric)
        print(f"  {cat:13} {len(subset):>5} -> {len(buffers):>5} clusters")
        links = count_per_link(links, buffers, f"n_{cat}")

    links["n_college_university"] = links["n_college"] + links["n_university"]

    # --- Residential zones: intersect link -> count + total area (m^2) ------
    res = gpd.read_file(config.OSM_GPKG, layer=config.RES_LAYER)
    res = res[res["fclass"].isin(config.RES_CATEGORIES)].to_crs(metric)
    print(f"\nResidential zones: {len(res)} polygons")
    links = count_area_per_link(links, res, "res_area_count", "res_area_sum")
    print(f"  links intersecting >=1 residential zone: "
          f"{(links['res_area_count'] > 0).sum()}")
    print(f"  total res_area_sum across all links: "
          f"{links['res_area_sum'].sum():,.0f} m^2")

    # --- Step 3 checks ------------------------------------------------------
    print("\nStep 3 - total links intersecting >=1 buffer, per category:")
    for cat in config.CATEGORIES:
        print(f"  n_{cat:11} sum={links[f'n_{cat}'].sum():>6}  "
              f"links_with>=1={(links[f'n_{cat}']>0).sum():>6}")

    # --- Step 4: save (already in 32643; keep it, it's metric & correct) ----
    links.to_file(config.OUT_GPKG, driver="GPKG")
    
    print(f"\nSaved {config.OUT_GPKG}")
    return links


if __name__ == "__main__":
    build_osm_features()
