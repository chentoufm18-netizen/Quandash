"""ECO CALENDAR v5 — Twelve Data API"""
import requests, json, os
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TD_API_KEY = os.environ.get("TWELVE_DATA_KEY", "")

CURRENCY_IMPACT = {
    "USD": ["EUR/USD","GBP/USD","USD/JPY","USD/CHF","USD/CAD","AUD/USD","NZD/USD","S&P 500","Nasdaq 100","Dow Jones","Gold","Crude Oil WTI"],
    "EUR": ["EUR/USD"], "GBP": ["GBP/USD"], "JPY": ["USD/JPY"],
    "CHF": ["USD/CHF"], "CAD": ["USD/CAD"], "AUD": ["AUD/USD"], "NZD": ["NZD/USD"],
}

TD_COUNTRY = {
    "United States":"USD","Eurozone":"EUR","United Kingdom":"GBP",
    "Japan":"JPY","Switzerland":"CHF","Canada":"CAD","Australia":"AUD","New Zealand":"NZD",
}

KB = {
    "non-farm employment": {"neg":False,"above":"Plus de jobs → USD bullish. Fed retarde les baisses.","below":"Moins de jobs → USD bearish. Fed coupe les taux."},
    "unemployment rate":   {"neg":True, "above":"Chômage plus haut → USD bearish.","below":"Chômage plus bas → USD bullish."},
    "jobless claims":      {"neg":True, "above":"Plus de claims → USD bearish.","below":"Moins de claims → USD bullish."},
    "cpi":    {"neg":False,"above":"Inflation élevée → Fed hawkish → USD bullish.","below":"Inflation basse → Fed dovish → USD bearish."},
    "core cpi":{"neg":False,"above":"Core CPI élevé → Fed restrictive → USD bullish.","below":"Core CPI bas → Fed peut assouplir → USD bearish."},
    "ppi":    {"neg":False,"above":"Prix prod. en hausse → inflation pipeline → USD bullish.","below":"Prix prod. en baisse → désinflation → USD bearish."},
    "core ppi":{"neg":False,"above":"Core PPI en hausse → inflation persistante → USD bullish.","below":"Core PPI en baisse → pression réduite → USD bearish."},
    "gdp":    {"neg":False,"above":"PIB au-dessus → croissance forte → bullish.","below":"PIB sous → ralentissement → bearish."},
    "retail sales":{"neg":False,"above":"Conso forte → USD bullish.","below":"Conso faible → USD bearish."},
    "ism":    {"neg":False,"above":"PMI beat → expansion → bullish.","below":"PMI miss → contraction → bearish."},
    "pmi":    {"neg":False,"above":"PMI beat → expansion → bullish.","below":"PMI miss → contraction → bearish."},
    "interest rate":{"neg":False,"above":"Taux plus haut → hawkish surprise → bullish.","below":"Taux plus bas → dovish surprise → bearish."},
    "rate decision":{"neg":False,"above":"Plus hawkish → bullish.","below":"Plus dovish → bearish."},
    "fomc":   {"neg":False,"above":"Fed hawkish → USD bullish.","below":"Fed dovish → USD bearish."},
    "ecb":    {"neg":False,"above":"BCE hawkish → EUR bullish.","below":"BCE dovish → EUR bearish."},
    "boe":    {"neg":False,"above":"BoE hawkish → GBP bullish.","below":"BoE dovish → GBP bearish."},
    "trade balance":{"neg":False,"above":"Surplus meilleur → bullish.","below":"Déficit pire → bearish."},
    "durable goods":{"neg":False,"above":"Commandes en hausse → USD bullish.","below":"Commandes en baisse → USD bearish."},
    "consumer confidence":{"neg":False,"above":"Confiance en hausse → USD bullish.","below":"Confiance en baisse → USD bearish."},
    "michigan":{"neg":False,"above":"Sentiment en hausse → USD bullish.","below":"Sentiment en baisse → USD bearish."},
    "average hourly":{"neg":False,"above":"Salaires en hausse → inflation salariale → USD bullish.","below":"Salaires en baisse → USD bearish."},
    "employment change":{"neg":False,"above":"Plus d'emplois → bullish.","below":"Moins d'emplois → bearish."},
    "housing":{"neg":False,"above":"Construction en hausse → USD bullish.","below":"Construction en baisse → USD bearish."},
    "inflation":{"neg":False,"above":"Inflation élevée → hawkish → bullish.","below":"Inflation basse → dovish → bearish."},
}

def _kb(title):
    t = title.lower()
    for k,v in KB.items():
        if k in t: return v
    return None

