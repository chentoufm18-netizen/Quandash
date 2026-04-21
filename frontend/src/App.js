import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './App.css';

const API = 'https://quandash.onrender.com';
const REFRESH_MS = 30000;

function App() {
  const [composite, setComposite] = useState(null);
  const [cotData, setCotData] = useState(null);
  const [ecoData, setEcoData] = useState(null);
  const [sentData, setSentData] = useState(null);
  const [levelsData, setLevelsData] = useState(null);
  const [levelsLoading, setLevelsLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async (showLoading) => {
    if (showLoading) setLoading(true);
    try {
      const endpoints = ['/api/composite', '/api/cot', '/api/eco', '/api/sentiment'];
      const [comp, cot, eco, sent] = await Promise.all(
        endpoints.map(e => fetch(`${API}${e}`).then(r => r.json()).catch(() => null))
      );
      if (comp) setComposite(comp);
      if (cot) setCotData(cot);
      if (eco) setEcoData(eco);
      if (sent) setSentData(sent);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(true); const t = setInterval(() => fetchData(false), REFRESH_MS); return () => clearInterval(t); }, [fetchData]);

  useEffect(() => {
    if (!selectedSymbol) { setLevelsData(null); return; }
    setLevelsLoading(true);
    fetch(`${API}/api/levels/${encodeURIComponent(selectedSymbol)}`)
      .then(r => r.json()).then(d => { setLevelsData(d); setLevelsLoading(false); })
      .catch(() => setLevelsLoading(false));
  }, [selectedSymbol]);

  const getSymbols = () => {
    const items = Object.values(composite?.data || cotData?.data || {});
    if (activeCategory === 'all') return items;
    return items.filter(i => i.category === activeCategory);
  };

  const getScore = (item) => item.composite_score ?? item.sentiment_score ?? 0;
  const getBias = (item) => item.composite_bias ?? item.bias ?? 'NEUTRAL';
  const scoreColor = (s) => s > 20 ? 'var(--green)' : s < -20 ? 'var(--red)' : 'var(--text-muted)';

  const fmt = (v, sym) => {
    if (v === undefined || v === null) return '—';
    const d = ['EUR/USD','GBP/USD','AUD/USD','NZD/USD','USD/CHF','USD/CAD'].includes(sym) ? 5 : 2;
    return Number(v).toFixed(d);
  };

  const cats = [
    { key: 'all', label: 'All', icon: '◉' },
    { key: 'forex', label: 'Forex', icon: '💱' },
    { key: 'index', label: 'Indices', icon: '📊' },
    { key: 'crypto', label: 'Crypto', icon: '₿' },
    { key: 'commodity', label: 'Commodities', icon: '🛢' },
  ];

  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: '📊' },
    { key: 'cot', label: 'COT Scanner', icon: '🏦' },
    { key: 'sentiment', label: 'Retail Sentiment', icon: '👥' },
    { key: 'eco', label: 'Economic Calendar', icon: '📅' },
    { key: 'methodology', label: 'Methodology', icon: '📘' },
  ];

  if (loading) return (
    <div className="loading-screen"><div className="spinner" /><p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading market data...</p></div>
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
  const sentSymbols = sentData?.data || {};
  const lv = levelsData;

  return (
    <div className="app">
      {/* ===== SIDEBAR ===== */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-dot" />
          <h1>QUANDASH</h1>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(n => (
            <div key={n.key} className={`nav-item ${activeTab === n.key ? 'active' : ''}`} onClick={() => setActiveTab(n.key)}>
              <span className="nav-icon">{n.icon}</span>
              <span className="nav-label">{n.label}</span>
              {n.key === 'eco' && highEvents.length > 0 && <span className="nav-badge">{highEvents.length}</span>}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-status">
            <span className="status-dot" />
            <span>Live — auto-refresh 30s</span>
          </div>
        </div>
      </aside>

      {/* ===== MAIN CONTENT ===== */}
      <main className="main">

        {/* ===== DASHBOARD TAB ===== */}
        {activeTab === 'dashboard' && (
          <>
            <div className="page-header">
              <div className="page-title">Top Trading Setups</div>
              <div className="page-sub">Composite scoring: COT + Economic + Sentiment analysis</div>
            </div>

            <div className="summary-strip">
              <div className="summary-card">
                <div className="summary-label">Bullish Signals</div>
                <div className="summary-value green">{bullishCount}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Bearish Signals</div>
                <div className="summary-value red">{bearishCount}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Neutral</div>
                <div className="summary-value amber">{neutralCount}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Total Assets</div>
                <div className="summary-value" style={{ color: 'var(--text-primary)' }}>{allSymbols.length}</div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2>Scoring Table</h2>
                <div className="filter-row">
                  {cats.map(c => (
                    <button key={c.key} className={`filter-btn ${activeCategory === c.key ? 'active' : ''}`}
                      onClick={() => setActiveCategory(c.key)}>{c.icon} {c.label}</button>
                  ))}
                </div>
              </div>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr>
                    <th>Symbol</th><th>Category</th><th>Score</th><th>Bias</th>
                    <th>COT</th><th>Eco</th><th>Sent.</th><th>SM Net</th><th>SM Δ</th>
                  </tr></thead>
                  <tbody>
                    {[...symbols].sort((a, b) => getScore(b) - getScore(a)).map((s, i) => (
                      <tr key={i} className={selectedSymbol === s.symbol ? 'selected' : ''}
                        onClick={() => setSelectedSymbol(selectedSymbol === s.symbol ? null : s.symbol)}>
                        <td style={{ fontWeight: 600 }}>{s.symbol}</td>
                        <td><span className={`cat-badge ${s.category}`}>{s.category}</span></td>
                        <td>
                          <div className="score-bar-wrap">
                            <div className="score-bar-track">
                              <div className="score-bar-fill" style={{
                                width: `${Math.min(Math.abs(getScore(s)), 100) / 2}%`,
                                background: getScore(s) > 0 ? 'var(--green)' : 'var(--red)',
                                marginLeft: getScore(s) < 0 ? `${50 - Math.abs(getScore(s)) / 2}%` : '50%',
                              }} />
                            </div>
                            <span className="mono" style={{ color: scoreColor(getScore(s)), minWidth: 40, textAlign: 'right' }}>
                              {getScore(s) > 0 ? '+' : ''}{getScore(s)}
                            </span>
                          </div>
                        </td>
                        <td><span className={`bias-tag ${getBias(s)}`}>{getBias(s)}</span></td>
                        <td className="mono muted">{s.cot_score ?? '—'}</td>
                        <td className="mono muted">{s.eco_score ?? '—'}</td>
                        <td className="mono muted">{s.sentiment_score !== undefined && s.retail_long_pct ? s.sentiment_score : '—'}</td>
                        <td className={`mono ${(s.smart_money_net || 0) >= 0 ? 'positive' : 'negative'}`}>{s.smart_money_net?.toLocaleString() || '—'}</td>
                        <td className={`mono ${(s.smart_money_change || 0) >= 0 ? 'positive' : 'negative'}`}>
                          {s.smart_money_change !== undefined ? `${s.smart_money_change >= 0 ? '+' : ''}${s.smart_money_change?.toLocaleString()}` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* ===== DETAIL PANEL ===== */}
            {selectedSymbol && (composite?.data?.[selectedSymbol] || cotData?.data?.[selectedSymbol]) && (() => {
              const d = composite?.data?.[selectedSymbol] || cotData?.data?.[selectedSymbol];
              return (
                <div className="card">
                  <div className="card-header">
                    <h2>{selectedSymbol} — Full Analysis</h2>
                    <span className={`bias-tag ${getBias(d)}`}>{getBias(d)}</span>
                  </div>
                  <div className="card-body">
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={d.history?.map((h, idx) => ({ w: `W${idx + 1}`, net: h.smart_money?.net || 0 })) || []}>
                        <XAxis dataKey="w" tick={{ fill: '#555764', fontSize: 11 }} />
                        <YAxis tick={{ fill: '#555764', fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: '#151820', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#e8e9ed' }} />
                        <Bar dataKey="net" radius={[4, 4, 0, 0]}>
                          {(d.history || []).map((h, i) => <Cell key={i} fill={(h.smart_money?.net || 0) >= 0 ? '#22c55e' : '#ef4444'} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>

                    {levelsLoading && <p className="muted" style={{ padding: 10, fontSize: 12 }}>Loading levels...</p>}

                    {!levelsLoading && lv && (
                      <>
                        <div className="detail-grid" style={{ marginTop: 16 }}>
                          <div className="detail-card">
                            <div className="detail-label">Current Price</div>
                            <div className="detail-value" style={{ color: 'var(--blue)' }}>{fmt(lv.current_price, selectedSymbol)}</div>
                          </div>
                          <div className="detail-card">
                            <div className="detail-label">ATR (14)</div>
                            <div className="detail-value">{fmt(lv.atr_14, selectedSymbol)}</div>
                          </div>
                          <div className="detail-card">
                            <div className="detail-label">Source</div>
                            <div className="detail-value" style={{ fontSize: 12, color: ['yahoo','twelvedata','live'].includes(lv.data_source) ? 'var(--green)' : lv.data_source === 'cached' ? 'var(--blue)' : 'var(--amber)' }}>
                              {['yahoo','twelvedata','live'].includes(lv.data_source) ? '● LIVE' : lv.data_source === 'cached' ? '● CACHED' : '⚠ FALLBACK'}
                            </div>
                          </div>
                          <div className="detail-card">
                            <div className="detail-label">Weekly High</div>
                            <div className="detail-value positive">{fmt(lv.weekly_high, selectedSymbol)}</div>
                          </div>
                          <div className="detail-card">
                            <div className="detail-label">Weekly Low</div>
                            <div className="detail-value negative">{fmt(lv.weekly_low, selectedSymbol)}</div>
                          </div>
                          <div className="detail-card">
                            <div className="detail-label">Monthly Range</div>
                            <div className="detail-value muted" style={{ fontSize: 12 }}>{fmt(lv.monthly_low, selectedSymbol)} — {fmt(lv.monthly_high, selectedSymbol)}</div>
                          </div>
                        </div>

                        <h3 style={{ fontSize: 13, fontWeight: 600, margin: '16px 0 10px', color: 'var(--text-secondary)' }}>WEEKLY PIVOT POINTS</h3>
                        <table className="pivot-table">
                          <tbody>
                            <tr className="resistance"><td>R3</td><td>{fmt(lv.resistance_3, selectedSymbol)}</td></tr>
                            <tr className="resistance"><td>R2</td><td>{fmt(lv.resistance_2, selectedSymbol)}</td></tr>
                            <tr className="resistance"><td>R1</td><td>{fmt(lv.resistance_1, selectedSymbol)}</td></tr>
                            <tr className="pivot-row"><td>PIVOT</td><td>{fmt(lv.pivot, selectedSymbol)}</td></tr>
                            <tr className="support"><td>S1</td><td>{fmt(lv.support_1, selectedSymbol)}</td></tr>
                            <tr className="support"><td>S2</td><td>{fmt(lv.support_2, selectedSymbol)}</td></tr>
                            <tr className="support"><td>S3</td><td>{fmt(lv.support_3, selectedSymbol)}</td></tr>
                          </tbody>
                        </table>

                        {lv.smoke_zones?.length > 0 && (
                          <>
                            <h3 style={{ fontSize: 13, fontWeight: 600, margin: '20px 0 10px', color: 'var(--text-secondary)' }}>
                              SMOKE ZONES ({lv.smoke_zones.length})
                            </h3>
                            {lv.smoke_zones.map((z, i) => (
                              <div key={i} className="smoke-zone">
                                <div className="smoke-range">{fmt(z.low, selectedSymbol)} — {fmt(z.high, selectedSymbol)}</div>
                                <div className="smoke-desc">{z.description}</div>
                              </div>
                            ))}
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })()}
          </>
        )}

        {/* ===== COT SCANNER ===== */}
        {activeTab === 'cot' && (
          <>
            <div className="page-header">
              <div className="page-title">COT Scanner</div>
              <div className="page-sub">Institutional positioning from CFTC Commitment of Traders reports</div>
            </div>
            <div className="card">
              <div className="card-header">
                <h2>Composite Score — All Assets</h2>
                <div className="filter-row">
                  {cats.map(c => (
                    <button key={c.key} className={`filter-btn ${activeCategory === c.key ? 'active' : ''}`}
                      onClick={() => setActiveCategory(c.key)}>{c.icon} {c.label}</button>
                  ))}
                </div>
              </div>
              <div style={{ padding: '12px 0' }}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 60, left: 20 }}>
                    <XAxis dataKey="name" tick={{ fill: '#555764', fontSize: 11 }} angle={-45} textAnchor="end" interval={0} />
                    <YAxis tick={{ fill: '#555764', fontSize: 11 }} domain={[-100, 100]} ticks={[-100, -50, 0, 50, 100]} />
                    <Tooltip contentStyle={{ background: '#151820', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, color: '#e8e9ed' }} formatter={v => [`${v}`, 'Score']} />
                    <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                      {chartData.map((e, i) => <Cell key={i} fill={e.score > 20 ? '#22c55e' : e.score < -20 ? '#ef4444' : '#555764'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="card">
              <div className="card-header"><h2>COT Positioning — Full Table</h2></div>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr>
                    <th>Symbol</th><th>Cat.</th><th>Score</th><th>Bias</th>
                    <th>SM Net</th><th>SM Δ</th><th>SM Long</th><th>SM Short</th>
                  </tr></thead>
                  <tbody>
                    {[...symbols].sort((a, b) => getScore(b) - getScore(a)).map((s, i) => (
                      <tr key={i} className={selectedSymbol === s.symbol ? 'selected' : ''}
                        onClick={() => setSelectedSymbol(selectedSymbol === s.symbol ? null : s.symbol)}>
                        <td style={{ fontWeight: 600 }}>{s.symbol}</td>
                        <td><span className={`cat-badge ${s.category}`}>{s.category}</span></td>
                        <td><span className={`score-badge ${getBias(s).toLowerCase()}`}>{getScore(s) > 0 ? '+' : ''}{getScore(s)}</span></td>
                        <td><span className={`bias-tag ${getBias(s)}`}>{getBias(s)}</span></td>
                        <td className={`mono ${(s.smart_money_net || 0) >= 0 ? 'positive' : 'negative'}`}>{s.smart_money_net?.toLocaleString() || '—'}</td>
                        <td className={`mono ${(s.smart_money_change || 0) >= 0 ? 'positive' : 'negative'}`}>
                          {s.smart_money_change !== undefined ? `${s.smart_money_change >= 0 ? '+' : ''}${s.smart_money_change?.toLocaleString()}` : '—'}
                        </td>
                        <td className="mono muted">{s.smart_money_long?.toLocaleString() || '—'}</td>
                        <td className="mono muted">{s.smart_money_short?.toLocaleString() || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* ===== RETAIL SENTIMENT ===== */}
        {activeTab === 'sentiment' && (
          <>
            <div className="page-header">
              <div className="page-title">Retail Sentiment</div>
              <div className="page-sub">Contrarian analysis — trade against the retail crowd</div>
            </div>
            <div className="card">
              <div className="card-header">
                <h2>Live Sentiment — Myfxbook Community Outlook</h2>
                <span className="card-sub">Real-time retail positioning from live accounts</span>
              </div>
              <iframe
                title="Myfxbook Community Outlook"
                src="/sentiment-widget.html"
                style={{ width: '100%', height: 500, border: 'none', background: '#151820' }}
              />
            </div>
            <div className="card">
              <div className="card-header">
                <h2>Contrarian Scoring — QuantDash</h2>
                <span className="card-sub">⚠️ = Extreme crowd positioning (strong contrarian signal)</span>
              </div>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr>
                    <th>Symbol</th><th>Retail Long</th><th>Retail Short</th><th>Retail Bias</th>
                    <th>Contrarian Score</th><th>Extreme</th><th>COT Alignment</th>
                  </tr></thead>
                  <tbody>
                    {Object.values(sentSymbols).sort((a, b) => Math.abs(b.contrarian_score) - Math.abs(a.contrarian_score)).map((s, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{s.symbol}</td>
                        <td>
                          <div className="retail-bar">
                            <div className="retail-long" style={{ width: `${s.retail_long_pct}%` }}>{s.retail_long_pct.toFixed(1)}%</div>
                            <div className="retail-short" style={{ width: `${s.retail_short_pct}%` }}>{s.retail_short_pct.toFixed(1)}%</div>
                          </div>
                        </td>
                        <td className="mono muted">{s.retail_short_pct.toFixed(1)}%</td>
                        <td><span className={`bias-tag ${s.retail_bias === 'LONG' ? 'BULLISH' : 'BEARISH'}`}>{s.retail_bias}</span></td>
                        <td>
                          <span className={`score-badge ${s.contrarian_score > 0 ? 'bullish' : s.contrarian_score < 0 ? 'bearish' : 'neutral'}`}>
                            {s.contrarian_score > 0 ? '+' : ''}{s.contrarian_score}
                          </span>
                        </td>
                        <td>{s.crowd_extreme ? <span style={{ color: 'var(--amber)' }}>⚠️ EXTREME</span> : <span className="muted">Normal</span>}</td>
                        <td style={{ color: s.cot_alignment === 'ALIGNED' ? 'var(--green)' : s.cot_alignment === 'DIVERGENT' ? 'var(--red)' : 'var(--text-muted)', fontWeight: 500 }}>
                          {s.cot_alignment}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* ===== ECONOMIC CALENDAR ===== */}
        {activeTab === 'eco' && (
          <>
            <div className="page-header">
              <div className="page-title">Economic Calendar</div>
              <div className="page-sub">High-impact events that move the markets</div>
            </div>
            <div className="card">
              <div className="card-header">
                <h2>Live Calendar — Investing.com</h2>
                <span className="card-sub">Real-time economic releases</span>
              </div>
              <iframe className="eco-iframe" title="Economic Calendar"
                src="https://sslecal2.investing.com/?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=2,3&features=datepicker,timezone,timeselector,filters&countries=110,17,25,34,32,6,37,36,5,22,39,14,48,10,35,43,56,26,12,72,4,50,71&calType=week&timeZone=58&lang=5" />
            </div>
          </>
        )}

        {/* ===== METHODOLOGY ===== */}
        {activeTab === 'methodology' && (
          <>
            <div className="page-header">
              <div className="page-title">Methodology</div>
              <div className="page-sub">How QuantDash scoring works — transparent, rules-based system</div>
            </div>
            <div className="card">
              <div className="card-body">
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 20 }}>
                  QuantDash combines three independent data pillars into a single composite score for each instrument.
                  The system is fully rules-based with no discretionary overrides.
                </p>
                <div className="pillar-grid">
                  {[
                    { icon: '🏦', name: 'COT Data (60%)', desc: 'CFTC institutional positioning — smart money direction' },
                    { icon: '📅', name: 'Economic Data (20%)', desc: 'Macro releases impact on currency strength' },
                    { icon: '👥', name: 'Retail Sentiment (20%)', desc: 'Contrarian signal — fade the crowd' },
                  ].map((p, i) => (
                    <div key={i} className="pillar-card">
                      <div className="pillar-icon">{p.icon}</div>
                      <div className="pillar-name">{p.name}</div>
                      <div className="pillar-desc">{p.desc}</div>
                    </div>
                  ))}
                </div>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: '20px 0 12px' }}>Data Sources</h3>
                <table className="source-table">
                  <thead><tr><th>Source</th><th>Data</th><th>Frequency</th></tr></thead>
                  <tbody>
                    <tr><td>CFTC</td><td>Commitment of Traders reports</td><td>Weekly (Friday)</td></tr>
                    <tr><td>Yahoo Finance</td><td>Price data (OHLCV)</td><td>Hourly</td></tr>
                    <tr><td>Investing.com</td><td>Economic calendar</td><td>Real-time (iframe)</td></tr>
                    <tr><td>Dukascopy SWFX</td><td>Retail sentiment</td><td>Real-time (iframe)</td></tr>
                  </tbody>
                </table>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: '20px 0 12px' }}>Scoring Scale</h3>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                  Each instrument receives a composite score from -100 to +100.
                  Scores above +40 signal strong bullish positioning; below -40 signal strong bearish.
                  The bias tag (BULLISH/BEARISH/NEUTRAL) reflects the consensus across all three pillars.
                </p>
              </div>
            </div>
          </>
        )}

      </main>
    </div>
  );
}

export default App;
