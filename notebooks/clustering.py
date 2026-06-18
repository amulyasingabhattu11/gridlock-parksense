import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import folium
from folium.plugins import HeatMap, MarkerCluster
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("  GRIDLOCK 2.0 — Hotspot Clustering Engine")
print("="*60)

# ── 1. LOAD & CLEAN ───────────────────────────────────────────────────────────
print("\n[1/6] Loading data...")
df = pd.read_csv('data/violations.csv')
df = df[df['junction_name'] != 'No Junction']
df = df.dropna(subset=['latitude', 'longitude'])
df['created_datetime'] = pd.to_datetime(df['created_datetime'], utc=True, errors='coerce')
df = df.dropna(subset=['created_datetime'])
df['hour'] = df['created_datetime'].dt.hour
df['day_of_week'] = df['created_datetime'].dt.dayofweek
print(f"✅ {len(df):,} records ready for clustering")

# ── 2. DBSCAN CLUSTERING ──────────────────────────────────────────────────────
print("\n[2/6] Running DBSCAN clustering...")

# Use lat/lon for clustering (eps in degrees ~500m radius)
coords = df[['latitude', 'longitude']].values

db = DBSCAN(
    # eps must be in radians when using haversine + radians input.
    # Choose approx 500 meter radius: eps = 500m / earth_radius_m
    min_samples=100, # minimum 100 violations to form a cluster
    algorithm='ball_tree',
    metric='haversine',
    n_jobs=1  # avoid heavy multiprocessing memory overhead
)

earth_radius_m = 6371000.0
eps_meters = 500.0
eps_rad = eps_meters / earth_radius_m

print(f"Using DBSCAN eps ≈ {eps_rad:.6e} radians (~{int(eps_meters)} m) and n_jobs=1")

# If dataset is large, skip full-point DBSCAN to avoid O(n^2) memory blowups;
# instead cluster aggregated junction centroids which are far fewer points.
if len(df) > 80000:
    print(f"Large dataset detected ({len(df):,} records). Skipping point-level DBSCAN and using junction-centroid fallback.")
    junctions = (
        df.groupby('junction_name')
          .agg(center_lat=('latitude', 'mean'), center_lon=('longitude', 'mean'), violations=('id', 'count'))
          .reset_index()
    )

    coords_j = junctions[['center_lat', 'center_lon']].values
    min_samples_j = max(3, int(100 / 20))
    print(f"Clustering {len(junctions):,} junction centroids with min_samples={min_samples_j}")

    db_j = DBSCAN(eps=eps_rad, min_samples=min_samples_j, algorithm='ball_tree', metric='haversine', n_jobs=1)
    db_j = db_j.fit(np.radians(coords_j))
    junctions['cluster'] = db_j.labels_

    mapping = junctions.set_index('junction_name')['cluster'].to_dict()
    df['cluster'] = df['junction_name'].map(mapping).fillna(-1).astype(int)

    n_clusters = len(set(junctions['cluster'])) - (1 if -1 in junctions['cluster'].values else 0)
    n_noise = (df['cluster'] == -1).sum()
    print(f"✅ Fallback clustering produced {n_clusters} clusters from {len(junctions):,} junctions")
    print(f"   Noise points after fallback: {n_noise:,}")

else:
    try:
        db = DBSCAN(eps=eps_rad, min_samples=100, algorithm='ball_tree', metric='haversine', n_jobs=1)
        db = db.fit(np.radians(coords))
        df['cluster'] = db.labels_

        n_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
        n_noise = (db.labels_ == -1).sum()
        print(f"✅ Found {n_clusters} hotspot clusters")
        print(f"   Noise points (scattered violations): {n_noise:,}")

    except MemoryError:
        print("⚠️ MemoryError while clustering all points — falling back to junction-centroid clustering")
        junctions = (
            df.groupby('junction_name')
              .agg(center_lat=('latitude', 'mean'), center_lon=('longitude', 'mean'), violations=('id', 'count'))
              .reset_index()
        )

        coords_j = junctions[['center_lat', 'center_lon']].values
        min_samples_j = max(3, int(100 / 20))
        print(f"Clustering {len(junctions):,} junction centroids with min_samples={min_samples_j}")

        db_j = DBSCAN(eps=eps_rad, min_samples=min_samples_j, algorithm='ball_tree', metric='haversine', n_jobs=1)
        db_j = db_j.fit(np.radians(coords_j))
        junctions['cluster'] = db_j.labels_

        mapping = junctions.set_index('junction_name')['cluster'].to_dict()
        df['cluster'] = df['junction_name'].map(mapping).fillna(-1).astype(int)

        n_clusters = len(set(junctions['cluster'])) - (1 if -1 in junctions['cluster'].values else 0)
        n_noise = (df['cluster'] == -1).sum()
        print(f"✅ Fallback clustering produced {n_clusters} clusters from {len(junctions):,} junctions")
        print(f"   Noise points after fallback: {n_noise:,}")