def _num(v):
    if not v or v in ("","—","-"): return None
    v = str(v).strip().replace("%","").replace(",","")
    m = 1
    if v.upper().endswith("K"): m=1000;v=v[:-1]
    elif v.upper().endswith("M"): m=1000000;v=v[:-1]
    elif v.upper().endswith("B"): m=1000000000;v=v[:-1]
    try: return float(v)*m
    except: return None

def _sent(title, actual, forecast, previous):
    if not actual or actual in ("","—","-"): return "PENDING"
    act=_num(actual); fct=_num(forecast); prv=_num(previous)
    if act is None: return "NEUTRAL"
    kb=_kb(title); neg=kb["neg"] if kb else False
    if fct is not None and fct!=0:
        d=((act-fct)/abs(fct))*100
        if d>2: return "BEARISH" if neg else "BULLISH"
        if d<-2: return "BULLISH" if neg else "BEARISH"
        return "NEUTRAL"
    if prv is not None and prv!=0:
        d=((act-prv)/abs(prv))*100
        if d>2: return "BEARISH" if neg else "BULLISH"
        if d<-2: return "BULLISH" if neg else "BEARISH"
    return "NEUTRAL"

def _expl(title, actual, forecast, previous, currency):
    if not actual or actual in ("","—","-"): return None
    act=_num(actual); fct=_num(forecast); prv=_num(previous)
    kb=_kb(title); neg=kb["neg"] if kb else False
    if act is not None and fct is not None and fct!=0:
        diff=act-fct; pct=(diff/abs(fct))*100; sign="+" if diff>0 else ""
        if abs(pct)<=2: return f"Conforme au forecast ({actual} vs {forecast}). Pas de surprise → impact limité."
        beat=(diff>0) if not neg else (diff<0)
        head=f"Actual {actual} vs forecast {forecast} ({sign}{pct:.1f}%)"
        if kb: return f"{head} — {kb['above'] if beat else kb['below']}"
        return f"{head} — {'Mieux' if beat else 'Pire'} que prévu → {currency} {'bullish' if beat else 'bearish'}."
    if act is not None and prv is not None and prv!=0:
        diff=act-prv; pct=(diff/abs(prv))*100; sign="+" if diff>0 else ""
        improving=(diff>0) if not neg else (diff<0)
        head=f"Actual {actual} vs précédent {previous} ({sign}{pct:.1f}%)"
        if kb: return f"{head} — {kb['above'] if improving else kb['below']}"
        return head
    return f"Publié : {actual}."

def _score(events):
    s={}
    for e in events:
        c=e.get("currency",""); imp=e.get("impact","Low"); sent=e.get("sentiment","NEUTRAL")
        if not c: continue
        w={"High":3,"Medium":1.5,"Low":0.5}.get(imp,0.5)
        d={"BULLISH":w,"BEARISH":-w}.get(sent,0)
        if c not in s: s[c]={"score":0,"events":0,"high_impact":0}
        s[c]["score"]+=d; s[c]["events"]+=1
        if imp=="High": s[c]["high_impact"]+=1
    for c in s: s[c]["normalized"]=max(-100,min(100,s[c]["score"]*10))
    return s

def fetch_twelvedata():
    if not TD_API_KEY: print("  [ECO] Pas de clé Twelve Data"); return []
    print("  [ECO] SOURCE 1: Twelve Data Economic Calendar...")
    today=datetime.now()
    start=(today-timedelta(days=today.weekday()+7)).strftime("%Y-%m-%d")
    end=(today+timedelta(days=14-today.weekday())).strftime("%Y-%m-%d")
    try:
        r=requests.get("https://api.twelvedata.com/economic_calendar",
            params={"start_date":start,"end_date":end,"apikey":TD_API_KEY},
            headers={"User-Agent":"Mozilla/5.0"},timeout=20)
        if r.status_code!=200: print(f"  [ECO]   HTTP {r.status_code}"); return []
        data=r.json()
        if "code" in data and data["code"]!=200: print(f"  [ECO]   API: {data.get('message','')}"); return []
        raw=data.get("events",data.get("data",data if isinstance(data,list) else []))
        print(f"  [ECO]   {len(raw)} événements bruts Twelve Data")
        events=[]; seen=set()
        for item in raw:
            title=(item.get("event") or item.get("title") or "").strip()
            country=(item.get("country") or "").strip()
            currency=TD_COUNTRY.get(country, item.get("currency","").upper())
            if not title or not currency: continue
            date_raw=item.get("date",""); time_raw=item.get("time","")
            try:
                if "T" in date_raw:
                    dt=datetime.fromisoformat(date_raw.replace("Z","+00:00"))
                    df=dt.strftime("%a %b %d"); tf=dt.strftime("%H:%M")
                else:
                    dt=datetime.strptime(date_raw,"%Y-%m-%d")
                    df=dt.strftime("%a %b %d"); tf=time_raw[:5] if time_raw else ""
            except: df=date_raw[:10]; tf=time_raw[:5] if time_raw else ""
            key=f"{df}|{tf}|{title}|{currency}"
            if key in seen: continue
            seen.add(key)
            imp_raw=(item.get("impact") or item.get("importance") or "low").lower()
            imp={"high":"High","medium":"Medium","low":"Low"}.get(imp_raw,"Low")
            actual=str(item.get("actual","") or "").strip()
            forecast=str(item.get("estimate","") or item.get("forecast","") or "").strip()
            previous=str(item.get("previous","") or "").strip()
            events.append({"date":df,"time":tf,"currency":currency,"impact":imp,"title":title,
                "actual":actual,"forecast":forecast,"previous":previous,
                "sentiment":_sent(title,actual,forecast,previous),
                "impact_explanation":_expl(title,actual,forecast,previous,currency),
                "affected_symbols":CURRENCY_IMPACT.get(currency,[])})
        n=sum(1 for e in events if e["actual"])
        print(f"  [ECO]   → {len(events)} events, {n} avec actuals")
        return events
    except Exception as e: print(f"  [ECO]   Erreur: {e}"); return []

