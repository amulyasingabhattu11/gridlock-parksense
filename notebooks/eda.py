import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium.plugins import HeatMap
import ast
import warnings

warnings.filterwarnings('ignore')

# ── 1. LOAD DATA ──────────────────────────────────────────────────────────────
print("Loading dataset...")
df = pd.read_csv('data/violations.csv')
print(f"✅ Loaded {len(df):,} records, {df.shape[1]} columns\n")

# ── 2. BASIC OVERVIEW ─────────────────────────────────────────────────────────
print("=== BASIC INFO ===")
print(
    df[
        [
            'latitude',
            'longitude',
            'violation_type',
            'vehicle_type',
            'created_datetime',
            'junction_name',
            'police_station',
        ]
    ].info()
)

# ── 3. PARSE VIOLATION TYPES ──────────────────────────────────────────────────
def parse_violations(v):
    try:
        return ast.literal_eval(v)
    except:
        return []

df['violations_list'] = df['violation_type'].apply(parse_violations)

# Explode into individual violations
df_exp = df.explode('violations_list').rename(
    columns={'violations_list': 'violation'}
)

df_exp['violation'] = df_exp['violation'].astype(str).str.strip()

print("\n=== TOP 15 VIOLATION TYPES ===")
top_violations = df_exp['violation'].value_counts().head(15)
print(top_violations.to_string())

# ── 4. TIME ANALYSIS ──────────────────────────────────────────────────────────
print("\nConverting datetime column...")

df['created_datetime'] = pd.to_datetime(
    df['created_datetime'],
    format='ISO8601',
    utc=True,
    errors='coerce'
)

invalid_dates = df['created_datetime'].isna().sum()
print(f"Invalid datetime values: {invalid_dates}")

# Remove rows with invalid datetimes if any
df = df.dropna(subset=['created_datetime'])

df['hour'] = df['created_datetime'].dt.hour
df['day_of_week'] = df['created_datetime'].dt.day_name()
df['month'] = df['created_datetime'].dt.month_name()

print("\n=== VIOLATIONS BY HOUR ===")
print(df['hour'].value_counts().sort_index().to_string())

# ── 5. HOTSPOT ANALYSIS ───────────────────────────────────────────────────────
print("\n=== TOP 20 HOTSPOT JUNCTIONS ===")
junction_counts = df['junction_name'].value_counts().head(20)
print(junction_counts.to_string())

print("\n=== TOP 15 POLICE STATIONS (most violations) ===")
ps_counts = df['police_station'].value_counts().head(15)
print(ps_counts.to_string())

print("\n=== TOP 15 VEHICLE TYPES ===")
print(df['vehicle_type'].value_counts().head(15).to_string())

# ── 6. ENFORCEMENT PRIORITY SCORE ─────────────────────────────────────────────
df['date_only'] = df['created_datetime'].dt.date

junction_stats = (
    df.groupby('junction_name')
    .agg(
        total_violations=('id', 'count'),
        unique_days=('date_only', 'nunique'),
        avg_lat=('latitude', 'mean'),
        avg_lon=('longitude', 'mean'),
    )
    .reset_index()
)

junction_stats['priority_score'] = (
    junction_stats['total_violations'] * 0.7
    + junction_stats['unique_days'] * 0.3
)

junction_stats = junction_stats.sort_values(
    'priority_score',
    ascending=False
)

print("\n=== TOP 20 ENFORCEMENT PRIORITY ZONES ===")
print(
    junction_stats.head(20)[
        [
            'junction_name',
            'total_violations',
            'unique_days',
            'priority_score',
        ]
    ].to_string(index=False)
)

# Save for backend use
junction_stats.to_csv('data/hotspots.csv', index=False)
print("\n✅ Saved hotspots.csv")

# ── 7. PLOTS ──────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle(
    'Bengaluru Parking Violations - EDA',
    fontsize=16,
    fontweight='bold'
)

# Plot 1: Top violations
top_violations.head(10).plot(
    kind='barh',
    ax=axes[0, 0],
    color='#e74c3c'
)
axes[0, 0].set_title('Top 10 Violation Types')
axes[0, 0].set_xlabel('Count')

# Plot 2: Violations by hour
df['hour'].value_counts().sort_index().plot(
    kind='bar',
    ax=axes[0, 1],
    color='#3498db'
)
axes[0, 1].set_title('Violations by Hour of Day')
axes[0, 1].set_xlabel('Hour')

# Plot 3: Violations by day of week
day_order = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
]

df['day_of_week'].value_counts().reindex(day_order).plot(
    kind='bar',
    ax=axes[1, 0],
    color='#2ecc71'
)

axes[1, 0].set_title('Violations by Day of Week')
axes[1, 0].set_xlabel('Day')
axes[1, 0].tick_params(axis='x', rotation=45)

# Plot 4: Top priority junctions
junction_stats.head(10).plot(
    x='junction_name',
    y='total_violations',
    kind='barh',
    ax=axes[1, 1],
    color='#f39c12'
)

axes[1, 1].set_title('Top 10 Enforcement Priority Junctions')
axes[1, 1].set_xlabel('Total Violations')

plt.tight_layout()
plt.savefig(
    'data/eda_plots.png',
    dpi=150,
    bbox_inches='tight'
)

print("✅ Saved eda_plots.png")
plt.show()

# ── 8. FOLIUM HEATMAP ─────────────────────────────────────────────────────────
print("\nGenerating interactive heatmap...")

sample = df[['latitude', 'longitude']].dropna().head(50000)
heat_data = sample.values.tolist()

m = folium.Map(
    location=[12.9716, 77.5946],
    zoom_start=12,
    tiles='CartoDB dark_matter'
)

HeatMap(
    heat_data,
    radius=10,
    blur=8,
    max_zoom=13,
    gradient={
        0.2: 'blue',
        0.4: 'lime',
        0.6: 'orange',
        1.0: 'red',
    },
).add_to(m)

# Add top priority markers
for _, row in junction_stats.head(20).iterrows():
    if pd.notna(row['avg_lat']) and pd.notna(row['avg_lon']):
        folium.CircleMarker(
            location=[row['avg_lat'], row['avg_lon']],
            radius=8,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.8,
            popup=folium.Popup(
                f"<b>{row['junction_name']}</b><br>"
                f"Violations: {int(row['total_violations']):,}<br>"
                f"Priority Score: {row['priority_score']:.0f}",
                max_width=200,
            ),
        ).add_to(m)

m.save('data/heatmap.html')

print("✅ Saved heatmap.html — open this in your browser!")

print("\n🎉 Day 1 EDA Complete!")
print("Files generated:")
print("  data/hotspots.csv   → enforcement priority zones")
print("  data/eda_plots.png  → analysis charts")
print("  data/heatmap.html   → interactive Bengaluru map")