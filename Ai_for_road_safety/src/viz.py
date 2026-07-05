"""Stage 5 - visualization: self-contained interactive risk map (Leaflet).

Writes a single HTML file with the scored network embedded: link color =
risk-score band (quantile-anchored: top 3% / 10% / 25%), line width = traffic
percentile, dashed = posted limit unverified. Popups show the diagnosis,
posted vs recommended limit, observed speeds, and a Street View link.

Needs internet when opened (basemap tiles + Leaflet from CDN).
"""

import json
from shapely.geometry import mapping
import pandas as pd
from . import config


def _round_coords(obj, nd=5):
    if isinstance(obj, (list, tuple)):
        return [_round_coords(o, nd) for o in obj]
    return round(obj, nd)


def _street_view(link):
    """StreetImageLink stores lon1,lat1,lon2,lat2 -> 'lat,lon' for Google."""
    parts = str(link or "").split(",")
    return f"{parts[1]},{parts[0]}" if len(parts) >= 2 else ""


def build_map(gdf, out_html=None):
    out_html = out_html or config.MAP_HTML
    g = gdf.to_crs(4326)

    feats = []
    for _, r in g.iterrows():
        geom = mapping(r.geometry)
        geom["coordinates"] = _round_coords(geom["coordinates"])
        feats.append({"type": "Feature", "geometry": geom, "properties": {
            "n": r.get("names_primary") or r["DISSOLVE_ID"],
            "id": r["DISSOLVE_ID"],
            "c": r["RoadClass"],
            "s": round(float(r["Stand_Risk_Score"]), 1),
            "cat": r["Category"],
            "act": r["Recommended_Action"],
            "pl": int(r["SpeedLimit"]) if pd.notna(r["SpeedLimit"]) else None,
            "lv": 1 if bool(r["Limit_Verified"]) else 0,
            "rl": int(r["Recommended_Limit"]),
            "v85": round(float(r["F85thPercentileSpeed"])),
            "med": round(float(r["MedianSpeed"])),
            "sz": 1 if bool(r["School_Zone_Flag"]) else 0,
            "tp": round(100 * float(r["RankedPercentile"])),
            "km": round(float(r["Shape_Length"]) / 1000, 1),
            "sv": _street_view(r.get("StreetImageLink")),
        }})

    q = gdf["Stand_Risk_Score"].quantile
    t75, t90, t97 = round(q(0.75), 1), round(q(0.90), 1), round(q(0.97), 1)

    html = (_TEMPLATE
            .replace("__DATA__", json.dumps({"type": "FeatureCollection", "features": feats},
                                            separators=(",", ":")))
            .replace("__T75__", str(t75)).replace("__T90__", str(t90)).replace("__T97__", str(t97)))
    with open(out_html, "w") as f:
        f.write(html)
    print(f"Saved {out_html} ({len(feats)} links; bands at {t75}/{t90}/{t97})")


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maharashtra Road-Safety Risk Map</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet">
<style>
  :root{--ink:#20262e;--paper:#f7f5f0;--line:#d8d2c6;--ring:#c1121f;}
  html,body{margin:0;height:100%;font:14px/1.45 system-ui,sans-serif;color:var(--ink);}
  #map{position:absolute;inset:0;background:#e9e6df;}
  .panel{position:absolute;z-index:1000;top:16px;left:16px;width:290px;max-height:calc(100% - 32px);
         overflow:auto;background:var(--paper);border:1px solid var(--line);border-radius:10px;
         box-shadow:0 4px 18px rgba(32,38,46,.14);padding:16px 18px;}
  .panel h1{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:24px;
            letter-spacing:.04em;text-transform:uppercase;margin:0;}
  .rule{height:3px;background:var(--ring);border-radius:2px;width:44px;margin:6px 0 12px;}
  .sect{font-family:"Barlow Condensed",sans-serif;font-weight:600;font-size:13px;letter-spacing:.09em;
        text-transform:uppercase;color:#5c6470;margin:14px 0 6px;}
  .leg{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:12.5px;}
  .sw{width:26px;height:5px;border-radius:2px;flex:none;}
  label.cat{display:flex;align-items:center;gap:7px;margin:4px 0;font-size:12.5px;cursor:pointer;}
  label.cat input{accent-color:var(--ring);}
  .count{font-family:"Barlow Condensed",sans-serif;font-size:20px;font-weight:700;}
  .count small{font-family:system-ui;font-size:11px;color:#5c6470;font-weight:400;}
  input[type=range]{width:100%;accent-color:var(--ring);}
  .srow{display:flex;justify-content:space-between;font-size:11px;color:#5c6470;}
  .leaflet-popup-content-wrapper{background:var(--paper);color:var(--ink);border-radius:10px;
        border:1px solid var(--line);}
  .leaflet-popup-content{margin:14px 16px;width:auto!important;}
  .pp h3{font-family:"Barlow Condensed",sans-serif;font-size:19px;font-weight:700;margin:0 0 1px;max-width:230px;}
  .pp .meta{font-size:11.5px;color:#5c6470;margin-bottom:9px;}
  .pp .cat{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px;
           background:#eee7da;margin-bottom:9px;}
  .discs{display:flex;gap:16px;align-items:flex-end;margin:4px 0 8px;}
  .disc{width:46px;height:46px;border-radius:50%;background:#fff;border:5px solid var(--ring);
        display:flex;align-items:center;justify-content:center;
        font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:19px;}
  .disc.unv{border-color:#9aa1ab;border-style:dashed;}
  .dl{font-size:10px;color:#5c6470;text-align:center;margin-top:3px;max-width:64px;}
  .kv{font-size:12.5px;margin:2px 0;}
  .kv b{font-family:"Barlow Condensed",sans-serif;font-size:15px;}
  .score{font-family:"Barlow Condensed",sans-serif;font-size:26px;font-weight:700;}
  .pp a{color:var(--ring);font-size:12px;}
  .act{font-size:11.5px;background:#eee7da;border-radius:6px;padding:5px 8px;margin-top:7px;}
  .note{font-size:11px;color:#8a4600;background:#f5e8cf;border-radius:6px;padding:4px 7px;margin-top:6px;}
  @media (max-width:640px){.panel{left:8px;right:8px;top:auto;bottom:8px;width:auto;max-height:44%;}}
</style>
</head>
<body>
<div id="map" role="application" aria-label="Road-safety risk map"></div>
<div class="panel">
  <h1>Road-Safety Risk Map</h1>
  <div class="rule"></div>
  <div class="count"><span id="cnt"></span> <small>links shown</small></div>
  <div class="sect">Risk score</div>
  <div class="leg"><span class="sw" style="background:#a4161a"></span>&ge; __T97__ <small>critical &middot; top 3%</small></div>
  <div class="leg"><span class="sw" style="background:#d1622b"></span>__T90__&ndash;__T97__ <small>high &middot; top 10%</small></div>
  <div class="leg"><span class="sw" style="background:#e0a63a"></span>__T75__&ndash;__T90__ <small>moderate &middot; top 25%</small></div>
  <div class="leg"><span class="sw" style="background:#2e7d6e"></span>&lt; __T75__ <small>low</small></div>
  <div class="leg"><span class="sw" style="background:repeating-linear-gradient(90deg,#5c6470 0 6px,transparent 6px 11px)"></span><small>dashed = posted limit unverified</small></div>
  <div class="leg"><span class="sw" style="background:#5c6470;height:2px"></span><small>line width = traffic volume</small></div>
  <div class="sect">Diagnosis</div>
  <div id="cats"></div>
  <div class="sect">Minimum score</div>
  <input type="range" id="minscore" min="0" max="100" value="0" step="1" aria-label="Minimum score filter">
  <div class="srow"><span>0</span><span id="msv">0</span><span>100</span></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const DATA = __DATA__;
const map = L.map('map',{preferCanvas:true});
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
  {attribution:'&copy; OpenStreetMap contributors, Overture Maps Foundation &middot; &copy; CARTO',maxZoom:19}).addTo(map);
const col = s => s>=__T97__?'#a4161a':s>=__T90__?'#d1622b':s>=__T75__?'#e0a63a':'#2e7d6e';
const style = p => ({color:col(p.s),weight:1+2.5*p.tp/100,opacity:.85,dashArray:p.lv?null:'6 5'});
function popup(p){
  const sv = p.sv?`<a href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${p.sv}" target="_blank" rel="noopener">Open Street View &rarr;</a>`:'';
  return `<div class="pp"><h3>${p.n}</h3>
    <div class="meta">${p.id} &middot; ${p.c} &middot; ${p.km} km</div>
    <div class="cat">${p.cat}</div>
    <div class="discs">
      <div><div class="disc ${p.lv?'':'unv'}">${p.pl}</div><div class="dl">posted${p.lv?'':' (unverified)'}</div></div>
      <div><div class="disc">${p.rl}</div><div class="dl">recommended</div></div>
      <div style="margin-left:6px"><div class="score">${p.s}</div><div class="dl" style="max-width:none">risk score</div></div>
    </div>
    <div class="kv">Observed: <b>${p.med}</b> median &middot; <b>${p.v85}</b> 85th pct km/h</div>
    <div class="kv">Traffic: <b>${p.tp}</b><small>th</small> percentile</div>
    <div class="act">${p.act}</div>
    ${p.sz?'<div class="note">School / kindergarten frontage &mdash; localized 30 km/h zone advised</div>':''}
    <div style="margin-top:7px">${sv}</div></div>`;
}
const layers=[];
const gj = L.geoJSON(DATA,{style:f=>style(f.properties),onEachFeature:(f,l)=>{
  layers.push(l);
  l.bindPopup(popup(f.properties),{maxWidth:290});
  l.on('mouseover',()=>l.setStyle({weight:style(f.properties).weight+2.5,opacity:1}));
  l.on('mouseout',()=>l.setStyle(style(f.properties)));
}}).addTo(map);
map.fitBounds(gj.getBounds());
const catsDiv=document.getElementById('cats');
[...new Set(DATA.features.map(f=>f.properties.cat))].forEach(c=>{
  const n=DATA.features.filter(f=>f.properties.cat===c).length;
  catsDiv.insertAdjacentHTML('beforeend',
    `<label class="cat"><input type="checkbox" checked data-cat="${c}">${c} <small style="color:#5c6470">(${n})</small></label>`);
});
function refresh(){
  const on=new Set([...document.querySelectorAll('#cats input:checked')].map(i=>i.dataset.cat));
  const min=+document.getElementById('minscore').value;
  document.getElementById('msv').textContent=min;
  let n=0;
  layers.forEach(l=>{
    const p=l.feature.properties, show=on.has(p.cat)&&p.s>=min;
    if(show){if(!map.hasLayer(l))map.addLayer(l);n++;}
    else if(map.hasLayer(l))map.removeLayer(l);
  });
  document.getElementById('cnt').textContent=n.toLocaleString();
}
document.getElementById('cats').addEventListener('change',refresh);
document.getElementById('minscore').addEventListener('input',refresh);
refresh();
</script>
</body>
</html>"""
