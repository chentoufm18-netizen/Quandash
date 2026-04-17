import React, { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './App.css';

const API = process.env.REACT_APP_API_URL || 'http://127.0.0.1:5000';
const REFRESH_MS = 30000;

function App() {
  const [composite, setComposite] = useState(null);
  const [cotData, setCotData] = useState(null);
  const [ecoData, setEcoData] = useState(null);
  const [sentData, setSentData] = useState(null);
  const [levelsData, setLevelsData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    setRefreshing(true);
    try {
      const eps = ['/api/composite','/api/cot','/api/eco','/api/sentiment','/api/summary','/api/levels'];
      const res = await Promise.all(eps.map(e => fetch(`${API}${e}`).catch(() => null)));
      if (res[0]?.ok) setComposite(await res[0].json());
      if (res[1]?.ok) setCotData(await res[1].json());
      if (res[2]?.ok) setEcoData(await res[2].json());
      if (res[3]?.ok) setSentData(await res[3].json());
      if (res[4]?.ok) setSummary(await res[4].json());
      if (res[5]?.ok) setLevelsData(await res[5].json());
      setLastRefresh(new Date());
      setError(null);
    } catch (e) { setError('API inaccessible'); }
    setLoading(false); setRefreshing(false);
  }, []);

  useEffect(() => { fetchData(true); const i = setInterval(() => fetchData(false), REFRESH_MS); return () => clearInterval(i); }, [fetchData]);

  const getSymbols = () => { const s = composite?.data || cotData?.data || {}; const items = Object.values(s); return activeCategory === 'all' ? items : items.filter(i => i.category === activeCategory); };
  const getScore = (item) => item.composite_score ?? item.sentiment_score ?? 0;
  const getBias = (item) => item.composite_bias ?? item.bias ?? 'NEUTRAL';
  const scoreColor = (s) => { if (s > 50) return '#22c55e'; if (s > 25) return '#4ade80'; if (s > 0) return '#86efac'; if (s > -25) return '#fca5a5'; if (s > -50) return '#f87171'; return '#ef4444'; };
  const biasTag = (bias) => { const m = { BULLISH:{bg:'#052e16',c:'#4ade80',b:'#166534'}, BEARISH:{bg:'#2a0a0a',c:'#f87171',b:'#7f1d1d'}, NEUTRAL:{bg:'#1a1a2e',c:'#a5b4fc',b:'#312e81'} }; const s = m[bias]||m.NEUTRAL; return <span style={{background:s.bg,color:s.c,border:`1px solid ${s.b}`,padding:'2px 10px',borderRadius:12,fontSize:11,fontWeight:600}}>{bias}</span>; };
  const impactDot = (i) => <span style={{color:{High:'#ef4444',Medium:'#f59e0b',Low:'#6b7280'}[i]||'#6b7280',marginRight:4}}>●</span>;
  const sentBadge = (s) => { const m={BULLISH:{bg:'#052e16',c:'#4ade80'},BEARISH:{bg:'#2a0a0a',c:'#f87171'},NEUTRAL:{bg:'#1c1c2e',c:'#94a3b8'},PENDING:{bg:'#1a1500',c:'#fbbf24'}}; const st=m[s]||m.NEUTRAL; return <span style={{background:st.bg,color:st.c,padding:'2px 8px',borderRadius:10,fontSize:10,fontWeight:600}}>{s}</span>; };
  const cats = [{key:'all',label:'Tous',icon:'◉'},{key:'forex',label:'Forex',icon:'💱'},{key:'index',label:'Indices',icon:'📊'},{key:'crypto',label:'Crypto',icon:'₿'},{key:'commodity',label:'Commodités',icon:'🛢'}];

  if (loading) return <div className="app"><div className="loading"><div className="spinner"/><p>Chargement...</p></div></div>;
  if (error && !cotData) return <div className="app"><div className="error-box"><h2>Erreur</h2><p>{error}</p><button onClick={()=>fetchData(true)} className="btn">Réessayer</button></div></div>;

  const symbols = getSymbols();
  const allSymbols = Object.values(composite?.data || cotData?.data || {});
  const chartData = [...symbols].sort((a,b)=>getScore(b)-getScore(a)).map(s=>({name:s.symbol,score:getScore(s)}));
  const highEvents = ecoData?.high_impact_events || [];
  const allEvents = ecoData?.events || [];
  const currScores = ecoData?.currency_scores || {};
  const sentSymbols = sentData?.data || {};
  const levels = levelsData?.data || {};

  const selectedLevels = selectedSymbol ? levels[selectedSymbol] : null;
  const selectedData = selectedSymbol ? (composite?.data?.[selectedSymbol] || cotData?.data?.[selectedSymbol]) : null;

  const CatTabs = () => <div className="category-tabs">{cats.map(c=><button key={c.key} className={`tab ${activeCategory===c.key?'active':''}`} onClick={()=>setActiveCategory(c.key)}><span className="tab-icon">{c.icon}</span> {c.label}</button>)}</div>;

  const ScoreChart = ({title}) => (
    <div className="card chart-card">
      <div className="card-header"><h2>{title}</h2><CatTabs/></div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{top:20,right:20,bottom:60,left:20}}>
          <XAxis dataKey="name" tick={{fill:'#94a3b8',fontSize:11}} angle={-45} textAnchor="end" interval={0}/>
          <YAxis tick={{fill:'#94a3b8',fontSize:11}} domain={[-100,100]} ticks={[-100,-50,0,50,100]}/>
          <Tooltip contentStyle={{background:'#0f172a',border:'1px solid #1e293b',borderRadius:8,color:'#e2e8f0'}} formatter={v=>[`${v}`,'Score']}/>
          <Bar dataKey="score" radius={[4,4,0,0]}>{chartData.map((e,i)=><Cell key={i} fill={scoreColor(e.score)}/>)}</Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className="app">
      {/* HEADER */}
      <header className="header">
        <div className="header-left"><h1 className="logo">QUANTDASH</h1><span className="version">v3.0</span></div>
        <div className="header-right">
          <div className="main-tabs">
            {[{key:'overview',label:"Vue d'ensemble"},{key:'cot',label:'COT Scanner'},{key:'eco',label:'Calendrier Éco',badge:highEvents.length},{key:'sentiment',label:'Sentiment Retail'}].map(t=>
              <button key={t.key} className={`main-tab ${activeTab===t.key?'active':''}`} onClick={()=>setActiveTab(t.key)}>
                {t.label}{t.badge>0&&<span className="tab-badge">{t.badge}</span>}
              </button>
            )}
          </div>
          <span className="signal-count">{allSymbols.length} signaux</span>
          <div className="refresh-info"><span className={`live-dot ${refreshing?'pulse':''}`}>●</span><span className="last-update">{lastRefresh?lastRefresh.toLocaleTimeString('fr-FR'):'—'}</span></div>
          <button onClick={()=>fetchData(false)} className="btn-refresh">⟳</button>
        </div>
      </header>

      {/* SUMMARY */}
      <div className="summary-row">
        <div className="card summary-card bullish-card">
          <div className="card-label">Top Bullish</div>
          {(summary?.top_bullish||[]).slice(0,3).map((s,i)=><div key={i} className="summary-item"><span className="summary-symbol">{s.symbol}</span><span className="summary-score bullish">+{s.score}</span></div>)}
        </div>
        <div className="card summary-card bearish-card">
          <div className="card-label">Top Bearish</div>
          {(summary?.top_bearish||[]).slice(0,3).map((s,i)=><div key={i} className="summary-item"><span className="summary-symbol">{s.symbol}</span><span className="summary-score bearish">{s.score}</span></div>)}
        </div>
        <div className="card summary-card stats-card">
          <div className="card-label">Signaux</div>
          <div className="stats-grid">
            <div className="stat"><span className="stat-value bullish">{allSymbols.filter(d=>getBias(d)==='BULLISH').length}</span><span className="stat-label">Bullish</span></div>
            <div className="stat"><span className="stat-value neutral">{allSymbols.filter(d=>getBias(d)==='NEUTRAL').length}</span><span className="stat-label">Neutral</span></div>
            <div className="stat"><span className="stat-value bearish">{allSymbols.filter(d=>getBias(d)==='BEARISH').length}</span><span className="stat-label">Bearish</span></div>
          </div>
        </div>
      </div>

      {/* OVERVIEW TAB */}
      {activeTab === 'overview' && <>
        <ScoreChart title="Composite Score — Tous les Actifs"/>
        <div className="card table-card">
          <div className="card-header"><h2>Tableau de Bord — Scoring Composite</h2></div>
          <div className="table-wrapper"><table className="data-table">
            <thead><tr><th>Symbole</th><th>Cat.</th><th>Score</th><th>Biais</th><th>COT</th><th>Éco</th><th>Sent.</th><th>SM Net</th><th>SM Δ</th></tr></thead>
            <tbody>{[...symbols].sort((a,b)=>getScore(b)-getScore(a)).map((s,i)=>
              <tr key={i} className={`table-row ${selectedSymbol===s.symbol?'selected':''}`} onClick={()=>setSelectedSymbol(selectedSymbol===s.symbol?null:s.symbol)}>
                <td className="symbol-cell">{s.symbol}</td>
                <td><span className={`cat-badge ${s.category}`}>{s.category}</span></td>
                <td><div className="score-bar-wrapper"><div className="score-bar" style={{width:`${Math.abs(getScore(s))/2}%`,background:scoreColor(getScore(s)),marginLeft:getScore(s)<0?`${50-Math.abs(getScore(s))/2}%`:'50%'}}/><span className="score-value">{getScore(s)>0?'+':''}{getScore(s)}</span></div></td>
                <td>{biasTag(getBias(s))}</td>
                <td className="mono-cell">{s.cot_score??'—'}</td>
                <td className="mono-cell">{s.eco_score??'—'}</td>
                <td className="mono-cell">{s.retail_long_pct?s.sentiment_score:'—'}</td>
                <td className={s.smart_money_net>=0?'positive':'negative'}>{s.smart_money_net?.toLocaleString()}</td>
                <td className={(s.smart_money_change||0)>=0?'positive':'negative'}>{(s.smart_money_change||0)>=0?'+':''}{s.smart_money_change?.toLocaleString()}</td>
              </tr>
            )}</tbody>
          </table></div>
        </div>
      </>}

      {/* COT TAB */}
      {activeTab === 'cot' && <>
        <ScoreChart title="COT Institutional Positioning"/>
        <div className="card table-card">
          <div className="card-header"><h2>COT Scanner</h2></div>
          <div className="table-wrapper"><table className="data-table">
            <thead><tr><th>Symbole</th><th>Catégorie</th><th>Score</th><th>Biais</th><th>SM Net</th><th>SM Δ</th><th>OI</th><th>Date</th></tr></thead>
            <tbody>{[...symbols].sort((a,b)=>getScore(b)-getScore(a)).map((s,i)=>
              <tr key={i} className={`table-row ${selectedSymbol===s.symbol?'selected':''}`} onClick={()=>setSelectedSymbol(selectedSymbol===s.symbol?null:s.symbol)}>
                <td className="symbol-cell">{s.symbol}</td>
                <td><span className={`cat-badge ${s.category}`}>{s.category}</span></td>
                <td><div className="score-bar-wrapper"><div className="score-bar" style={{width:`${Math.abs(getScore(s))/2}%`,background:scoreColor(getScore(s)),marginLeft:getScore(s)<0?`${50-Math.abs(getScore(s))/2}%`:'50%'}}/><span className="score-value">{getScore(s)>0?'+':''}{getScore(s)}</span></div></td>
                <td>{biasTag(getBias(s))}</td>
                <td className={s.smart_money_net>=0?'positive':'negative'}>{s.smart_money_net?.toLocaleString()}</td>
                <td className={(s.smart_money_change||0)>=0?'positive':'negative'}>{(s.smart_money_change||0)>=0?'+':''}{s.smart_money_change?.toLocaleString()}</td>
                <td className="muted">{s.open_interest?.toLocaleString()}</td>
                <td className="muted">{s.latest_date}</td>
              </tr>
            )}</tbody>
          </table></div>
        </div>
      </>}

      {/* ECO TAB */}
      {activeTab === 'eco' && <>
        <div className="card">
          <div className="card-header"><h2>Scores Économiques par Devise</h2></div>
          <div className="currency-scores-grid">
            {Object.entries(currScores).sort((a,b)=>b[1].normalized-a[1].normalized).map(([cur,d],i)=>
              <div key={i} className="currency-score-card">
                <div className="currency-name">{cur}</div>
                <div className="currency-score-bar-wrap"><div className="currency-score-bar" style={{width:`${Math.max(3,Math.abs(d.normalized)/2)}%`,background:d.normalized>=0?'#4ade80':'#f87171',marginLeft:d.normalized<0?`${50-Math.abs(d.normalized)/2}%`:'50%'}}/></div>
                <div className={`currency-score-val ${d.normalized>0?'positive':d.normalized<0?'negative':'muted'}`}>{d.normalized>0?'+':''}{d.normalized.toFixed(1)}</div>
                <div className="currency-events">{d.high_impact}🔴 / {d.events} evt</div>
              </div>
            )}
          </div>
        </div>
        <div className="card">
          <div className="card-header"><h2>Événements</h2><span className="impact-badge">{allEvents.length} événements</span></div>
          <div className="table-wrapper"><table className="data-table">
            <thead><tr><th>Date</th><th>Heure</th><th>Devise</th><th>Impact</th><th>Événement</th><th>Actuel</th><th>Prévision</th><th>Précédent</th><th>Sentiment</th></tr></thead>
            <tbody>{allEvents.map((e,i)=>
              <tr key={i} className="table-row" style={e.impact==='High'?{background:'rgba(239,68,68,0.05)'}:{}}>
                <td className="muted">{e.date}</td><td className="mono-cell">{e.time}</td>
                <td><span className="currency-badge">{e.currency}</span></td>
                <td>{impactDot(e.impact)}{e.impact}</td>
                <td style={{fontWeight:500}}>{e.title}</td>
                <td className={e.actual?'positive':'muted'}>{e.actual||'—'}</td>
                <td className="muted">{e.forecast||'—'}</td><td className="muted">{e.previous||'—'}</td>
                <td>{sentBadge(e.sentiment)}</td>
              </tr>
            )}</tbody>
          </table></div>
        </div>
      </>}

      {/* SENTIMENT TAB */}
      {activeTab === 'sentiment' && <>
        <div className="card">
          <div className="card-header"><h2>Sentiment Retail — Contrarian</h2><span className="muted" style={{fontSize:12}}>⚠️ = Signal contrarian fort</span></div>
          <div className="table-wrapper"><table className="data-table">
            <thead><tr><th>Symbole</th><th>Retail Long</th><th>Short</th><th>Biais</th><th>Contrarian</th><th>Extrême</th><th>COT Align</th></tr></thead>
            <tbody>{Object.values(sentSymbols).sort((a,b)=>Math.abs(b.contrarian_score)-Math.abs(a.contrarian_score)).map((s,i)=>
              <tr key={i} className="table-row">
                <td className="symbol-cell">{s.symbol}</td>
                <td><div className="retail-bar"><div className="retail-long" style={{width:`${s.retail_long_pct}%`}}>{s.retail_long_pct.toFixed(1)}%</div><div className="retail-short" style={{width:`${s.retail_short_pct}%`}}>{s.retail_short_pct.toFixed(1)}%</div></div></td>
                <td className="muted">{s.retail_short_pct.toFixed(1)}%</td>
                <td><span style={{background:s.retail_bias==='LONG'?'#052e16':'#2a0a0a',color:s.retail_bias==='LONG'?'#4ade80':'#f87171',padding:'2px 8px',borderRadius:10,fontSize:11,fontWeight:600}}>{s.retail_bias}</span></td>
                <td className={s.contrarian_score>0?'positive':s.contrarian_score<0?'negative':'muted'}><span style={{fontFamily:'monospace',fontWeight:600,fontSize:14}}>{s.contrarian_score>0?'+':''}{s.contrarian_score}</span></td>
                <td>{s.crowd_extreme?<span style={{color:'#f59e0b'}}>⚠️</span>:<span className="muted">—</span>}</td>
                <td style={{color:s.cot_alignment==='ALIGNED'?'#4ade80':s.cot_alignment==='DIVERGENT'?'#f87171':'#94a3b8',fontWeight:500}}>{s.cot_alignment}</td>
              </tr>
            )}</tbody>
          </table></div>
        </div>
      </>}

      {/* ===== DETAIL PANEL WITH KEY LEVELS ===== */}
      {selectedSymbol && selectedData && (
        <div className="card detail-card">
          <div className="card-header">
            <h2>{selectedSymbol} — Analyse Complète</h2>
            <button className="btn-close" onClick={()=>setSelectedSymbol(null)}>✕</button>
          </div>

          {/* Score + SM Data */}
          <div className="detail-grid">
            {[['Score Composite',getScore(selectedData),getScore(selectedData)>=0?'positive':'negative'],
              ['SM Long',selectedData.smart_money_long,'positive'],['SM Short',selectedData.smart_money_short,'negative'],
              ['Net Position',selectedData.smart_money_net,selectedData.smart_money_net>=0?'positive':'negative'],
              ['Commercial Net',selectedData.commercial_net,''],['Open Interest',selectedData.open_interest,'muted'],
              ['Retail Long',selectedData.retail_long_pct?`${selectedData.retail_long_pct}%`:'—',''],
              ['Crowd Extreme',selectedData.crowd_extreme?'OUI ⚠️':'Non',selectedData.crowd_extreme?'negative':''],
            ].map(([l,v,c],i)=><div key={i} className="detail-item"><span className="detail-label">{l}</span><span className={`detail-value ${c}`}>{typeof v==='number'?v.toLocaleString():v}</span></div>)}
          </div>

          {/* KEY LEVELS SECTION */}
          {selectedLevels && (
            <div className="levels-section">
              <h3 className="section-title">Key Levels — Niveaux Institutionnels</h3>

              {/* Price + ATR */}
              <div className="levels-grid">
                <div className="level-card price-card">
                  <span className="level-label">Prix Actuel</span>
                  <span className="level-value">{selectedLevels.current_price}</span>
                </div>
                <div className="level-card">
                  <span className="level-label">ATR (14)</span>
                  <span className="level-value">{selectedLevels.atr_14}</span>
                </div>
                <div className="level-card">
                  <span className="level-label">Pivot</span>
                  <span className="level-value">{selectedLevels.pivot}</span>
                </div>
              </div>

              {/* S/R Levels */}
              <div className="sr-table">
                <div className="sr-row header-row"><span>Résistances</span><span>Niveau</span></div>
                <div className="sr-row resistance"><span>R3</span><span>{selectedLevels.resistance_3}</span></div>
                <div className="sr-row resistance"><span>R2</span><span>{selectedLevels.resistance_2}</span></div>
                <div className="sr-row resistance"><span>R1</span><span>{selectedLevels.resistance_1}</span></div>
                <div className="sr-row pivot-row"><span>PIVOT</span><span>{selectedLevels.pivot}</span></div>
                <div className="sr-row support"><span>S1</span><span>{selectedLevels.support_1}</span></div>
                <div className="sr-row support"><span>S2</span><span>{selectedLevels.support_2}</span></div>
                <div className="sr-row support"><span>S3</span><span>{selectedLevels.support_3}</span></div>
                <div className="sr-row header-row" style={{marginTop:8}}><span>Range</span><span>Niveau</span></div>
                <div className="sr-row"><span>Weekly High</span><span>{selectedLevels.weekly_high}</span></div>
                <div className="sr-row"><span>Weekly Low</span><span>{selectedLevels.weekly_low}</span></div>
                <div className="sr-row"><span>Monthly High</span><span>{selectedLevels.monthly_high}</span></div>
                <div className="sr-row"><span>Monthly Low</span><span>{selectedLevels.monthly_low}</span></div>
              </div>

              {/* NRNR Patterns */}
              {selectedLevels.patterns && selectedLevels.patterns.length > 0 && (
                <div className="patterns-section">
                  <h4 className="subsection-title">Patterns NRNR Détectés</h4>
                  {selectedLevels.patterns.map((p, i) => (
                    <div key={i} className={`pattern-card ${p.direction === 'BULLISH' ? 'pattern-bull' : p.direction === 'BEARISH' ? 'pattern-bear' : 'pattern-neutral'}`}>
                      <div className="pattern-header">
                        <span className="pattern-type">{p.type}</span>
                        <span className={`pattern-dir ${p.direction === 'BULLISH' ? 'positive' : p.direction === 'BEARISH' ? 'negative' : ''}`}>{p.direction}</span>
                      </div>
                      <div className="pattern-desc">{p.description}</div>
                      <div className="pattern-levels">
                        <span>High: {p.level_high}</span>
                        <span>Low: {p.level_low}</span>
                        <span className="muted">{p.date}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Smoke Zones */}
              {selectedLevels.smoke_zones && selectedLevels.smoke_zones.length > 0 && (
                <div className="smoke-section">
                  <h4 className="subsection-title">Smoke Zones — Pièges Institutionnels</h4>
                  {selectedLevels.smoke_zones.map((s, i) => (
                    <div key={i} className="smoke-card">
                      <div className="smoke-range">{s.low} — {s.high}</div>
                      <div className="smoke-desc">{s.description}</div>
                      <span className="muted">{s.date}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* COT Levels */}
              {selectedLevels.cot_levels?.accumulation_weeks?.length > 0 && (
                <div className="cot-levels-section">
                  <h4 className="subsection-title">Smart Money — Semaines d'Accumulation</h4>
                  {selectedLevels.cot_levels.accumulation_weeks.map((w, i) => (
                    <div key={i} className="accum-card">
                      <span className={w.direction === 'ACCUMULATION' ? 'positive' : 'negative'}>{w.direction}</span>
                      <span className="mono-cell">{w.magnitude}% de l'OI</span>
                      <span className="muted">{w.date}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* History Chart */}
          <h3 className="section-title" style={{marginTop:16}}>Historique SM Net — 8 semaines</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={selectedData.history?.map(h=>({date:h.date?.slice(5,10),net:h.smart_money?.net||0})).reverse()}>
              <XAxis dataKey="date" tick={{fill:'#64748b',fontSize:10}}/><YAxis tick={{fill:'#64748b',fontSize:10}}/>
              <Tooltip contentStyle={{background:'#0f172a',border:'1px solid #1e293b',borderRadius:8,color:'#e2e8f0'}}/>
              <Bar dataKey="net" radius={[3,3,0,0]}>{selectedData.history?.map((h,i)=><Cell key={i} fill={(h.smart_money?.net||0)>=0?'#4ade80':'#f87171'}/>)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <footer className="footer"><p>QuantDash v3.0 — CFTC COT + Economic Calendar + Retail Sentiment + Key Levels</p></footer>
    </div>
  );
}

export default App;
