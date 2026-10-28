import json, csv, math, re, sys, datetime as dt
W = sys.argv[1]
TODAY = sys.argv[2]
old = json.load(open(f'{W}/previous_fundamentals.json'))
OLD = {x['symbol']: x for x in old}
scan = {r['sym']: r for r in csv.DictReader(open(f'{W}/scan.csv'))}
def num(v):
    if v in (None, '', 'null'): return None
    return float(v)
fin = {}
for fn in ['fin1.txt','fin2.txt','fin3.txt','fin4.txt']:
    for line in open(f'{W}/{fn}'):
        p = line.split()
        if not p: continue
        fin.setdefault(p[0], []).append(dict(d=p[1], rev=num(p[2]), gp=num(p[3]), ni=num(p[4])))
rat = {}
for line in open(f'{W}/ratings.txt'):
    s,b,h,se,t = line.split(); rat[s] = (int(b),int(h),int(se),float(t))
clamp = lambda x,a,b: max(a,min(b,x))
def r(x,n):
    return None if x is None else round(x,n)
rows = []
for s, o in OLD.items():
    sc = scan[s]
    price = num(sc['last']); high = num(sc['high']); mcap = num(sc['mcap'])
    fpe = num(sc['fpe']); ccy = sc['ccy']
    model = o['model']
    F = fin.get(s)
    latest_q = None
    if F:
        q0 = F[0]; latest_q = q0['d']
        d0 = dt.date.fromisoformat(q0['d'])
        prev = None
        for q in F[1:]:
            if abs((d0 - dt.date.fromisoformat(q['d'])).days - 365) <= 40: prev = q
        g = (q0['rev']/prev['rev'] - 1) if (q0['rev'] and prev and prev['rev']) else None
        runrate = q0['rev']*4/1e9 if q0['rev'] is not None else None
        gm = q0['gp']/q0['rev'] if (q0['gp'] is not None and q0['rev']) else num(sc['gm'])
        last4 = [q for q in F[:4] if q['rev'] is not None and q['ni'] is not None]
        nmt = sum(q['ni'] for q in last4)/sum(q['rev'] for q in last4) if last4 and sum(q['rev'] for q in last4) else None
        nmq = q0['ni']/q0['rev'] if (q0['rev'] and q0['ni'] is not None) else None
        basis = 'quarterly'
    else:
        g = num(sc['g']); gm = num(sc['gm']); nmt = num(sc['nm']); nmq = nmt
        if ccy == 'USD':
            runrate = num(sc['ttm'])/1e9; basis = 'ttm'
        else:
            runrate = None; basis = 'n/a (non-USD reporting)'
    eps = price/fpe if (fpe is not None and 0 < fpe < 150) else None
    # Earnings lens
    E = None
    if eps is not None:
        if model == 'secular':
            gg = min(max(g or 0,0)*100,120); E = eps*clamp(15+0.25*gg,15,45)
        elif model == 'cyclical': E = eps*14
        elif model == 'memory':
            E = eps*0.55*14 if (nmq is not None and nmq > 0.35 and fpe < 10) else eps*16
        elif model == 'semicap':
            E = eps*clamp(15+0.2*min((g or 0)*100,120),16,28)
        elif model == 'ipp': E = eps*20
    # Sales lens
    S = None
    if model in ('secular','spec') and (eps is None or (nmq is not None and nmq < 0)) and s != 'LITE' \
       and not (gm is not None and gm < 0) and runrate:
        fps = (0.12*min(max(g or 0,0)*100,100)+2) * (math.sqrt(gm/0.5) if gm is not None else 0.7) * (1+clamp(nmq or 0,-0.3,0.3))
        if s in ('CRWV','NBIS','APLD','CORZ'): fps /= 2
        debt = 35e9 if s == 'CRWV' else 0
        S = price*max(fps*runrate*1e9 - debt, 0)/mcap
    b,h,se,A = rat.get(s,(None,None,None,None))
    lens = [(v,w) for v,w in ((E,.45),(S,.25),(A,.30)) if v is not None and v > 0]
    fv = sum(v*w for v,w in lens)/sum(w for v,w in lens) if lens else None
    conf = 'High' if (E and E>0 and A and A>0) else ('Medium' if len(lens)>=2 else 'Low')
    if ccy != 'USD' and conf == 'High': conf = 'Medium'
    off = price/high - 1
    # screen
    reasons = []
    meaningful = (runrate is not None and runrate >= 0.1) or (ccy != 'USD')
    if not meaningful or g is None:
        reasons.append('Pre-revenue or revenue too small to measure growth')
    elif g < 0.20:
        if abs(g) < 0.005: reasons.append('Revenue flat y/y, below the 20% bar')
        else:
            pct = g*100
            txt = f'{pct:+.1f}' if abs(pct-20) <= 1 else f'{pct:+.0f}'
            txt = txt.replace('-', '−')
            reasons.append(f'Revenue {txt}% y/y, below the 20% bar')
    if off > -0.25:
        reasons.append(f'only {round(-off*100):.0f}% off its high (needs 25%)')
    if gm is not None and gm < 0:
        reasons.append('negative gross margin, so the sales lens is undefined')
    if fv is None: reasons.append('no fair value available')
    passes = not reasons
    screen = 'Passes' if passes else '; '.join(reasons)
    screen = screen[0].upper() + screen[1:]
    row = dict(symbol=s, name=o['name'], ai=True, theme=o['theme'], model=model,
        model_note={'memory':'Memory/storage: valued on mid-cycle earnings, not the current peak.',
                    'semicap':'Semicap: P/E capped at 28x to reflect the equipment cycle.',
                    'cyclical':'Hardware/EMS: valued at a 14x cyclical multiple.',
                    'ipp':'Power producer: valued at 20x forward earnings.',
                    'spec':'Speculative: no meaningful earnings; valued on sales and street targets.',
                    'secular':''}[model],
        rev_growth=r(g,4), runrate_rev_b=r(runrate,3), gross_margin=r(gm,4), net_margin_ttm=r(nmt,4),
        latest_quarter=latest_q, high_52w=r(high,2), snapshot_price=r(price,2), snapshot_mcap_b=r(mcap/1e9,1),
        fwd_pe=r(fpe,2) if (fpe is not None and fpe < 150) else None, ntm_eps=r(eps,2),
        fair_earnings=r(E,2), fair_sales=r(S,2), analyst_target=r(A,2), analyst_buy=b, analyst_hold=h, analyst_sell=se,
        fair_value=r(fv,2), fair_low=r(min(v for v,_ in lens),2) if lens else None, fair_high=r(max(v for v,_ in lens),2) if lens else None,
        asof=TODAY, note=o['note'], segment=o['segment'], mag7=o['mag7'], nvda_eco=o['nvda_eco'], group=o['group'],
        lenses=len(lens), confidence=conf, rev_basis=basis, passes=passes, screen=screen)
    # note contradiction check
    n = o['note']; bad = []
    m = re.search(r'Revenue ([+−-]\d+)% y/y', n)
    if m and g is not None and abs(int(m.group(1).replace('−','-')) - g*100) > 2: bad.append('growth')
    m = re.search(r'(\d+)% below the (?:52-week )?high', n)
    if m and abs(int(m.group(1)) + off*100) > 3: bad.append('offhigh')
    m = re.search(r'(\d+) of (\d+) analysts', n)
    if m and b is not None and (int(m.group(1)) != b or int(m.group(2)) != b+h+se): bad.append('analysts')
    m = re.search(r'at ([\d.]+)x forward', n)
    if m and (fpe is None or abs(float(m.group(1)) - fpe) > 1.5): bad.append('pe')
    if bad:
        gtxt = (f'{g*100:+.0f}'.replace('-','−') + '% y/y in the latest quarter') if g is not None else 'growth not measurable'
        rr = f' (run-rate ${runrate:.1f}B)' if runrate is not None else ''
        nmtxt = f', with a {nmt*100:.0f}% trailing net margin'.replace('-','−') if nmt is not None else ''
        pe = f' at {fpe:.1f}x forward earnings' if (fpe and fpe < 150) else ''
        an = f'; {b} of {b+h+se} analysts rate it a buy' if b is not None else ''
        row['note'] = f'Revenue {gtxt}{rr}{nmtxt}. Shares are {-off*100:.0f}% below the 52-week high{pe}{an}.'
        row['_rewritten'] = bad
    rows.append(row)
