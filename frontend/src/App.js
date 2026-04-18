import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './App.css';

const API = 'https://quandash.onrender.com';
const REFRESH_MS = 30000; // Auto-refresh every 30s

function App() {
  const [composite, setComposite] = useState(null);
  const [cotData, setCotData] = useState(null);
  const [ecoData, setEcoData] = useState(null);
  const [sentData, setSentData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [levelsData, setLevelsData] = useState(null);
  const [levelsLoading, setLevelsLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    setRefreshing(true);
    try {
      const endpoints = ['/api/composite', '/api/cot', '/api/eco', '/api/sentiment', '/api/summary'];
      const responses = await Promise.all(endpoints.map(e => fetch(`${API}${e}`).catch(() => null)));
      const [compRes, cotRes, ecoRes, sentRes, sumRes] = responses;

      if (compRes?.ok) setComposite(await compRes.json());
      if (cotRes?.ok) setCotData(await cotRes.json());
      if (ecoRes?.ok) setEcoData(await ecoRes.json());
      if (sentRes?.ok) setSentData(await sentRes.json());
      if (sumRes?.ok) setSummary(await sumRes.json());

      setLastRefresh(new Date());
      setError(null);
    } catch (e) {
      setError('API inaccessible. Lance server.py dans le backend.');
    }
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    fetchData(true);
    const interval = setInterval(() => fetchData(false), REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Fetch key levels when a symbol is selected
  useEffect(() => {
    if (!selectedSymbol) { setLevelsData(null); return; }
    setLevelsLoading(true);
    fetch(`${API}/api/levels/${encodeURIComponent(selectedSymbol)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { setLevelsData(d); setLevelsLoading(false); })
      .catch(() => { setLevelsData(null); setLevelsLoading(false); });
  }, [selectedSymbol]);

  // Data helpers
  const getSymbols = () => {
    const source = composite?.data || cotData?.data || {};
    const items = Object.values(source);
    if (activeCategory === 'all') return items;
    return items.filter(i => i.category === activeCategory);
  };

  const getScore = (item) => item.composite_score ?? item.sentiment_score ?? 0;
  const getBias = (item) => item.composite_bias ?? item.bias ?? 'NEUTRAL';

  const scoreColor = (s) => {
    if (s > 50) return '#16a34a';
    if (s > 25) return '#22c55e';
    if (s > 0) return '#86efac';
    if (s > -25) return '#fca5a5';
    if (s > -50) return '#ef4444';
    return '#dc2626';
  };

  const biasTag = (bias) => {
    const m = {
      BULLISH: { bg: '#dcfce7', c: '#15803d', b: '#bbf7d0' },
      BEARISH: { bg: '#fee2e2', c: '#dc2626', b: '#fecaca' },
      NEUTRAL: { bg: '#f3f4f6', c: '#6b7280', b: '#e5e7eb' },
    };
    const s = m[bias] || m.NEUTRAL;
    return <span style={{ background: s.bg, color: s.c, border: `1px solid ${s.b}`, padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600 }}>{bias}</span>;
  };

  const impactDot = (imp) => {
    const c = { High: '#dc2626', Medium: '#d97706', Low: '#9ca3af' };
    return <span style={{ color: c[imp] || '#9ca3af', marginRight: 4 }}>●</span>;
  };

  const sentBadge = (s) => {
    const m = { BULLISH: { bg: '#dcfce7', c: '#15803d' }, BEARISH: { bg: '#fee2e2', c: '#dc2626' }, NEUTRAL: { bg: '#f3f4f6', c: '#6b7280' }, PENDING: { bg: '#fef3c7', c: '#d97706' } };
    const st = m[s] || m.NEUTRAL;
    return <span style={{ background: st.bg, color: st.c, padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600 }}>{s}</span>;
  };

  const cats = [
    { key: 'all', label: 'Tous', icon: '◉' },
    { key: 'forex', label: 'Forex', icon: '💱' },
    { key: 'index', label: 'Indices', icon: '📊' },
    { key: 'crypto', label: 'Crypto', icon: '₿' },
    { key: 'commodity', label: 'Commodités', icon: '🛢' },
  ];

  if (loading) return (
    <div className="app"><div className="loading"><div className="spinner" /><p>Chargement des données...</p></div></div>
  );

  if (error && !cotData) return (
    <div className="app"><div className="error-box"><h2>Erreur</h2><p>{error}</p><button onClick={() => fetchData(true)} className="btn">Réessayer</button></div></div>
  );

  const symbols = getSymbols();
  const allSymbols = Object.values(composite?.data || cotData?.data || {});
  const bullishCount = allSymbols.filter(d => getBias(d) === 'BULLISH').length;
  const neutralCount = allSymbols.filter(d => getBias(d) === 'NEUTRAL').length;
  const bearishCount = allSymbols.filter(d => getBias(d) === 'BEARISH').length;

  const chartData = [...symbols].sort((a, b) => getScore(b) - getScore(a)).map(s => ({
    name: s.symbol, score: getScore(s), bias: getBias(s),
  }));

  const highEvents = ecoData?.high_impact_events || [];
  const allEvents = ecoData?.events || [];
  const currScores = ecoData?.currency_scores || {};
  const sentSymbols = sentData?.data || {};

  return (
    <div className="app">
      {/* TOP BAR */}
      <div className="topbar">
        <div className="topbar-left">
          <h1 className="logo">QUANTDASH</h1>
          <span className="tagline">Institutional Positioning Intelligence</span>
        </div>
        <div className="topbar-right">
          <div className="refresh-info">
            <span className={`live-dot ${refreshing ? 'pulse' : ''}`}>●</span>
            <span className="last-update">Live · {lastRefresh ? lastRefresh.toLocaleTimeString('fr-FR') : '—'}</span>
          </div>
          <button onClick={() => fetchData(false)} className="btn-refresh" title="Rafraîchir">⟳</button>
          <a href="mailto:contact@quantdash.io" className="btn-access">Get Access →</a>
        </div>
      </div>

      {/* DATA SOURCES BAR */}
      <div className="sources-bar">
        <span className="sources-label">Data</span>
        {[
          { name: 'CFTC COT', desc: 'Weekly', color: '#2563eb' },
          { name: 'Myfxbook', desc: 'Live', color: '#7c3aed' },
          { name: 'Forex Factory', desc: 'Live', color: '#d97706' },
          { name: 'Twelve Data', desc: 'Live', color: '#16a34a' },
        ].map((s, i) => (
          <div key={i} className="source-chip">
            <span className="source-dot" style={{ background: s.color }} />
            <span className="source-name">{s.name}</span>
            <span className="source-desc">{s.desc}</span>
          </div>
        ))}
        <span className="signal-count" style={{ marginLeft: 'auto' }}>{allSymbols.length} instruments</span>
      </div>

      {/* NAV */}
      <header className="header">
        <div className="main-tabs">
          {[
            { key: 'overview', label: 'Overview' },
            { key: 'cot', label: 'COT Scanner' },
            { key: 'eco', label: 'Economic Calendar', badge: highEvents.length },
            { key: 'sentiment', label: 'Retail Sentiment' },
            { key: 'methodology', label: 'Methodology' },
          ].map(t => (
            <button key={t.key} className={`main-tab ${activeTab === t.key ? 'active' : ''}`} onClick={() => setActiveTab(t.key)}>
              {t.label}
              {t.badge > 0 && <span className="tab-badge">{t.badge}</span>}
            </button>
          ))}
        </div>
      </header>

      {/* SUMMARY CARDS */}
      <div className="summary-row">
        <div className="card summary-card bullish-card">
          <div className="card-label">Top Bullish</div>
          {(summary?.top_bullish || []).slice(0, 3).map((s, i) => (
            <div key={i} className="summary-item">
              <span className="summary-symbol">{s.symbol}</span>
              <span className="summary-score bullish">+{s.score}</span>
            </div>
          ))}
        </div>
        <div className="card summary-card bearish-card">
          <div className="card-label">Top Bearish</div>
          {(summary?.top_bearish || []).slice(0, 3).map((s, i) => (
            <div key={i} className="summary-item">
              <span className="summary-symbol">{s.symbol}</span>
              <span className="summary-score bearish">{s.score}</span>
            </div>
          ))}
        </div>
        <div className="card summary-card stats-card">
          <div className="card-label">Signaux</div>
          <div className="stats-grid">
            <div className="stat"><span className="stat-value bullish">{bullishCount}</span><span className="stat-label">Bullish</span></div>
            <div className="stat"><span className="stat-value neutral">{neutralCount}</span><span className="stat-label">Neutral</span></div>
            <div className="stat"><span className="stat-value bearish">{bearishCount}</span><span className="stat-label">Bearish</span></div>
          </div>
        </div>
      </div>

      {/* ===== OVERVIEW TAB ===== */}
      {activeTab === 'overview' && (
        <>
          <div className="card chart-card">
            <div className="card-header">
              <h2>Composite Score — Tous les Actifs</h2>
              <div className="category-tabs">
                {cats.map(c => (
                  <button key={c.key} className={`tab ${activeCategory === c.key ? 'active' : ''}`} onClick={() => setActiveCategory(c.key)}>
                    <span className="tab-icon">{c.icon}</span> {c.label}
                  </button>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 60, left: 20 }}>
                <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} domain={[-100, 100]} ticks={[-100, -50, 0, 50, 100]} />
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 8, color: '#111827', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} formatter={v => [`${v}`, 'Score']} />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {chartData.map((e, i) => <Cell key={i} fill={scoreColor(e.score)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card table-card">
            <div className="card-header"><h2>Tableau de Bord — Scoring Composite</h2></div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr>
                  <th>Symbole</th><th>Cat.</th><th>Score</th><th>Biais</th>
                  <th>COT</th><th>Éco</th><th>Sent.</th><th>SM Net</th><th>SM Δ</th>
                </tr></thead>
                <tbody>
                  {[...symbols].sort((a, b) => getScore(b) - getScore(a)).map((s, i) => (
                    <tr key={i} className={`table-row ${selectedSymbol === s.symbol ? 'selected' : ''}`}
                        onClick={() => setSelectedSymbol(selectedSymbol === s.symbol ? null : s.symbol)}>
                      <td className="symbol-cell">{s.symbol}</td>
                      <td><span className={`cat-badge ${s.category}`}>{s.category}</span></td>
                      <td>
                        <div className="score-bar-wrapper">
                          <div className="score-bar" style={{
                            width: `${Math.abs(getScore(s)) / 2}%`,
                            background: scoreColor(getScore(s)),
                            marginLeft: getScore(s) < 0 ? `${50 - Math.abs(getScore(s)) / 2}%` : '50%',
                          }} />
                          <span className="score-value">{getScore(s) > 0 ? '+' : ''}{getScore(s)}</span>
                        </div>
                      </td>
                      <td>{biasTag(getBias(s))}</td>
                      <td className="mono-cell">{s.cot_score ?? s.sentiment_score ?? '—'}</td>
                      <td className="mono-cell">{s.eco_score ?? '—'}</td>
                      <td className="mono-cell">{s.sentiment_score !== undefined && s.retail_long_pct ? s.sentiment_score : '—'}</td>
                      <td className={s.smart_money_net >= 0 ? 'positive' : 'negative'}>{s.smart_money_net?.toLocaleString()}</td>
                      <td className={s.smart_money_change >= 0 ? 'positive' : 'negative'}>
                        {s.smart_money_change >= 0 ? '+' : ''}{s.smart_money_change?.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ===== COT TAB ===== */}
      {activeTab === 'cot' && (
        <>
          <div className="card chart-card">
            <div className="card-header">
              <h2>COT Institutional Positioning</h2>
              <div className="category-tabs">
                {cats.map(c => (
                  <button key={c.key} className={`tab ${activeCategory === c.key ? 'active' : ''}`} onClick={() => setActiveCategory(c.key)}>
                    <span className="tab-icon">{c.icon}</span> {c.label}
                  </button>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 60, left: 20 }}>
                <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} domain={[-100, 100]} ticks={[-100, -50, 0, 50, 100]} />
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 8, color: '#111827', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} formatter={v => [`${v}`, 'Score']} />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {chartData.map((e, i) => <Cell key={i} fill={scoreColor(e.score)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card table-card">
            <div className="card-header"><h2>COT Scanner — Positionnement Institutionnel</h2></div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr>
                  <th>Symbole</th><th>Catégorie</th><th>Score</th><th>Biais</th>
                  <th>SM Net</th><th>SM Δ</th><th>OI</th><th>Date</th>
                </tr></thead>
                <tbody>
                  {[...symbols].sort((a, b) => getScore(b) - getScore(a)).map((s, i) => (
                    <tr key={i} className={`table-row ${selectedSymbol === s.symbol ? 'selected' : ''}`}
                        onClick={() => setSelectedSymbol(selectedSymbol === s.symbol ? null : s.symbol)}>
                      <td className="symbol-cell">{s.symbol}</td>
                      <td><span className={`cat-badge ${s.category}`}>{s.category}</span></td>
                      <td>
                        <div className="score-bar-wrapper">
                          <div className="score-bar" style={{
                            width: `${Math.abs(getScore(s)) / 2}%`, background: scoreColor(getScore(s)),
                            marginLeft: getScore(s) < 0 ? `${50 - Math.abs(getScore(s)) / 2}%` : '50%',
                          }} />
                          <span className="score-value">{getScore(s) > 0 ? '+' : ''}{getScore(s)}</span>
                        </div>
                      </td>
                      <td>{biasTag(getBias(s))}</td>
                      <td className={s.smart_money_net >= 0 ? 'positive' : 'negative'}>{s.smart_money_net?.toLocaleString()}</td>
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
        </>
      )}

      {/* ===== ECO TAB ===== */}
      {activeTab === 'eco' && (
        <>
          <div className="card">
            <div className="card-header">
              <h2>Scores Économiques par Devise</h2>
            </div>
            <div className="currency-scores-grid">
              {Object.entries(currScores).sort((a, b) => b[1].normalized - a[1].normalized).map(([cur, d], i) => (
                <div key={i} className="currency-score-card">
                  <div className="currency-name">{cur}</div>
                  <div className="currency-score-bar-wrap">
                    <div className="currency-score-bar" style={{
                      width: `${Math.max(3, Math.abs(d.normalized) / 2)}%`,
                      background: d.normalized >= 0 ? '#16a34a' : '#dc2626',
                      marginLeft: d.normalized < 0 ? `${50 - Math.abs(d.normalized) / 2}%` : '50%',
                    }} />
                  </div>
                  <div className={`currency-score-val ${d.normalized > 0 ? 'positive' : d.normalized < 0 ? 'negative' : 'muted'}`}>
                    {d.normalized > 0 ? '+' : ''}{d.normalized.toFixed(1)}
                  </div>
                  <div className="currency-events">{d.high_impact}🔴 / {d.events} evt</div>
                </div>
              ))}
            </div>
          </div>

          {highEvents.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2>Événements High Impact</h2>
                <span className="impact-badge">{highEvents.length} événements</span>
              </div>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Date</th><th>Heure</th><th>Devise</th><th>Impact</th><th>Événement</th><th>Actuel</th><th>Prévision</th><th>Précédent</th><th>Sentiment</th></tr></thead>
                  <tbody>
                    {highEvents.map((e, i) => (
                      <>
                        <tr key={i} className="table-row">
                          <td className="muted">{e.date}</td>
                          <td className="mono-cell">{e.time}</td>
                          <td><span className="currency-badge">{e.currency}</span></td>
                          <td>{impactDot(e.impact)}{e.impact}</td>
                          <td style={{ fontWeight: 500 }}>{e.title}</td>
                          <td className={e.actual ? 'positive' : 'muted'}>{e.actual || '—'}</td>
                          <td className="muted">{e.forecast || '—'}</td>
                          <td className="muted">{e.previous || '—'}</td>
                          <td>{sentBadge(e.sentiment)}</td>
                        </tr>
                        {e.impact_explanation && (
                          <tr key={`exp-${i}`}>
                            <td colSpan={9} className="explanation-row">
                              <span className="explanation-icon">💬</span>
                              {e.impact_explanation}
                            </td>
                          </tr>
                        )}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="card">
            <div className="card-header"><h2>Tous les Événements</h2><span className="muted" style={{ fontSize: 12 }}>{allEvents.length} événements</span></div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Date</th><th>Heure</th><th>Devise</th><th>Impact</th><th>Événement</th><th>Actuel</th><th>Prévision</th><th>Précédent</th><th>Sentiment</th></tr></thead>
                <tbody>
                  {allEvents.map((e, i) => (
                    <>
                      <tr key={i} className="table-row">
                        <td className="muted">{e.date}</td>
                        <td className="mono-cell">{e.time}</td>
                        <td><span className="currency-badge">{e.currency}</span></td>
                        <td>{impactDot(e.impact)}{e.impact}</td>
                        <td style={{ fontWeight: 500 }}>{e.title}</td>
                        <td className={e.actual ? 'positive' : 'muted'}>{e.actual || '—'}</td>
                        <td className="muted">{e.forecast || '—'}</td>
                        <td className="muted">{e.previous || '—'}</td>
                        <td>{sentBadge(e.sentiment)}</td>
                      </tr>
                      {e.impact_explanation && (
                        <tr key={`exp-${i}`}>
                          <td colSpan={9} className="explanation-row">
                            <span className="explanation-icon">💬</span>
                            {e.impact_explanation}
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ===== SENTIMENT TAB ===== */}
      {activeTab === 'sentiment' && (
        <>
          <div className="card">
            <div className="card-header">
              <h2>Sentiment Retail — Positionnement Contrarian</h2>
              <span className="muted" style={{ fontSize: 12 }}>⚠️ = Foule en extrême (signal contrarian fort)</span>
            </div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr>
                  <th>Symbole</th><th>Retail Long</th><th>Retail Short</th><th>Biais Retail</th>
                  <th>Score Contrarian</th><th>Extrême</th><th>COT Alignment</th>
                </tr></thead>
                <tbody>
                  {Object.values(sentSymbols).sort((a, b) => Math.abs(b.contrarian_score) - Math.abs(a.contrarian_score)).map((s, i) => (
                    <tr key={i} className="table-row">
                      <td className="symbol-cell">{s.symbol}</td>
                      <td>
                        <div className="retail-bar">
                          <div className="retail-long" style={{ width: `${s.retail_long_pct}%` }}>{s.retail_long_pct.toFixed(1)}%</div>
                          <div className="retail-short" style={{ width: `${s.retail_short_pct}%` }}>{s.retail_short_pct.toFixed(1)}%</div>
                        </div>
                      </td>
                      <td className="muted">{s.retail_short_pct.toFixed(1)}%</td>
                      <td>
                        <span style={{
                          background: s.retail_bias === 'LONG' ? '#dcfce7' : '#fee2e2',
                          color: s.retail_bias === 'LONG' ? '#15803d' : '#dc2626',
                          padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
                        }}>{s.retail_bias}</span>
                      </td>
                      <td className={s.contrarian_score > 0 ? 'positive' : s.contrarian_score < 0 ? 'negative' : 'muted'}>
                        <span style={{ fontFamily: 'monospace', fontWeight: 600, fontSize: 14 }}>
                          {s.contrarian_score > 0 ? '+' : ''}{s.contrarian_score}
                        </span>
                      </td>
                      <td>{s.crowd_extreme ? <span style={{ color: '#d97706' }}>⚠️ EXTREME</span> : <span className="muted">Normal</span>}</td>
                      <td>
                        <span style={{
                          color: s.cot_alignment === 'ALIGNED' ? '#16a34a' : s.cot_alignment === 'DIVERGENT' ? '#dc2626' : '#9ca3af',
                          fontWeight: 500,
                        }}>{s.cot_alignment}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><h2>Indicateur Smart vs Dumb Money</h2></div>
            <div className="smart-dumb-grid">
              {Object.values(sentSymbols).filter(s => s.crowd_extreme).map((s, i) => (
                <div key={i} className="smart-dumb-card">
                  <div className="sd-symbol">{s.symbol}</div>
                  <div className="sd-desc">
                    Retail {s.retail_bias === 'LONG' ? 'massivement long' : 'massivement short'} à {Math.max(s.retail_long_pct, s.retail_short_pct).toFixed(1)}%
                  </div>
                  <div className={`sd-signal ${s.contrarian_score > 0 ? 'positive' : 'negative'}`}>
                    Signal: {s.contrarian_score > 0 ? 'ACHETER' : 'VENDRE'} (contrarian)
                  </div>
                </div>
              ))}
              {Object.values(sentSymbols).filter(s => s.crowd_extreme).length === 0 && (
                <p className="muted" style={{ padding: 20 }}>Aucun signal contrarian extrême pour le moment.</p>
              )}
            </div>
          </div>
        </>
      )}

      {/* ===== METHODOLOGY TAB ===== */}
      {activeTab === 'methodology' && (
        <div className="methodology-page">
          <div className="method-hero">
            <h2 className="method-hero-title">How QuantDash Works</h2>
            <p className="method-hero-sub">A transparent, rules-based system combining institutional positioning, macroeconomic data, and retail sentiment into a single actionable score.</p>
          </div>

          <div className="method-score-card">
            <div className="method-score-title">Composite Score Formula</div>
            <div className="method-pillars">
              <div className="method-pillar pillar-cot">
                <div className="pillar-pct">50%</div>
                <div className="pillar-name">COT Positioning</div>
                <div className="pillar-desc">CFTC Commitment of Traders — tracks what institutions (Non-Commercials / Smart Money) are doing vs commercial hedgers. Published every Friday.</div>
                <div className="pillar-source">Source: CFTC.gov</div>
              </div>
              <div className="method-pillar pillar-eco">
                <div className="pillar-pct">25%</div>
                <div className="pillar-name">Economic Calendar</div>
                <div className="pillar-desc">Macro events scored by impact and surprise factor. High-impact surprises (NFP, CPI, rate decisions) shift currency bias significantly.</div>
                <div className="pillar-source">Source: Forex Factory</div>
              </div>
              <div className="method-pillar pillar-sent">
                <div className="pillar-pct">25%</div>
                <div className="pillar-name">Retail Sentiment (Contrarian)</div>
                <div className="pillar-desc">When retail traders are crowded on one side (&gt;65%), the contrarian signal fires. Crowd extremes historically precede reversals.</div>
                <div className="pillar-source">Source: Myfxbook</div>
              </div>
            </div>
          </div>

          <div className="method-grid">
            <div className="method-block">
              <div className="method-block-title">Score Interpretation</div>
              <div className="method-score-legend">
                {[
                  { range: '+75 → +100', label: 'Strong Bullish', color: '#15803d', bg: '#dcfce7' },
                  { range: '+25 → +75', label: 'Bullish', color: '#16a34a', bg: '#f0fdf4' },
                  { range: '-25 → +25', label: 'Neutral', color: '#6b7280', bg: '#f3f4f6' },
                  { range: '-75 → -25', label: 'Bearish', color: '#dc2626', bg: '#fff1f1' },
                  { range: '-100 → -75', label: 'Strong Bearish', color: '#b91c1c', bg: '#fee2e2' },
                ].map((s, i) => (
                  <div key={i} className="legend-row" style={{ background: s.bg }}>
                    <span className="legend-range" style={{ color: s.color, fontFamily: 'DM Mono, monospace' }}>{s.range}</span>
                    <span className="legend-label" style={{ color: s.color, fontWeight: 600 }}>{s.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="method-block">
              <div className="method-block-title">Coverage — 20 Instruments</div>
              <div className="method-instruments">
                {[
                  { cat: 'Forex', color: '#4f46e5', bg: '#eef2ff', items: 'EUR/USD · GBP/USD · USD/JPY · USD/CHF · USD/CAD · AUD/USD · NZD/USD' },
                  { cat: 'Indices', color: '#2563eb', bg: '#dbeafe', items: 'S&P 500 · Nasdaq 100 · Dow Jones' },
                  { cat: 'Crypto', color: '#d97706', bg: '#fef3c7', items: 'Bitcoin · Ethereum' },
                  { cat: 'Commodities', color: '#16a34a', bg: '#dcfce7', items: 'Gold · Silver · Crude Oil · Natural Gas · Copper · Corn · Wheat · Soybeans' },
                ].map((g, i) => (
                  <div key={i} className="method-instrument-group">
                    <span className="cat-badge" style={{ background: g.bg, color: g.color, marginRight: 8 }}>{g.cat}</span>
                    <span className="method-instrument-list">{g.items}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="method-block">
              <div className="method-block-title">Data Refresh Cadence</div>
              <div className="method-cadence">
                {[
                  { source: 'COT Data', freq: 'Weekly — every Friday 3:30pm ET', color: '#2563eb' },
                  { source: 'Economic Calendar', freq: 'Every 5 minutes', color: '#d97706' },
                  { source: 'Retail Sentiment', freq: 'Every 5 minutes', color: '#7c3aed' },
                  { source: 'Key Levels & Prices', freq: 'Every 60 minutes', color: '#16a34a' },
                  { source: 'Composite Score', freq: 'On every data update', color: '#6b7280' },
                ].map((c, i) => (
                  <div key={i} className="cadence-row">
                    <span className="source-dot" style={{ background: c.color }} />
                    <span className="cadence-source">{c.source}</span>
                    <span className="cadence-freq">{c.freq}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="method-disclaimer">
            <strong>Risk Disclosure</strong> — QuantDash provides analytical data for informational purposes only. It does not constitute financial advice or a solicitation to buy or sell any financial instrument. Trading involves substantial risk of loss. Past signal performance does not guarantee future results. Always conduct your own analysis before making trading decisions.
          </div>
        </div>
      )}

      {/* DETAIL PANEL */}
      {selectedSymbol && (composite?.data?.[selectedSymbol] || cotData?.data?.[selectedSymbol]) && (() => {
        const d = composite?.data?.[selectedSymbol] || cotData?.data?.[selectedSymbol];
        const lv = levelsData;
        const fmt = (v, sym) => {
          if (v == null) return '—';
          const n = typeof v === 'number' ? v : parseFloat(v);
          if (isNaN(n)) return '—';
          if (['EUR/USD','GBP/USD','USD/CHF','AUD/USD','NZD/USD','USD/CAD'].includes(sym)) return n.toFixed(5);
          if (sym === 'USD/JPY') return n.toFixed(3);
          if (['Gold','Silver','S&P 500','Nasdaq 100','Dow Jones'].includes(sym)) return n.toFixed(2);
          if (['Bitcoin','Ethereum'].includes(sym)) return n.toFixed(0);
          return n.toFixed(4);
        };
        return (
          <div className="card detail-card">
            <div className="card-header">
              <h2>{selectedSymbol} — Détail Complet</h2>
              <button className="btn-close" onClick={() => setSelectedSymbol(null)}>✕</button>
            </div>

            {/* COT Metrics */}
            <div className="detail-grid">
              {[
                ['Score Composite', getScore(d), getScore(d) >= 0 ? 'positive' : 'negative'],
                ['SM Long', d.smart_money_long, 'positive'],
                ['SM Short', d.smart_money_short, 'negative'],
                ['Net Position', d.smart_money_net, d.smart_money_net >= 0 ? 'positive' : 'negative'],
                ['Commercial Net', d.commercial_net, ''],
                ['Open Interest', d.open_interest, 'muted'],
                ['Retail Long', d.retail_long_pct ? `${d.retail_long_pct}%` : '—', ''],
                ['Crowd Extreme', d.crowd_extreme ? 'OUI ⚠️' : 'Non', d.crowd_extreme ? 'negative' : ''],
              ].map(([label, val, cls], i) => (
                <div key={i} className="detail-item">
                  <span className="detail-label">{label}</span>
                  <span className={`detail-value ${cls}`}>{typeof val === 'number' ? val.toLocaleString() : val}</span>
                </div>
              ))}
            </div>

            {/* COT History Chart */}
            <h3 style={{ color: '#6b7280', margin: '20px 0 10px', fontSize: 13 }}>Historique Net — 8 semaines</h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={d.history?.map(h => ({ date: h.date?.slice(5, 10), net: h.smart_money?.net || 0 })).reverse()}>
                <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: 8, color: '#111827', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} />
                <Bar dataKey="net" radius={[3, 3, 0, 0]}>
                  {d.history?.map((h, i) => <Cell key={i} fill={(h.smart_money?.net || 0) >= 0 ? '#16a34a' : '#dc2626'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            {/* ===== KEY LEVELS SECTION ===== */}
            <div className="levels-section">
              <div className="section-title">Key Levels — Niveaux Clés</div>

              {levelsLoading && <p className="muted" style={{ padding: 10 }}>Chargement des niveaux...</p>}

              {!levelsLoading && lv && (
                <>
                  {/* Price + ATR + Range */}
                  <div className="levels-grid">
                    <div className="level-card price-card">
                      <span className="level-label">Prix Actuel</span>
                      <span className="level-value" style={{ color: 'var(--blue)' }}>{fmt(lv.current_price, selectedSymbol)}</span>
                    </div>
                    <div className="level-card">
                      <span className="level-label">ATR (14)</span>
                      <span className="level-value">{fmt(lv.atr_14, selectedSymbol)}</span>
                    </div>
                    <div className="level-card">
                      <span className="level-label">Source</span>
                      <span className="level-value" style={{ fontSize: 12, color: lv.data_source === 'twelvedata' ? 'var(--green)' : 'var(--amber)' }}>
                        {lv.data_source === 'twelvedata' ? '● LIVE' : '⚠ FALLBACK'}
                      </span>
                    </div>
                    <div className="level-card">
                      <span className="level-label">Weekly High</span>
                      <span className="level-value positive">{fmt(lv.weekly_high, selectedSymbol)}</span>
                    </div>
                    <div className="level-card">
                      <span className="level-label">Weekly Low</span>
                      <span className="level-value negative">{fmt(lv.weekly_low, selectedSymbol)}</span>
                    </div>
                    <div className="level-card">
                      <span className="level-label">Monthly Range</span>
                      <span className="level-value muted" style={{ fontSize: 11 }}>
                        {fmt(lv.monthly_low, selectedSymbol)} — {fmt(lv.monthly_high, selectedSymbol)}
                      </span>
                    </div>
                  </div>

                  {/* Pivot / S/R Table */}
                  <div className="subsection-title">Support / Résistance — Pivot Points</div>
                  <div className="sr-table">
                    <div className="sr-row header-row"><span>Niveau</span><span>Prix</span></div>
                    <div className="sr-row resistance"><span>R3</span><span>{fmt(lv.resistance_3, selectedSymbol)}</span></div>
                    <div className="sr-row resistance"><span>R2</span><span>{fmt(lv.resistance_2, selectedSymbol)}</span></div>
                    <div className="sr-row resistance"><span>R1</span><span>{fmt(lv.resistance_1, selectedSymbol)}</span></div>
                    <div className="sr-row pivot-row"><span>PIVOT</span><span>{fmt(lv.pivot, selectedSymbol)}</span></div>
                    <div className="sr-row support"><span>S1</span><span>{fmt(lv.support_1, selectedSymbol)}</span></div>
                    <div className="sr-row support"><span>S2</span><span>{fmt(lv.support_2, selectedSymbol)}</span></div>
                    <div className="sr-row support"><span>S3</span><span>{fmt(lv.support_3, selectedSymbol)}</span></div>
                  </div>

                  {/* Smoke Zones */}
                  {lv.smoke_zones && lv.smoke_zones.length > 0 && (
                    <>
                      <div className="subsection-title">Smoke Zones — Pièges Institutionnels ({lv.smoke_zones.length})</div>
                      {lv.smoke_zones.map((sz, i) => (
                        <div key={i} className="smoke-card">
                          <div className="smoke-range">
                            {fmt(sz.low || sz.price_low, selectedSymbol)} — {fmt(sz.high || sz.price_high, selectedSymbol)}
                          </div>
                          <div className="smoke-desc">{sz.description || sz.type || 'Zone de manipulation potentielle'}</div>
                        </div>
                      ))}
                    </>
                  )}

                  {/* COT Accumulation Levels */}
                  {lv.cot_levels && lv.cot_levels.accumulation_weeks && lv.cot_levels.accumulation_weeks.length > 0 && (
                    <>
                      <div className="subsection-title">Smart Money — Accumulation/Distribution</div>
                      {lv.cot_levels.accumulation_weeks.map((w, i) => (
                        <div key={i} className="accum-card">
                          <span className="muted">{w.date}</span>
                          <span style={{ color: w.direction === 'ACCUMULATION' ? 'var(--green)' : 'var(--red)', fontWeight: 600, fontSize: 11 }}>
                            {w.direction}
                          </span>
                          <span className="muted">{w.magnitude}% OI</span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: w.sm_change >= 0 ? 'var(--green)' : 'var(--red)' }}>
                            {w.sm_change >= 0 ? '+' : ''}{w.sm_change?.toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </>
                  )}

                </>
              )}

              {!levelsLoading && !lv && (
                <p className="muted" style={{ padding: 10 }}>Niveaux indisponibles pour ce symbole.</p>
              )}
            </div>
          </div>
        );
      })()}

      <footer className="footer-pro">
        <div className="footer-top">
          <div className="footer-brand">
            <span className="footer-logo">QUANTDASH</span>
            <span className="footer-tagline">Institutional Positioning Intelligence</span>
          </div>
          <div className="footer-links">
            <a href="mailto:contact@quantdash.io" className="footer-link">Contact</a>
            <span className="footer-sep">·</span>
            <a href="https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm" target="_blank" rel="noreferrer" className="footer-link">CFTC Data</a>
            <span className="footer-sep">·</span>
            <a href="https://www.myfxbook.com/community/outlook" target="_blank" rel="noreferrer" className="footer-link">Myfxbook</a>
            <span className="footer-sep">·</span>
            <a href="https://www.forexfactory.com/calendar" target="_blank" rel="noreferrer" className="footer-link">Forex Factory</a>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2025 QuantDash · All data is provided for informational purposes only and does not constitute financial advice.</span>
          <span>Auto-refresh {REFRESH_MS / 1000}s · v4.0</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