def fetch_faireconomy():
    print("  [ECO] SOURCE 2: faireconomy.media (fallback)...")
    events=[]; seen=set()
    for label,url in [("thisweek","https://nfs.faireconomy.media/ff_calendar_thisweek.json"),
                      ("lastweek","https://nfs.faireconomy.media/ff_calendar_lastweek.json")]:
        try:
            r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=15)
            if r.status_code!=200: print(f"  [ECO]   {label}: HTTP {r.status_code}"); continue
            for item in r.json():
                title=(item.get("title") or "").strip()
                currency=(item.get("country") or "").upper().strip()
                if not title or not currency: continue
                date_raw=item.get("date","")
                try: dt=datetime.fromisoformat(date_raw.replace("Z","+00:00")); df=dt.strftime("%a %b %d"); tf=dt.strftime("%H:%M")
                except: df=date_raw[:10]; tf=""
                key=f"{df}|{tf}|{title}|{currency}"
                if key in seen: continue
                seen.add(key)
                imp=(item.get("impact") or "").capitalize()
                if imp not in ("High","Medium","Low"): imp="Low"
                actual=(item.get("actual") or "").strip()
                forecast=(item.get("forecast") or "").strip()
                previous=(item.get("previous") or "").strip()
                events.append({"date":df,"time":tf,"currency":currency,"impact":imp,"title":title,
                    "actual":actual,"forecast":forecast,"previous":previous,
                    "sentiment":_sent(title,actual,forecast,previous),
                    "impact_explanation":_expl(title,actual,forecast,previous,currency),
                    "affected_symbols":CURRENCY_IMPACT.get(currency,[])})
        except Exception as e: print(f"  [ECO]   {label}: {e}")
    n=sum(1 for e in events if e["actual"])
    print(f"  [ECO]   {len(events)} events, {n} avec actuals")
    return events

def run():
    print("="*55); print("  ECO CALENDAR v5 — QuantDash"); print("="*55)
    events=fetch_twelvedata()
    if not events: events=fetch_faireconomy()
    if not events: print("  [ECO] Toutes sources échouées — calendrier vide"); events=[]
    n_publi=sum(1 for e in events if e.get("impact_explanation"))
    n_pend=sum(1 for e in events if e["sentiment"]=="PENDING")
    print(f"\n  {len(events)} events | {sum(1 for e in events if e['impact']=='High')} High | {n_publi} publiés | {n_pend} à venir")
    eco_scores=_score(events)
    os.makedirs(DATA_DIR,exist_ok=True)
    fp=os.path.join(DATA_DIR,"eco_data.json")
    with open(fp,"w",encoding="utf-8") as f:
        json.dump({"last_updated":datetime.now().isoformat(),"total_events":len(events),
            "high_impact_count":sum(1 for e in events if e["impact"]=="High"),
            "published_count":n_publi,"currency_scores":eco_scores,"events":events,
            "high_impact_events":[e for e in events if e["impact"]=="High"],
            "upcoming_events":[e for e in events if e["sentiment"]=="PENDING"][:15],
            "released_events":[e for e in events if e.get("impact_explanation")][:25]},f,indent=2,ensure_ascii=False)
    print(f"  [ECO] Sauvegardé → {fp}"); print("="*55)
    return events, eco_scores

if __name__=="__main__": run()