rows.sort(key=lambda x: -(x['fair_value']/x['snapshot_price']) if x['fair_value'] else 0)
rew = [(x['symbol'], x.pop('_rewritten')) for x in rows if '_rewritten' in x]
json.dump(rows, open(f'{W}/fundamentals.json','w'), ensure_ascii=False, indent=1)
nos = [dict(symbol=x['symbol'], name=x['name'], segment=x['segment'], off_high=round(x['snapshot_price']/x['high_52w']-1,4), reason=x['screen']) for x in rows if not x['passes']]
nos.sort(key=lambda x: x['off_high'])
json.dump(nos, open(f'{W}/not_on_screen.json','w'), ensure_ascii=False, indent=1)
print('rewritten notes:', rew)
oldp = {s for s,x in OLD.items() if x['passes']}; newp = {x['symbol'] for x in rows if x['passes']}
print('started passing:', sorted(newp-oldp)); print('stopped passing:', sorted(oldp-newp))
for x in rows:
    if OLD[x['symbol']]['screen'] != x['screen'] : print('screen changed', x['symbol'], OLD[x['symbol']]['screen'], '->', x['screen'])
P = [x for x in rows if x['passes']]
print('top gaps:', [(x['symbol'], round(x['fair_value']/x['snapshot_price']-1,3)) for x in P[:5]])
import statistics
m7 = [x['fair_value']/x['snapshot_price']-1 for x in rows if x['mag7']]
print('mag7 median', statistics.median(m7), len(m7))
print('n', len(rows), 'pass', len(P), 'nos', len(nos))
# diff fair values vs old
for x in rows:
    ov = OLD[x['symbol']]['fair_value']
    if ov and x['fair_value'] and abs(x['fair_value']/ov-1) > 0.05: print('fv change', x['symbol'], ov, x['fair_value'])
    if (ov is None) != (x['fair_value'] is None): print('fv null change', x['symbol'])