# ── 3. CLUSTER STATS ──────────────────────────────────────────────────────────
print("\n[3/6] Computing cluster statistics...")

cluster_stats = df[df['cluster'] != -1].groupby('cluster').agg(
    total_violations=('id', 'count'),
    unique_junctions=('junction_name', 'nunique'),
    unique_days=('created_datetime', lambda x: x.dt.date.nunique()),
    unique_vehicles=('vehicle_type', 'nunique'),
    center_lat=('latitude', 'mean'),
    center_lon=('longitude', 'mean'),
    peak_hour=('hour', lambda x: x.mode()[0]),
    lat_min=('latitude', 'min'),
    lat_max=('latitude', 'max'),
    lon_min=('longitude', 'min'),
    lon_max=('longitude', 'max'),
).reset_index()

# Top junction per cluster
top_junction = (
    df[df['cluster'] != -1]
    .groupby(['cluster', 'junction_name'])
    .size()
    .reset_index(name='count')
    .sort_values('count', ascending=False)
    .groupby('cluster')
    .first()
    .reset_index()[['cluster', 'junction_name']]
    .rename(columns={'junction_name': 'top_junction'})
)
cluster_stats = cluster_stats.merge(top_junction, on='cluster')

# ── 4. ENFORCEMENT PRIORITY SCORE ─────────────────────────────────────────────
print("\n[4/6] Computing enforcement priority scores...")

cluster_stats['priority_score'] = (
    cluster_stats['total_violations'] * 0.50 +
    cluster_stats['unique_days']       * 0.25 +
    cluster_stats['unique_vehicles']   * 0.15 +
    cluster_stats['unique_junctions']  * 0.10
)

# Normalize to 0–100
max_score = cluster_stats['priority_score'].max()
cluster_stats['priority_score_norm'] = (
    cluster_stats['priority_score'] / max_score * 100
).round(1)

# Risk label
def risk_label(score):
    if score >= 70:   return 'CRITICAL'
    elif score >= 40: return 'HIGH'
    elif score >= 15: return 'MEDIUM'
    else:             return 'LOW'

cluster_stats['risk_level'] = cluster_stats['priority_score_norm'].apply(risk_label)
cluster_stats = cluster_stats.sort_values('priority_score_norm', ascending=False).reset_index(drop=True)
cluster_stats['rank'] = cluster_stats.index + 1

print("\n=== TOP 15 ENFORCEMENT PRIORITY CLUSTERS ===")
print(cluster_stats.head(15)[[
    'rank','top_junction','total_violations',
    'unique_days','peak_hour','priority_score_norm','risk_level'
]].to_string(index=False))

# Save
cluster_stats.to_csv('data/clusters.csv', index=False)
print("\n✅ Saved data/clusters.csv")

# Also save cluster labels back to main df
df[['id','cluster']].to_csv('data/violation_clusters.csv', index=False)

# ── 5. PEAK HOUR ANALYSIS PER CLUSTER ────────────────────────────────────────
print("\n[5/6] Peak hour analysis...")

hour_profile = df[df['cluster'] != -1].groupby(['cluster', 'hour']).size().reset_index(name='count')
peak_hours = hour_profile.loc[hour_profile.groupby('cluster')['count'].idxmax()]
peak_hours = peak_hours.rename(columns={'hour': 'busiest_hour'})

