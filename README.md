# 🚦 ParkSense — AI-Driven Parking Enforcement Intelligence

> **Gridlock Hackathon 2.0** · Flipkart × Bengaluru Traffic Police × HackerEarth  
> **Theme:** Poor Visibility on Parking-Induced Congestion  
> **Built by:** Amulya Singabhattu · BVRIT Hyderabad College of Engineering for Women

---

## 🔴 Live Demo

| | Link |
|---|---|
| 🖥️ Frontend Dashboard | [gridlock-parksense.vercel.app](https://gridlock-parksense.vercel.app) |
| ⚙️ Backend API | [gridlock-backend-d08s.onrender.com](https://gridlock-backend-d08s.onrender.com) |
| 💻 GitHub Repo | [github.com/amulyasingabhattu11/gridlock-parksense](https://github.com/amulyasingabhattu11/gridlock-parksense) |

> ⚠️ The backend runs on a free Render instance. First request may take 30–50 seconds to wake up. Refresh once and all data loads instantly.

---

## 🧠 Problem Statement

Bengaluru's roads are choked by illegal and wrong parking near commercial areas, metro stations, and busy junctions. Enforcement today is **patrol-based and reactive** — with no data-driven system to tell officers:
- Where violations cluster most
- Which junctions need priority attention
- What time of day enforcement is most effective

---

## 💡 Solution

**ParkSense** analyzes 298,450 real violation records from Bengaluru Traffic Police (Jan–May 2024) to deliver:

- 🗺️ **Interactive violation heatmap** of Bengaluru
- 🤖 **DBSCAN clustering** to identify dense hotspot zones
- 📊 **Enforcement priority scoring** (CRITICAL / HIGH / MEDIUM / LOW)
- ⏰ **Temporal pattern analysis** — peak hours and busiest days
- 🚓 **Live enforcement recommendations** based on current hour

---

## 📊 Key Findings

| Metric | Value |
|---|---|
| Total violations analyzed | 298,450 |
| Wrong Parking + No Parking | 93% of all violations |
| Junctions monitored | 168 |
| Police station areas | 30 |
| DBSCAN clusters found | 8 |
| Top hotspot | BTP051 — Safina Plaza Junction (15,449 violations) |
| Peak enforcement window | 03:00–05:00 & 19:00–23:00 |
| Data period | Nov 2023 – Apr 2024 |

---

## 🏗️ Architecture

```
data/
├── violations_sample.csv     ← 5,000 sampled records (for deployment)
├── hotspots.csv              ← 169 ranked enforcement junctions
└── clusters.csv              ← 8 DBSCAN clusters with risk scores

notebooks/
├── eda.py                    ← Exploratory data analysis + heatmap
└── clustering.py             ← DBSCAN clustering + priority scoring

backend/
├── app.py                    ← Flask REST API (9 endpoints)
└── requirements.txt          ← Python dependencies

frontend/
└── src/
    ├── App.js                ← React dashboard (4 tabs)
    └── App.css               ← Dark theme styles
```

---

## 🤖 ML Pipeline

1. **Data Cleaning** — Remove `No Junction` entries, parse datetimes
2. **DBSCAN Clustering** — `eps=0.005` (~500m radius), `min_samples=30`, `metric=haversine`
3. **Cluster Statistics** — violations, unique days, vehicle types, peak hour per cluster
4. **Priority Score** — weighted formula:
   ```
   score = violations×0.50 + unique_days×0.25 + unique_vehicles×0.15 + unique_junctions×0.10
   ```
5. **Risk Classification** — normalized to 0–100 → CRITICAL (≥70) / HIGH (40–70) / MEDIUM (15–40) / LOW (<15)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Data Analysis | Python, Pandas, NumPy |
| Machine Learning | Scikit-learn (DBSCAN), SciPy |
| Visualization | Folium, Matplotlib, Seaborn |
| Backend | Flask, Flask-CORS, Gunicorn |
| Frontend | React.js, Recharts, Leaflet |
| Backend Deploy | Render (free tier) |
| Frontend Deploy | Vercel |
| Version Control | Git, GitHub |

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the repo
```bash
git clone https://github.com/amulyasingabhattu11/gridlock-parksense.git
cd gridlock-parksense
```

### 2. Set up Python backend
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 3. Add dataset
Place `violations.csv` (from ASTraM / HackerEarth dataset) in the `data/` folder.

### 4. Run EDA + clustering (optional)
```bash
python notebooks/eda.py
python notebooks/clustering.py
```

### 5. Start Flask backend
```bash
python backend/app.py
# API running at http://localhost:5000
```

### 6. Start React frontend (new terminal)
```bash
cd frontend
npm install
npm start
# Dashboard at http://localhost:3000
```

---

## 🔌 API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Project info + endpoint list |
| `GET /api/stats` | Dashboard KPI summary |
| `GET /api/hotspots` | Top enforcement priority junctions |
| `GET /api/clusters` | DBSCAN clusters with risk levels |
| `GET /api/violations/hourly` | Violation count by hour |
| `GET /api/violations/daily` | Violation count by day of week |
| `GET /api/violations/monthly` | Violation count by month |
| `GET /api/violations/types` | Top violation types |
| `GET /api/violations/vehicles` | Top vehicle types |
| `GET /api/heatmap-points` | Sampled lat/lon points for map |
| `GET /api/enforcement/recommend` | Live enforcement recommendations |

---

## 📱 Dashboard Tabs

| Tab | What it shows |
|---|---|
| **Overview** | KPI cards, top violation types, vehicle pie chart |
| **Clusters** | 8 DBSCAN hotspot cards with risk badges and peak hours |
| **Patterns** | Hourly and daily violation bar charts |
| **Enforcement** | Priority table: top 15 junctions with score bars |

---

## 📁 Project Structure

```
gridlock-parksense/
├── data/
│   ├── clusters.csv
│   ├── hotspots.csv
│   ├── violations_sample.csv
│   ├── eda_plots.png
│   ├── heatmap.html
│   └── enhanced_heatmap.html
├── notebooks/
│   ├── eda.py
│   └── clustering.py
├── backend/
│   ├── app.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   └── src/
│       ├── App.js
│       └── App.css
└── README.md
```

---

## 👩‍💻 About the Builder

**Amulya Singabhattu**  
B.Tech CSE · BVRIT Hyderabad College of Engineering for Women (2024–2028)  


- 🔗 GitHub: [github.com/amulyasingabhattu11](https://github.com/amulyasingabhattu11)
  

---

## 📄 License

This project was built for Gridlock Hackathon 2.0. Data provided by Bengaluru Traffic Police (ASTraM unit) via HackerEarth.
