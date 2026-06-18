from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import json
import os

app = Flask(__name__)
CORS(app)

# ── LOAD DATA AT STARTUP ──────────────────────────────────────────────────────
BASE = os.path.join(os.path.dirname(__file__), '..', 'data')

print("Loading data files...")
df_violations  = pd.read_csv(os.path.join(BASE, 'violations_sample.csv'))
df_hotspots    = pd.read_csv(os.path.join(BASE, 'hotspots.csv'))
df_clusters    = pd.read_csv(os.path.join(BASE, 'clusters.csv'))

# Parse datetime
df_violations['created_datetime'] = pd.to_datetime(
    df_violations['created_datetime'], utc=True, errors='coerce'
)
df_violations = df_violations.dropna(subset=['created_datetime'])
df_violations['hour']        = df_violations['created_datetime'].dt.hour
df_violations['day_of_week'] = df_violations['created_datetime'].dt.day_name()
df_violations['month']       = df_violations['created_datetime'].dt.month_name()
df_violations = df_violations[df_violations['junction_name'] != 'No Junction']

print(f"✅ {len(df_violations):,} violations | "
      f"{len(df_hotspots)} hotspots | "
      f"{len(df_clusters)} clusters ready\n")

# ── HELPERS ───────────────────────────────────────────────────────────────────
def safe_json(obj):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, (np.integer,)):  return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, (np.ndarray,)):  return obj.tolist()
    return obj

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return jsonify({
        "project": "Gridlock 2.0 — Parking Enforcement Intelligence",
        "team":    "Amulya Singabhattu",
        "theme":   "Poor Visibility on Parking-Induced Congestion",
        "endpoints": [
            "/api/stats",
            "/api/hotspots",
            "/api/clusters",
            "/api/violations/hourly",
            "/api/violations/daily",
            "/api/violations/monthly",
            "/api/violations/types",
            "/api/violations/vehicles",
            "/api/heatmap-points",
        ]
    })


@app.route('/api/stats')
def stats():
    """Summary KPI cards for the dashboard."""
    critical = df_clusters[df_clusters['risk_level'] == 'CRITICAL']
    high     = df_clusters[df_clusters['risk_level'] == 'HIGH']

    top_junction = (
        df_violations['junction_name']
        .value_counts()
        .idxmax()
    )

    return jsonify({
        "total_violations":   int(len(df_violations)),
        "total_clusters":     int(len(df_clusters)),
        "critical_zones":     int(len(critical)),
        "high_risk_zones":    int(len(high)),
        "junctions_monitored": int(df_violations['junction_name'].nunique()),
        "police_stations":    int(df_violations['police_station'].nunique()),
        "top_hotspot":        str(top_junction),
        "date_range": {
            "from": str(df_violations['created_datetime'].min().date()),
            "to":   str(df_violations['created_datetime'].max().date()),
        }
    })


@app.route('/api/hotspots')
def hotspots():
    """Top enforcement priority junctions."""
    limit = int(request.args.get('limit', 20))
    exclude_no_junction = df_hotspots[
        df_hotspots['junction_name'] != 'No Junction'
    ].head(limit)

    records = []
    for _, row in exclude_no_junction.iterrows():
        records.append({
            "junction_name":    str(row['junction_name']),
            "total_violations": int(row['total_violations']),
            "unique_days":      int(row['unique_days']),
            "priority_score":   round(float(row['priority_score']), 1),
            "lat":              float(row['avg_lat']),
            "lon":              float(row['avg_lon']),
        })
    return jsonify(records)


@app.route('/api/clusters')
def clusters():
    """All DBSCAN clusters with risk classification."""
    records = []
    for _, row in df_clusters.iterrows():
        records.append({
            "cluster_id":       int(row['cluster']),
            "rank":             int(row['rank']),
            "top_junction":     str(row['top_junction']),
            "total_violations": int(row['total_violations']),
            "unique_days":      int(row['unique_days']),
            "unique_vehicles":  int(row['unique_vehicles']),
            "peak_hour":        int(row['peak_hour']),
            "priority_score":   float(row['priority_score_norm']),
            "risk_level":       str(row['risk_level']),
            "center_lat":       float(row['center_lat']),
            "center_lon":       float(row['center_lon']),
        })
    return jsonify(records)


