import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import './App.css';

const API = 'https://gridlock-backend-d08s.onrender.com';
const RISK_COLORS = { CRITICAL: '#FF3B3B', HIGH: '#FF8C00', MEDIUM: '#FFD700', LOW: '#00C851' };
const PIE_COLORS = ['#FF3B3B','#FF8C00','#FFD700','#00C851','#4f8ef7','#9b59b6','#1abc9c','#e74c3c','#3498db','#f39c12'];

function VehicleLegend({ data }) {
  const total = data.reduce((s, d) => s + (d.count || 0), 0) || 1;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {data.map((d, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 14, height: 14, background: PIE_COLORS[i % PIE_COLORS.length], display: 'inline-block', borderRadius: 3 }} />
          <div style={{ color: '#ddd', fontSize: 13 }}>
            <div style={{ fontWeight: 600 }}>{d.vehicle_type}</div>
            <div style={{ color: '#9aa', fontSize: 12 }}>{Math.round((d.count || 0) * 100 / total)}% • {d.count?.toLocaleString()}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function StatCard({ label, value, sub, color }) {
  return (
    <div className="stat-card" style={{ borderTop: `3px solid ${color || '#4f8ef7'}` }}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function RiskBadge({ level }) {
  return (
    <span className="risk-badge" style={{ background: RISK_COLORS[level] + '22', color: RISK_COLORS[level], border: `1px solid ${RISK_COLORS[level]}` }}>
      {level}
    </span>
  );
}

export default function App() {
  const [stats, setStats]       = useState(null);
  const [clusters, setClusters] = useState([]);
  const [hourly, setHourly]     = useState([]);
  const [daily, setDaily]       = useState([]);
  const [types, setTypes]       = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/stats`).then(r => r.json()),
      fetch(`${API}/api/clusters`).then(r => r.json()),
      fetch(`${API}/api/violations/hourly`).then(r => r.json()),
      fetch(`${API}/api/violations/daily`).then(r => r.json()),
      fetch(`${API}/api/violations/types`).then(r => r.json()),
      fetch(`${API}/api/violations/vehicles`).then(r => r.json()),
      fetch(`${API}/api/hotspots?limit=15&score=recency`).then(r => r.json()),
    ]).then(([s, c, h, d, t, v, hs]) => {
      setStats(s); setClusters(c); setHourly(h);
      setDaily(d); setTypes(t); setVehicles(v); setHotspots(hs);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Use a safe maximum for recency scores to avoid division by 0/undefined
  const maxRecency = Math.max(...hotspots.map(h => h.priority_score_recency || 0), 1);

  if (loading) return (
    <div className="loading">
      <div className="spinner" />
      <p>Loading Bengaluru traffic data...</p>
    </div>
  );

  const shortJunction = (name) => name.replace(/^BTP\d+\s*-\s*/i, '').slice(0, 28);

  return (
    <div className="app">
      {/* HEADER */}
      <header className="header">
        <div className="header-left">
          <div className="header-logo">🚦</div>
          <div>
            <h1>ParkSense Intelligence</h1>
            <p>Bengaluru Parking Enforcement · Gridlock Hackathon 2.0</p>
          </div>
        </div>
        <div className="header-right">
          <span className="live-dot" />
          <span className="live-text">LIVE DATA</span>
          {stats && <span className="date-range">{stats.date_range.from} → {stats.date_range.to}</span>}
        </div>
      </header>

      {/* NAV TABS */}
      <nav className="tabs">
        {['overview', 'clusters', 'patterns', 'enforcement'].map(tab => (
          <button key={tab} className={`tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </nav>

      <main className="main">

        {/* ── OVERVIEW TAB ── */}
        {activeTab === 'overview' && (
          <>
            {/* KPI Cards */}
            <div className="stats-grid">
              <StatCard label="Total Violations" value={stats?.total_violations?.toLocaleString()} color="#FF3B3B" />
              <StatCard label="Junctions Monitored" value={stats?.junctions_monitored} color="#4f8ef7" />
              <StatCard label="Police Stations" value={stats?.police_stations} color="#00C851" />
              <StatCard label="Critical Zones" value={stats?.critical_zones} color="#FF3B3B" sub="Immediate action needed" />
              <StatCard label="High Risk Zones" value={stats?.high_risk_zones} color="#FF8C00" />
              <StatCard label="Clusters Detected" value={stats?.total_clusters} color="#9b59b6" sub="DBSCAN hotspot groups" />
            </div>

            {/* Top hotspot banner */}
            <div className="banner">
              <span className="banner-icon">📍</span>
              <span><b>Top Enforcement Priority:</b> {stats?.top_hotspot}</span>
            </div>

            {/* Charts row */}
            <div className="charts-row">
              <div className="chart-card">
                <h3>Top Violation Types</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={types} layout="vertical" margin={{ left: 20 }}>
                    <XAxis type="number" tick={{ fill: '#aaa', fontSize: 11 }} />
                    <YAxis type="category" dataKey="violation_type" tick={{ fill: '#ccc', fontSize: 10 }} width={160}
                      tickFormatter={v => v.slice(0, 22)} />
                    <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #333' }} />
                    <Bar dataKey="count" fill="#FF3B3B" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-card">
                <h3>Vehicle Types in Violations</h3>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{ flex: '0 0 65%' }}>
                    <ResponsiveContainer width="100%" height={250}>
                      <PieChart>
                        <Pie data={vehicles} dataKey="count" nameKey="vehicle_type" cx="50%" cy="50%" outerRadius={90} labelLine={false}>
                          {vehicles.map((_, i) => (
                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #333' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ flex: '0 0 35%', paddingLeft: 20 }}>
                    <VehicleLegend data={vehicles} />
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── CLUSTERS TAB ── */}
        {activeTab === 'clusters' && (
          <>
            <div className="section-title">
              <h2>DBSCAN Hotspot Clusters</h2>
              <p>Machine learning–identified violation zones ranked by enforcement priority score</p>
            </div>
            <div className="cluster-grid">
              {clusters.map(c => (
                <div key={c.cluster_id} className="cluster-card" style={{ borderLeft: `4px solid ${RISK_COLORS[c.risk_level]}` }}>
                  <div className="cluster-header">
                    <span className="cluster-rank">#{c.rank}</span>
                    <RiskBadge level={c.risk_level} />
                    <span className="cluster-score">{c.priority_score}/100</span>
                  </div>
                  <div className="cluster-name">{shortJunction(c.top_junction)}</div>
                  <div className="cluster-stats">
                    <div><span>Violations</span><b>{c.total_violations?.toLocaleString()}</b></div>
                    <div><span>Active Days</span><b>{c.unique_days}</b></div>
                    <div><span>Peak Hour</span><b>{String(c.peak_hour).padStart(2,'0')}:00</b></div>
                    <div><span>Vehicle Types</span><b>{c.unique_vehicles}</b></div>
                  </div>
                  <div className="cluster-coords">
                    📍 {c.center_lat?.toFixed(4)}, {c.center_lon?.toFixed(4)}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ── PATTERNS TAB ── */}
        {activeTab === 'patterns' && (
          <>
            <div className="section-title">
              <h2>Temporal Violation Patterns</h2>
              <p>When and where violations peak — critical for optimal officer deployment</p>
            </div>
            <div className="charts-col">
              <div className="chart-card wide">
                <h3>Violations by Hour of Day</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={hourly}>
                    <XAxis dataKey="hour" tickFormatter={h => `${String(h).padStart(2,'0')}:00`} tick={{ fill: '#aaa', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#aaa', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #333' }}
                      labelFormatter={h => `${String(h).padStart(2,'0')}:00`} />
                    <Bar dataKey="count" fill="#4f8ef7" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-card wide">
                <h3>Violations by Day of Week</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={daily}>
                    <XAxis dataKey="day" tickFormatter={d => d?.slice(0,3)} tick={{ fill: '#aaa', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#aaa', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #333' }} />
                    <Bar dataKey="count" fill="#00C851" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}

        {/* ── ENFORCEMENT TAB ── */}
        {activeTab === 'enforcement' && (
          <>
            <div className="section-title">
              <h2>Enforcement Priority Zones</h2>
              <p>Top junctions ranked by violation frequency and persistence — deploy officers here first</p>
            </div>
            <div className="table-card">
              <table className="enforcement-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Junction</th>
                    <th>Police Station Area</th>
                    <th>Violations</th>
                    <th>Active Days</th>
                    <th>Priority Score</th>
                  </tr>
                </thead>
                <tbody>
                  {hotspots.map((h, i) => (
                    <tr key={i}>
                      <td><span className="rank-num">{i + 1}</span></td>
                      <td className="junction-cell">{h.junction_name}</td>
                      <td>{h.junction_name.match(/^BTP\d+/)?.[0] || '—'}</td>
                      <td><b style={{ color: '#FF3B3B' }}>{h.total_violations?.toLocaleString()}</b>
                        {h.recent_violations ? <div className="muted">{h.recent_violations} recent</div> : null}
                      </td>
                      <td>{h.unique_days} / 152</td>
                      <td>
                        <div className="score-bar-wrap">
                          <div
                            className="score-bar"
                            style={{ width: `${Math.min(100, (h.priority_score_recency / maxRecency) * 100)}%` }}
                          />
                          <span>{h.priority_score_recency ? h.priority_score_recency.toFixed(0) : (h.priority_score ? h.priority_score.toFixed(0) : '—')}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

      </main>

      <footer className="footer">
        ParkSense · Gridlock Hackathon 2.0 · Flipkart × Bengaluru Traffic Police · Built by Amulya Singabhattu
      </footer>
    </div>
  );
}