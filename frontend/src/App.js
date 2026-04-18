import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './App.css';

const API = 'http://127.0.0.1:5000';

function App() {
  const [cotData, setCotData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cotRes, sumRes] = await Promise.all([
        fetch(`${API}/api/cot`),
        fetch(`${API}/api/summary`)
      ]);
      const cot = await cotRes.json();
      const sum = await sumRes.json();
      setCotData(cot);
      setSummary(sum);
      setError(null);
    } catch (e) {
      setError('Impossible de se connecter à l\'API. Vérifie que server.py tourne.');
    }
    setLoading(false);
  };

  const getSymbols = () => {
    if (!cotData?.data) return [];
    const items = Object.values(cotData.data);
    if (activeCategory === 'all') return items;
    return items.filter(i => i.category === activeCategory);
  };

  const getScoreColor = (score) => {
    if (score > 50) return '#22c55e';
    if (score > 25) return '#4ade80';
    if (score > 0) return '#86efac';
    if (score > -25) return '#fca5a5';
    if (score > -50) return '#f87171';
    return '#ef4444';
  };

  const getBiasTag = (bias) => {
    const styles = {
      BULLISH: { bg: '#052e16', color: '#4ade80', border: '#166534' },
      BEARISH: { bg: '#2a0a0a', color: '#f87171', border: '#7f1d1d' },
      NEUTRAL: { bg: '#1a1a2e', color: '#a5b4fc', border: '#312e81' },
    };
    const s = styles[bias] || styles.NEUTRAL;
    return (
      <span style={{
        background: s.bg, color: s.color, border: `1px solid ${s.border}`,
        padding: '2px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 600,
        letterSpacing: '0.5px'
      }}>
        {bias}
      </span>
    );
  };

  const categories = [
    { key: 'all', label: 'Tous', icon: '◉' },
    { key: 'forex', label: 'Forex', icon: '💱' },
    { key: 'index', label: 'Indices', icon: '📊' },
    { key: 'crypto', label: 'Crypto', icon: '₿' },
    { key: 'commodity', label: 'Commodités', icon: '🛢' },
  ];

  if (loading) {
    return (
      <div className="app">
        <div className="loading">
          <div className="spinner"></div>
          <p>Chargement des données...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app">
        <div className="error-box">
          <h2>Erreur de connexion</h2>
          <p>{error}</p>
          <button onClick={fetchData} className="btn">Réessayer</button>
        </div>
      </div>
    );
  }

  const symbols = getSymbols();
  const chartData = symbols
    .sort((a, b) => b.sentiment_score - a.sentiment_score)
    .map(s => ({ name: s.symbol, score: s.sentiment_score, bias: s.bias }));

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1 className="logo">QUANTDASH</h1>
          <span className="version">v1.0</span>
        </div>
        <div className="header-right">
          <span className="signal-count">{summary?.signals_count || 0} signaux</span>
          <span className="last-update">
            MAJ: {cotData?.last_updated?.split('T')[0] || '—'}
          </span>
          <button onClick={fetchData} className="btn-refresh" title="Rafraîchir">⟳</button>
        </div>
      </header>

      {/* Summary Cards */}
      <div className="summary-row">
        <div className="card summary-card bullish-card">
          <div className="card-label">Top Bullish</div>
          {summary?.top_bullish?.slice(0, 3).map((s, i) => (
            <div key={i} className="summary-item">
              <span className="summary-symbol">{s.symbol}</span>
              <span className="summary-score bullish">+{s.score}</span>
            </div>
          ))}
        </div>
        <div className="card summary-card bearish-card">
          <div className="card-label">Top Bearish</div>
          {summary?.top_bearish?.slice(0, 3).map((s, i) => (
            <div key={i} className="summary-item">
              <span className="summary-symbol">{s.symbol}</span>
              <span className="summary-score bearish">{s.score}</span>
            </div>
          ))}
        </div>
        <div className="card summary-card stats-card">
          <div className="card-label">Vue d'ensemble</div>
          <div className="stats-grid">
            <div className="stat">
              <span className="stat-value bullish">
                {Object.values(cotData?.data || {}).filter(d => d.bias === 'BULLISH').length}
              </span>
              <span className="stat-label">Bullish</span>
            </div>
            <div className="stat">
              <span className="stat-value neutral">
                {Object.values(cotData?.data || {}).filter(d => d.bias === 'NEUTRAL').length}
              </span>
              <span className="stat-label">Neutral</span>
            </div>
            <div className="stat">
              <span className="stat-value bearish">
                {Object.values(cotData?.data || {}).filter(d => d.bias === 'BEARISH').length}
              </span>
              <span className="stat-label">Bearish</span>
            </div>
          </div>
        </div>
      </div>

      {/* Score Chart */}
      <div className="card chart-card">
        <div className="card-header">
          <h2>Sentiment Score — COT Positioning</h2>
          <div className="category-tabs">
            {categories.map(c => (
              <button
                key={c.key}
                className={`tab ${activeCategory === c.key ? 'active' : ''}`}
                onClick={() => setActiveCategory(c.key)}
              >
                <span className="tab-icon">{c.icon}</span> {c.label}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 60, left: 20 }}>
            <XAxis
              dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }}
              angle={-45} textAnchor="end" interval={0}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              domain={[-100, 100]}
              ticks={[-100, -50, 0, 50, 100]}
            />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }}
              formatter={(value) => [`${value}`, 'Score']}
            />
            <Bar dataKey="score" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={getScoreColor(entry.score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Symbol Table */}
      <div className="card table-card">
        <div className="card-header">
          <h2>COT Scanner — Positionnement Institutionnel</h2>
        </div>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbole</th>
                <th>Catégorie</th>
                <th>Score</th>
                <th>Biais</th>
                <th>SM Net</th>
                <th>SM Δ</th>
                <th>Open Interest</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {symbols.sort((a, b) => b.sentiment_score - a.sentiment_score).map((s, i) => (
                <tr
                  key={i}
                  className={`table-row ${selectedSymbol === s.symbol ? 'selected' : ''}`}
                  onClick={() => setSelectedSymbol(selectedSymbol === s.symbol ? null : s.symbol)}
                >
                  <td className="symbol-cell">{s.symbol}</td>
                  <td><span className={`cat-badge ${s.category}`}>{s.category}</span></td>
                  <td>
                    <div className="score-bar-wrapper">
                      <div
                        className="score-bar"
                        style={{
                          width: `${Math.abs(s.sentiment_score) / 2}%`,
                          background: getScoreColor(s.sentiment_score),
                          marginLeft: s.sentiment_score < 0 ? `${50 - Math.abs(s.sentiment_score) / 2}%` : '50%',
                        }}
                      ></div>
                      <span className="score-value">{s.sentiment_score > 0 ? '+' : ''}{s.sentiment_score}</span>
                    </div>
                  </td>
                  <td>{getBiasTag(s.bias)}</td>
                  <td className={s.smart_money_net >= 0 ? 'positive' : 'negative'}>
                    {s.smart_money_net?.toLocaleString()}
                  </td>
                  <td className={s.smart_money_change >= 0 ? 'positive' : 'negative'}>
                    {s.smart_money_change >= 0 ? '+' : ''}{s.smart_money_change?.toLocaleString()}
                  </td>
                  <td className="muted">{s.open_interest?.toLocaleString()}</td>
                  <td className="muted">{s.latest_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Panel */}
      {selectedSymbol && cotData?.data?.[selectedSymbol] && (
        <div className="card detail-card">
          <div className="card-header">
            <h2>{selectedSymbol} — Détail COT</h2>
            <button className="btn-close" onClick={() => setSelectedSymbol(null)}>✕</button>
          </div>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Smart Money Long</span>
              <span className="detail-value positive">
                {cotData.data[selectedSymbol].smart_money_long?.toLocaleString()}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Smart Money Short</span>
              <span className="detail-value negative">
                {cotData.data[selectedSymbol].smart_money_short?.toLocaleString()}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Net Position</span>
              <span className={`detail-value ${cotData.data[selectedSymbol].smart_money_net >= 0 ? 'positive' : 'negative'}`}>
                {cotData.data[selectedSymbol].smart_money_net?.toLocaleString()}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Commercial Net</span>
              <span className="detail-value">
                {cotData.data[selectedSymbol].commercial_net?.toLocaleString()}
              </span>
            </div>
          </div>
          <h3 style={{ color: '#94a3b8', margin: '20px 0 10px', fontSize: '13px', fontWeight: 500 }}>
            Historique Smart Money Net (8 semaines)
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={
              cotData.data[selectedSymbol].history?.map(h => ({
                date: h.date?.slice(5, 10),
                net: h.smart_money?.net || h.asset_managers?.net || h.managed_money?.net || 0
              })).reverse()
            }>
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: '#e2e8f0' }}
              />
              <Bar dataKey="net" radius={[3, 3, 0, 0]}>
                {cotData.data[selectedSymbol].history?.map((h, i) => {
                  const net = h.smart_money?.net || 0;
                  return <Cell key={i} fill={net >= 0 ? '#4ade80' : '#f87171'} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p>QuantDash — Built for traders, by traders | Data: CFTC COT Reports</p>
      </footer>
    </div>
  );
}

export default App;