print("\nTop 10 clusters — busiest enforcement hour:")
merged = cluster_stats[['rank','top_junction','risk_level','cluster']].head(10).merge(
    peak_hours[['cluster','busiest_hour']],
    on='cluster',
    how='left'
)
print(merged[['rank','top_junction','risk_level','busiest_hour']].to_string(index=False))

# ── 6. ENHANCED FOLIUM MAP ────────────────────────────────────────────────────
print("\n[6/6] Building enhanced map...")

RISK_COLORS = {
    'CRITICAL': '#FF0000',
    'HIGH':     '#FF6600',
    'MEDIUM':   '#FFAA00',
    'LOW':      '#00CC44'
}

m = folium.Map(
    location=[12.9716, 77.5946],
    zoom_start=12,
    tiles='CartoDB dark_matter'
)

# Base heatmap
sample = df[['latitude', 'longitude']].dropna().sample(min(50000, len(df)), random_state=42)
HeatMap(
    sample.values.tolist(),
    radius=10,
    blur=8,
    max_zoom=13,
    gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'orange', 1.0: 'red'}
).add_to(m)

# Cluster markers
for _, row in cluster_stats.iterrows():
    color = RISK_COLORS.get(row['risk_level'], '#FFFFFF')
    
    popup_html = f"""
    <div style='font-family:Arial; min-width:220px'>
        <h4 style='color:{color}; margin:0'>🚨 {row['risk_level']} RISK</h4>
        <hr style='margin:4px 0'>
        <b>Rank #{int(row['rank'])}</b><br>
        <b>Zone:</b> {row['top_junction']}<br>
        <b>Violations:</b> {int(row['total_violations']):,}<br>
        <b>Active Days:</b> {int(row['unique_days'])}<br>
        <b>Peak Hour:</b> {int(row['peak_hour']):02d}:00<br>
        <b>Priority Score:</b> {row['priority_score_norm']}/100<br>
        <b>Vehicle Types:</b> {int(row['unique_vehicles'])}
    </div>
    """
    
    folium.CircleMarker(
        location=[row['center_lat'], row['center_lon']],
        radius=12 if row['risk_level'] == 'CRITICAL' else 9 if row['risk_level'] == 'HIGH' else 7,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.85,
        weight=2,
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=f"#{int(row['rank'])} {row['risk_level']} — {row['top_junction']}"
    ).add_to(m)

# Legend
legend_html = """
<div style='position:fixed; bottom:30px; left:30px; z-index:1000;
     background:#1a1a2e; padding:15px; border-radius:10px;
     border:2px solid #444; font-family:Arial; color:white'>
    <b style='font-size:14px'>🚦 Enforcement Priority</b><br><br>
    <span style='color:#FF0000'>●</span> CRITICAL (score ≥ 70)<br>
    <span style='color:#FF6600'>●</span> HIGH (score 40–70)<br>
    <span style='color:#FFAA00'>●</span> MEDIUM (score 15–40)<br>
    <span style='color:#00CC44'>●</span> LOW (score &lt; 15)<br><br>
    <small>Click markers for details</small>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

m.save('data/enhanced_heatmap.html')
print("✅ Saved data/enhanced_heatmap.html")

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  DAY 2 COMPLETE — Summary")
print("="*60)
critical = cluster_stats[cluster_stats['risk_level']=='CRITICAL']
high     = cluster_stats[cluster_stats['risk_level']=='HIGH']
medium   = cluster_stats[cluster_stats['risk_level']=='MEDIUM']
low      = cluster_stats[cluster_stats['risk_level']=='LOW']

print(f"  CRITICAL zones : {len(critical)}")
print(f"  HIGH zones     : {len(high)}")
print(f"  MEDIUM zones   : {len(medium)}")
print(f"  LOW zones      : {len(low)}")
print(f"  Total clusters : {n_clusters}")
print(f"\nFiles saved:")
print(f"  data/clusters.csv           → cluster metadata for Flask API")
print(f"  data/violation_clusters.csv → per-violation cluster labels")
print(f"  data/enhanced_heatmap.html  → interactive map with risk markers")
print("="*60)