@app.route('/api/violations/hourly')
def violations_hourly():
    """Violation count by hour of day."""
    hourly = (
        df_violations.groupby('hour')
        .size()
        .reset_index(name='count')
        .sort_values('hour')
    )
    return jsonify(hourly.to_dict(orient='records'))


@app.route('/api/violations/daily')
def violations_daily():
    """Violation count by day of week."""
    day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    daily = (
        df_violations.groupby('day_of_week')
        .size()
        .reindex(day_order)
        .reset_index(name='count')
        .rename(columns={'day_of_week': 'day'})
    )
    return jsonify(daily.to_dict(orient='records'))


@app.route('/api/violations/monthly')
def violations_monthly():
    """Violation count by month."""
    month_order = ['January','February','March','April','May','June',
                   'July','August','September','October','November','December']
    monthly = (
        df_violations.groupby('month')
        .size()
        .reset_index(name='count')
        .rename(columns={'month': 'month'})
    )
    monthly['month'] = pd.Categorical(monthly['month'], categories=month_order, ordered=True)
    monthly = monthly.sort_values('month')
    return jsonify(monthly.to_dict(orient='records'))


@app.route('/api/violations/types')
def violation_types():
    """Top violation types."""
    import ast
    def parse_v(v):
        try:    return ast.literal_eval(v)
        except: return []

    df_exp = df_violations.copy()
    df_exp['vlist'] = df_exp['violation_type'].apply(parse_v)
    df_exp = df_exp.explode('vlist')
    df_exp['vlist'] = df_exp['vlist'].astype(str).str.strip()

    top = (
        df_exp[df_exp['vlist'] != 'nan']
        .groupby('vlist')
        .size()
        .reset_index(name='count')
        .sort_values('count', ascending=False)
        .head(10)
        .rename(columns={'vlist': 'violation_type'})
    )
    return jsonify(top.to_dict(orient='records'))


@app.route('/api/violations/vehicles')
def violation_vehicles():
    """Top vehicle types involved in violations."""
    vehicles = (
        df_violations.groupby('vehicle_type')
        .size()
        .reset_index(name='count')
        .sort_values('count', ascending=False)
        .head(10)
    )
    return jsonify(vehicles.to_dict(orient='records'))


@app.route('/api/heatmap-points')
def heatmap_points():
    """Lat/lon points for frontend heatmap (sampled)."""
    limit = int(request.args.get('limit', 5000))
    sample = (
        df_violations[['latitude', 'longitude']]
        .dropna()
        .sample(min(limit, len(df_violations)), random_state=42)
    )
    points = sample.values.tolist()
    return jsonify(points)


@app.route('/api/enforcement/recommend')
def enforcement_recommend():
    """Top zones needing enforcement RIGHT NOW based on current hour."""
    from datetime import datetime, timezone
    current_hour = datetime.now(timezone.utc).hour

    # Find clusters whose peak hour is within 2 hours of now
    df_clusters['hour_diff'] = abs(df_clusters['peak_hour'] - current_hour)
    urgent = df_clusters[df_clusters['hour_diff'] <= 2].sort_values(
        'priority_score_norm', ascending=False
    ).head(5)

    records = []
    for _, row in urgent.iterrows():
        records.append({
            "junction":     str(row['top_junction']),
            "risk_level":   str(row['risk_level']),
            "score":        float(row['priority_score_norm']),
            "peak_hour":    int(row['peak_hour']),
            "lat":          float(row['center_lat']),
            "lon":          float(row['center_lon']),
        })
    return jsonify({
        "current_hour": current_hour,
        "recommendations": records
    })


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)