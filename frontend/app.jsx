// Trade-Claw — Live App with real backend integration

const { useState, useMemo, useEffect, useCallback, useRef } = React;

// ─── Atoms ─────────────────────────────────────────────────
const Icon = ({ name }) => <span dangerouslySetInnerHTML={{ __html: I[name] || '' }} />;
const Card = ({ title, action, children, style }) => (
  <div className="card" style={style}>
    {(title || action) && <div className="card-head"><div className="card-title">{title}</div>{action}</div>}
    {children}
  </div>
);
const Badge = ({ variant = 'neutral', children }) => <span className={`badge badge-${variant}`}>{children}</span>;
const Progress = ({ pct, variant = '' }) => (
  <div className="progress"><div className={`progress-fill ${variant}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} /></div>
);
const KvList = ({ items }) => (
  <table className="tbl" style={{ marginTop: 4 }}>
    <tbody>{items.map(([k, v]) => <tr key={k}><td className="t-label" style={{ width: '40%' }}>{k}</td><td className="t-mono">{v}</td></tr>)}</tbody>
  </table>
);

// ─── Toasts ────────────────────────────────────────────────
const ToastCtx = React.createContext({ push: () => {} });
function ToastHost({ children }) {
  const [list, setList] = useState([]);
  const push = useCallback((type, msg) => {
    const id = Math.random();
    setList(l => [...l, { id, type, msg }]);
    setTimeout(() => setList(l => l.filter(t => t.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 200, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {list.map(t => (
          <div key={t.id} className={`alert-banner alert-${t.type === 'error' ? 'critical' : t.type === 'warn' ? 'warn' : 'info'}`}
               style={{ minWidth: 280, boxShadow: 'var(--shadow-lg)' }}>
            <Icon name={t.type === 'error' ? 'alert' : t.type === 'success' ? 'check' : 'bell'}/>
            <div>{t.msg}</div>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
const useToast = () => React.useContext(ToastCtx);

// ─── Setup Modal ───────────────────────────────────────────
function SetupModal({ open, onClose, onDone }) {
  const toast = useToast();
  const [tab, setTab] = useState('config'); // config | new-session
  const [baseUrl, setBaseUrl] = useState(Config.baseUrl);
  const [apiKey, setApiKey] = useState(Config.apiKey);
  const [sessionId, setSessionId] = useState(Config.sessionId);
  const [healthy, setHealthy] = useState(null);
  const [busy, setBusy] = useState(false);

  // New session form
  const [brokerType, setBrokerType] = useState(Config.brokerType || 'mock');
  const [environment, setEnvironment] = useState(Config.environment || 'paper');
  const [credsJson, setCredsJson] = useState('{\n  "api_key": "your-key-here",\n  "secret_key": "..."\n}');

  const checkHealth = useCallback(async () => {
    Config.baseUrl = baseUrl;
    try { await Api.health(); setHealthy(true); }
    catch (e) { setHealthy(false); toast.push('error', `Health check failed: ${e.message}`); }
  }, [baseUrl, toast]);

  const save = () => {
    Config.baseUrl = baseUrl; Config.apiKey = apiKey; Config.sessionId = sessionId;
    toast.push('success', 'Konfiguration gespeichert');
    onDone();
  };

  const createSession = async () => {
    setBusy(true);
    try {
      Config.baseUrl = baseUrl; Config.apiKey = apiKey;
      let credentials;
      try { credentials = JSON.parse(credsJson); }
      catch { throw new Error('Credentials sind kein gültiges JSON'); }
      if (environment === 'live') {
        const ok = confirm(
          'WARNUNG: Live-Modus mit echtem Geld.\n\n' +
          'Bist du sicher? Dieser Account wird echte Orders ausführen.\n\n' +
          'OK = Live-Modus  ·  Abbrechen = zurück zu Paper'
        );
        if (!ok) { setBusy(false); return; }
      }
      const res = await Api.setupBroker({
        broker_type: brokerType,
        credentials,
        environment,
      });
      setSessionId(res.session_id);
      Config.sessionId = res.session_id;
      Config.brokerType = brokerType;
      Config.environment = environment;
      toast.push('success', `Session erstellt: ${res.session_id.slice(0, 8)}… (${environment})`);
      onDone();
    } catch (e) {
      toast.push('error', `Setup fehlgeschlagen: ${e.message}`);
    } finally { setBusy(false); }
  };

  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 640 }}>
        <div className="t-h3 mb-8">Backend Verbindung</div>
        <div className="t-body-sm text-muted mb-16">
          API-Key &amp; Session-ID werden in <span className="t-mono">localStorage</span> gespeichert.
        </div>

        <div className="tabs">
          <button className={`tab ${tab==='config'?'active':''}`} onClick={() => setTab('config')}>Bestehende Session</button>
          <button className={`tab ${tab==='new-session'?'active':''}`} onClick={() => setTab('new-session')}>Neue Session erstellen</button>
        </div>

        <div className="field-group mb-16">
          <label className="t-label">API Base URL</label>
          <div className="row gap-8">
            <input className="input mono" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} style={{ flex: 1 }} />
            <button className="btn btn-secondary btn-sm" onClick={checkHealth}>Health</button>
          </div>
          {healthy === true && <div className="t-body-sm text-success">✓ Backend erreichbar</div>}
          {healthy === false && <div className="t-body-sm text-danger">✕ Nicht erreichbar — CORS gesetzt?</div>}
        </div>

        <div className="field-group mb-16">
          <label className="t-label">API Key (X-API-Key Header)</label>
          <input className="input mono" type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="dein-api-key" />
        </div>

        {tab === 'config' && (
          <>
            <div className="field-group mb-16">
              <label className="t-label">Session ID</label>
              <input className="input mono" value={sessionId} onChange={e => setSessionId(e.target.value)} placeholder="abc-123-..." />
            </div>
            <div className="row gap-8">
              <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Abbrechen</button>
              <button className="btn btn-primary" style={{ flex: 2 }} onClick={save} disabled={!apiKey || !sessionId}>Speichern &amp; Verbinden</button>
            </div>
          </>
        )}

        {tab === 'new-session' && (
          <>
            <div className="field-group mb-16">
              <label className="t-label">Broker</label>
              <select className="select" value={brokerType} onChange={e => setBrokerType(e.target.value)}>
                <option value="mock">Mock (Testing)</option>
                <option value="alpaca">Alpaca</option>
                <option value="oanda">OANDA</option>
                <option value="hyperliquid">Hyperliquid</option>
              </select>
            </div>

            <div className="field-group mb-16">
              <label className="t-label">Modus</label>
              <div className="row" style={{ gap: 8 }}>
                {[
                  ['paper', 'Paper / Demo', 'Sandbox · kein echtes Geld'],
                  ['live',  'Live · echtes Geld', 'Order-Routing an realen Account'],
                ].map(([k, l, sub]) => (
                  <button key={k} type="button" onClick={() => setEnvironment(k)}
                    className={`btn ${environment===k ? (k==='live'?'btn-danger':'btn-primary') : 'btn-secondary'}`}
                    style={{ flex: 1, textAlign: 'left', padding: '10px 12px' }}>
                    <div><b>{l}</b></div>
                    <div className="t-body-sm" style={{ opacity: 0.85 }}>{sub}</div>
                  </button>
                ))}
              </div>
              {environment === 'live' && (
                <div className="alert-banner alert-warn mt-8">
                  <Icon name="alert"/>
                  <div>
                    <b>Live-Modus aktiv.</b> Orders gehen mit echten Mitteln raus. Du bekommst nochmal eine Bestätigung beim Setup.
                  </div>
                </div>
              )}
            </div>

            {brokerType !== 'mock' && (
              <div className="alert-banner alert-info mb-16">
                <Icon name="bell"/>
                <div>
                  <div><b>Hinweis zu Credentials:</b></div>
                  {brokerType === 'hyperliquid' && (
                    <div className="t-body-sm">{`{ "api_key": "<wallet 0x…>", "secret_key": "<eth privkey>" }`}</div>
                  )}
                  {brokerType === 'alpaca' && (
                    <div className="t-body-sm">{`{ "api_key": "<key>", "secret_key": "<secret>" }`}</div>
                  )}
                  {brokerType === 'oanda' && (
                    <div className="t-body-sm">{`{ "api_key": "<token>", "account_id": "<acct>" }`}</div>
                  )}
                </div>
              </div>
            )}

            <div className="field-group mb-16">
              <label className="t-label">Credentials (JSON)</label>
              <textarea className="input mono" rows={5} value={credsJson} onChange={e => setCredsJson(e.target.value)} style={{ resize: 'vertical' }} />
            </div>
            <div className="row gap-8">
              <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Abbrechen</button>
              <button className={`btn ${environment==='live' ? 'btn-danger' : 'btn-primary'}`} style={{ flex: 2 }} onClick={createSession} disabled={busy || !apiKey}>
                {busy ? 'Verbinde…' : `Session erstellen (${environment})`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Live Data Hook ────────────────────────────────────────
function useLiveData() {
  const [positions, setPositions] = useState({ positions: [], total_unrealized_pnl: '0', drawdown_pct: '0', is_halted: false });
  const [audit, setAudit] = useState({ logs: [], total_count: 0 });
  const [risk, setRisk] = useState(null);
  const [errors, setErrors] = useState({});
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    if (!Config.isReady()) return;
    const stops = [
      makePoller(() => Api.getPositions(), {
        interval: 5000,
        onData: d => { setPositions(d); setLastUpdate(new Date()); setErrors(e => ({ ...e, positions: null })); },
        onError: e => setErrors(er => ({ ...er, positions: e.message })),
      }),
      makePoller(() => Api.getAudit({ limit: 20 }), {
        interval: 8000,
        onData: d => setAudit(d),
        onError: e => setErrors(er => ({ ...er, audit: e.message })),
      }),
      makePoller(() => Api.riskStatus(), {
        interval: 10000,
        onData: d => setRisk(d),
        onError: () => {},
      }),
    ];
    return () => stops.forEach(s => s());
  }, []);

  return { positions, audit, risk, errors, lastUpdate };
}

// ─── Helpers ───────────────────────────────────────────────
const num = v => Number(v ?? 0);
const fmtMoney = v => {
  const n = num(v); const sign = n >= 0 ? '+' : '−';
  return `${sign}$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
};
const pnlClass = n => num(n) > 0 ? 'text-success' : num(n) < 0 ? 'text-danger' : 'text-muted';

// ─── Dashboard ─────────────────────────────────────────────
function Dashboard({ live, onHalt, onNav }) {
  const { positions, lastUpdate, errors } = live;
  const total = num(positions.total_unrealized_pnl);
  const dd = num(positions.drawdown_pct);
  const ddPct = Math.abs(dd) / 15 * 100;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">ÜBERSICHT</div>
          <h1 className="t-h1">Dashboard</h1>
        </div>
        <div className="row">
          <div className="timestamp">{lastUpdate ? `Live · ${lastUpdate.toLocaleTimeString('de-DE')}` : 'Verbinde…'}</div>
        </div>
      </div>

      {errors.positions && (
        <div className="alert-banner alert-critical mb-16">
          <Icon name="alert"/><div><b>API Fehler</b> — {errors.positions}</div>
        </div>
      )}
      {positions.is_halted && (
        <div className="alert-banner alert-critical mb-16">
          <Icon name="lock"/><div><b>SYSTEM HALTED</b> — Risk-Engine hat den Trading-Stop ausgelöst.</div>
        </div>
      )}
      {Math.abs(dd) >= 12 && !positions.is_halted && (
        <div className="alert-banner alert-warn mb-16">
          <Icon name="alert"/><div><b>DRAWDOWN ALERT</b> — Aktuell {dd.toFixed(2)}% (Limit −15%)</div>
        </div>
      )}

      <div className="kpi-grid mb-16">
        <KpiCard label="Unrealized P&L" value={fmtMoney(total)} cls={total >= 0 ? 'up' : 'down'} valCls={pnlClass(total)} meta={`${positions.positions.length} offene Positionen`} />
        <KpiCard label="Drawdown" value={`${dd.toFixed(2)}%`} cls={Math.abs(dd) >= 12 ? 'down' : 'neutral'} valCls={Math.abs(dd) >= 12 ? 'text-warning' : ''} meta="Limit: −15%" />
        <KpiCard label="Risk Status" value={positions.is_halted ? 'HALTED' : 'AKTIV'} cls={positions.is_halted ? 'down' : 'up'} valCls={positions.is_halted ? 'text-danger' : 'text-success'} meta="Backend Risk Engine" />
        <KpiCard label="Backend" value="ONLINE" cls="up" valCls="text-success" meta={Config.baseUrl.replace(/^https?:\/\//, '')} />
      </div>

      <div className="grid mb-16" style={{ gridTemplateColumns: '1.4fr 1fr' }}>
        <Card title="Risiko-Status" action={<span className="t-label">Live</span>}>
          <div className="risk-row">
            <div className="risk-head">
              <div className="risk-name">Drawdown</div>
              <div className="risk-stat"><span className={Math.abs(dd) >= 12 ? 'text-warning' : 'text-success'}>{dd.toFixed(2)}%</span> <span className="text-faint">/ −15.0%</span></div>
            </div>
            <Progress pct={ddPct} variant={ddPct > 80 ? 'warn' : ddPct > 50 ? '' : 'success'} />
            <div className="t-body-sm text-muted">Recovery benötigt: {fmtMoney(-total)}</div>
          </div>
          <div className="risk-row">
            <div className="risk-head">
              <div className="risk-name">Halted Status</div>
              <div className="risk-stat">{positions.is_halted ? <span className="text-danger">JA</span> : <span className="text-success">Nein</span>}</div>
            </div>
            <Progress pct={positions.is_halted ? 100 : 0} variant={positions.is_halted ? 'danger' : 'success'} />
            <div className="t-body-sm text-muted">Aus <span className="t-mono">/api/v1/positions</span></div>
          </div>
        </Card>

        <Card title="Notfall-Steuerung">
          <button className="halt-btn" onClick={onHalt}>
            <span className="pulse-ring"></span><Icon name="halt"/>EMERGENCY HALT
          </button>
          <div className="t-body-sm text-muted mt-8">Schließt alle {positions.positions.length} offenen Positionen via Cancel-Order Endpoint.</div>
          <div className="col gap-8 mt-16">
            <button className="btn btn-primary" onClick={() => onNav('trade')}><Icon name="zap"/> Neuer Trade</button>
            <button className="btn btn-secondary" onClick={() => onNav('analytics')}><Icon name="analytics"/> Analytics</button>
          </div>
        </Card>
      </div>

      <Card title={`Offene Positionen (${positions.positions.length})`}>
        {positions.positions.length === 0 ? (
          <div className="t-body text-muted" style={{ padding: '24px 0', textAlign: 'center' }}>
            Keine offenen Positionen.
          </div>
        ) : (
          <div style={{ margin: '0 -20px' }}>
            <div className="position-row" style={{ borderBottom: '1px solid var(--neutral-700)' }}>
              <div className="t-label">Symbol</div>
              <div className="t-label">Side</div>
              <div className="t-label">Preise</div>
              <div className="t-label">Size</div>
              <div className="t-label" style={{ textAlign: 'right' }}>P&amp;L</div>
              <div className="t-label" style={{ textAlign: 'right' }}>%</div>
            </div>
            {positions.positions.map((p, i) => (
              <div key={i} className="position-row">
                <div className="pair">{p.symbol}</div>
                <div><span className={`dir ${p.side.toLowerCase()}`}>{p.side}</span></div>
                <div className="price-block">
                  <div><div className="lbl">Entry</div><div className="val">{p.entry_price}</div></div>
                  <div><div className="lbl">Aktuell</div><div className="val">{p.current_price}</div></div>
                </div>
                <div><span className="t-mono">{p.size}</span></div>
                <div className={`pnl ${pnlClass(p.unrealized_pnl)}`}>{fmtMoney(p.unrealized_pnl)}</div>
                <div className={`t-mono ${pnlClass(p.pnl_pct)}`} style={{ textAlign: 'right' }}>{num(p.pnl_pct).toFixed(2)}%</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

const KpiCard = ({ label, value, meta, cls, valCls = '' }) => (
  <div className={`kpi ${cls}`}>
    <div className="kpi-label">{label}</div>
    <div className={`kpi-value ${valCls}`}>{value}</div>
    <div className="kpi-meta">{meta}</div>
  </div>
);

// ─── Trading Console ───────────────────────────────────────
function TradingConsole({ live }) {
  const toast = useToast();
  const [symbol, setSymbol] = useState('EUR_USD');
  const [side, setSide] = useState('BUY');
  const [size, setSize] = useState('1000');
  const [entry, setEntry] = useState('1.0842');
  const [sl, setSl] = useState('1.0815');
  const [tp, setTp] = useState('1.0890');
  const [quote, setQuote] = useState(null);
  const [validation, setValidation] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState('entry');

  const fetchQuote = async () => {
    try { const q = await Api.getQuote(symbol, size); setQuote(q); setEntry(String(q.ask)); }
    catch (e) { toast.push('error', `Quote fehlgeschlagen: ${e.message}`); }
  };

  const runPreCheck = async () => {
    try {
      const total = num(live.positions.total_unrealized_pnl);
      const equity = 50000 + total;
      const res = await Api.preTradeCheck({
        symbol, side, quantity: parseFloat(size),
        entry_price: parseFloat(entry), stop_loss: parseFloat(sl), take_profit: parseFloat(tp),
        account_equity: equity,
      });
      setValidation(res);
    } catch (e) { toast.push('error', `Pre-Trade Check: ${e.message}`); }
  };

  const submit = async () => {
    setBusy(true);
    try {
      const res = await Api.submitOrder({
        symbol, side,
        size: parseFloat(size), entry_price: parseFloat(entry),
        stop_loss: parseFloat(sl), take_profit: parseFloat(tp),
        idempotency_key: uuid(),
      });
      toast.push('success', `Order ${res.order_id} ausgeführt — R/R ${res.risk_ratio || '—'}`);
    } catch (e) {
      toast.push('error', `Order abgelehnt: ${e.message}`);
    } finally { setBusy(false); }
  };

  const eN = parseFloat(entry), sN = parseFloat(sl), tN = parseFloat(tp);
  const riskPips = Math.abs(eN - sN) * 10000;
  const rewardPips = Math.abs(tN - eN) * 10000;
  const rr = rewardPips / Math.max(0.0001, riskPips);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">TRADING</div>
          <h1 className="t-h1">Trading Console</h1>
        </div>
        <Badge variant="info"><span className="dot live" style={{ marginRight: 4 }}></span> Session {Config.sessionId.slice(0, 8)}…</Badge>
      </div>

      <Card title="Trade Entry" action={<button className="btn btn-secondary btn-sm" onClick={fetchQuote}><Icon name="refresh"/> Live Quote</button>}>
        <div className="tabs">
          {[['entry','Entry'],['risk','Risk Check'],['confirm','Confirm']].map(([k,l]) => (
            <button key={k} className={`tab ${tab===k?'active':''}`} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>

        {tab === 'entry' && (
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="field-group">
              <label className="t-label">Symbol (z.B. EUR_USD, BTC_USD)</label>
              <input className="input mono" value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} />
              {quote && <div className="field-hint">Bid: {quote.bid} · Ask: {quote.ask} · Last: {quote.last}</div>}
            </div>
            <div className="field-group">
              <label className="t-label">Direction</label>
              <div className="row" style={{ gap: 8 }}>
                {['BUY','SELL'].map(d => (
                  <button key={d} onClick={() => setSide(d)}
                    className={`btn ${side===d ? (d==='BUY'?'btn-primary':'btn-danger') : 'btn-secondary'}`}
                    style={{ flex: 1 }}>
                    <Icon name={d==='BUY'?'arrowUp':'arrowDown'}/> {d}
                  </button>
                ))}
              </div>
            </div>
            <div className="field-group">
              <label className="t-label">Size (Units)</label>
              <input className="input mono" value={size} onChange={e => setSize(e.target.value)} />
            </div>
            <div className="field-group">
              <label className="t-label">Entry Price</label>
              <input className="input mono" value={entry} onChange={e => setEntry(e.target.value)} />
            </div>
            <div className="field-group">
              <label className="t-label">Stop Loss</label>
              <input className="input mono" value={sl} onChange={e => setSl(e.target.value)} />
              <div className="field-hint text-danger">Risk: {riskPips.toFixed(1)} pips</div>
            </div>
            <div className="field-group">
              <label className="t-label">Take Profit</label>
              <input className="input mono" value={tp} onChange={e => setTp(e.target.value)} />
              <div className="field-hint text-success">Reward: {rewardPips.toFixed(1)} pips · R/R 1:{rr.toFixed(2)}</div>
            </div>
          </div>
        )}

        {tab === 'risk' && (
          <div className="col gap-12">
            <button className="btn btn-secondary" onClick={runPreCheck}>Pre-Trade Check ausführen</button>
            {validation && (
              <div className={`alert-banner ${validation.approved ? 'alert-info' : 'alert-critical'}`}>
                <Icon name={validation.approved ? 'check' : 'alert'}/>
                <div>
                  <b>{validation.approved ? 'APPROVED' : 'REJECTED'}</b>
                  <pre style={{ fontSize: 11, marginTop: 8, fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(validation.details, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'confirm' && (
          <div className="col gap-16">
            <KvList items={[
              ['Symbol', symbol], ['Side', side], ['Size', size],
              ['Entry', entry], ['Stop Loss', sl], ['Take Profit', tp],
              ['Risk / Reward', `1 : ${rr.toFixed(2)}`],
              ['Session', Config.sessionId.slice(0,12) + '…'],
            ]}/>
            <button className="btn btn-primary" onClick={submit} disabled={busy}>
              <Icon name="zap"/> {busy ? 'Sende Order…' : 'Order ausführen (POST /api/v1/orders/submit)'}
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── Risk Management ───────────────────────────────────────
function RiskManagement({ live, onHalt }) {
  const { positions, audit, risk } = live;
  const dd = num(positions.drawdown_pct);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">SAFETY</div>
          <h1 className="t-h1">Risk Management</h1>
        </div>
        <Badge variant={positions.is_halted ? 'danger' : 'success'}>
          {positions.is_halted ? 'HALTED' : 'ACTIVE'}
        </Badge>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1.5fr 1fr' }}>
        <Card title="Hard Limits (vom Backend)">
          <HardLimitRow name="Drawdown" cur={`${dd.toFixed(2)}%`} lim="−15%"
            pct={Math.abs(dd)/15*100}
            status={Math.abs(dd) >= 13 ? 'crit' : Math.abs(dd) >= 10 ? 'warn' : 'safe'}
            variant={Math.abs(dd) >= 13 ? 'danger' : Math.abs(dd) >= 10 ? 'warn' : 'success'} />
          <HardLimitRow name="Halted" cur={positions.is_halted ? 'JA' : 'Nein'} lim="—" pct={positions.is_halted ? 100 : 0}
            status={positions.is_halted ? 'crit' : 'safe'} variant={positions.is_halted ? 'danger' : 'success'} />
          <HardLimitRow name="Offene Positionen" cur={positions.positions.length} lim="∞" pct={Math.min(100, positions.positions.length * 10)}
            status="safe" />
          {risk && (
            <div className="alert-banner alert-info mt-16">
              <Icon name="check"/>
              <div className="t-mono" style={{ fontSize: 11 }}>{JSON.stringify(risk, null, 2)}</div>
            </div>
          )}
        </Card>

        <Card title="Emergency Controls">
          <button className="halt-btn" onClick={onHalt}>
            <span className="pulse-ring"></span><Icon name="halt"/>EMERGENCY HALT
          </button>
          <div className="t-body-sm text-muted mt-8">Cancelt alle offenen Orders via Backend.</div>
        </Card>
      </div>

      <Card title="Audit Log (Live)" style={{ marginTop: 16 }} action={<Badge variant="neutral">{audit.total_count} Einträge gesamt</Badge>}>
        {audit.logs.length === 0 ? (
          <div className="t-body text-muted">Keine Einträge.</div>
        ) : (
          <div className="col" style={{ gap: 0 }}>
            {audit.logs.map(a => (
              <div key={a.id} className="row gap-12" style={{ padding: '10px 0', borderBottom: '1px solid var(--neutral-700)' }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', flexShrink: 0, marginTop: 6,
                  background: a.severity === 'CRITICAL' || a.severity === 'ERROR' ? 'var(--danger-500)' :
                              a.severity === 'WARNING' ? 'var(--warning-500)' : 'var(--primary-500)' }} />
                <div style={{ flex: 1 }}>
                  <div className="t-body"><b>{a.action}</b> {a.symbol && <span className="t-mono">· {a.symbol}</span>}</div>
                  <div className="t-body-sm text-faint">{a.details}</div>
                </div>
                <div className="t-body-sm text-faint" style={{ whiteSpace: 'nowrap' }}>
                  {new Date(a.timestamp).toLocaleString('de-DE')}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

const HardLimitRow = ({ name, cur, lim, pct, status, variant }) => (
  <div className="risk-row">
    <div className="risk-head">
      <div className="row gap-12">
        <div className="risk-name">{name}</div>
        <Badge variant={status === 'safe' ? 'success' : status === 'warn' ? 'warning' : 'danger'}>
          {status === 'safe' ? 'SAFE' : status === 'warn' ? 'WARNING' : 'CRITICAL'}
        </Badge>
      </div>
      <div className="risk-stat"><span className="t-mono">{cur}</span> <span className="text-faint">/ {lim}</span></div>
    </div>
    <Progress pct={pct} variant={variant} />
  </div>
);

// ─── Audit Page (full history) ─────────────────────────────
function AuditPage() {
  const toast = useToast();
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState({ action: '', severity: '', limit: 100 });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const res = await Api.getAudit({
        action: filter.action || undefined,
        severity: filter.severity || undefined,
        limit: filter.limit,
      });
      setLogs(res.logs); setTotal(res.total_count);
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  }, [filter, toast]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">PERFORMANCE</div>
          <h1 className="t-h1">Audit & History</h1>
        </div>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div className="row gap-12" style={{ flexWrap: 'wrap' }}>
          <div className="field-group" style={{ flex: 1, minWidth: 160 }}>
            <label className="t-label">Action</label>
            <select className="select" value={filter.action} onChange={e => setFilter(f => ({ ...f, action: e.target.value }))}>
              <option value="">Alle</option>
              <option>ORDER_SUBMITTED</option><option>ORDER_REJECTED</option>
              <option>ORDER_CANCELLED</option><option>ORDER_FILLED</option>
              <option>SESSION_CREATED</option><option>SESSION_CLOSED</option>
              <option>RISK_BREACH</option>
            </select>
          </div>
          <div className="field-group" style={{ flex: 1, minWidth: 140 }}>
            <label className="t-label">Severity</label>
            <select className="select" value={filter.severity} onChange={e => setFilter(f => ({ ...f, severity: e.target.value }))}>
              <option value="">Alle</option><option>INFO</option><option>WARNING</option>
              <option>ERROR</option><option>CRITICAL</option>
            </select>
          </div>
          <div className="field-group" style={{ flex: 1, minWidth: 100 }}>
            <label className="t-label">Limit</label>
            <input className="input mono" type="number" value={filter.limit}
                   onChange={e => setFilter(f => ({ ...f, limit: parseInt(e.target.value) || 100 }))}/>
          </div>
          <button className="btn btn-secondary" style={{ alignSelf: 'flex-end' }} onClick={load} disabled={busy}>
            <Icon name="refresh"/> {busy ? 'Lade…' : 'Aktualisieren'}
          </button>
        </div>
      </Card>

      <Card title={`Audit Trail · ${logs.length} von ${total}`}>
        {logs.length === 0 ? (
          <div className="t-body text-muted" style={{ padding: '24px 0', textAlign: 'center' }}>Keine Einträge.</div>
        ) : (
          <div style={{ overflowX: 'auto', margin: '0 -20px' }}>
            <table className="tbl">
              <thead><tr>
                <th style={{ paddingLeft: 20 }}>ID</th><th>Action</th><th>Symbol</th>
                <th>Details</th><th>Severity</th><th>Timestamp</th>
              </tr></thead>
              <tbody>
                {logs.map(l => (
                  <tr key={l.id}>
                    <td style={{ paddingLeft: 20 }} className="t-mono text-faint">#{l.id}</td>
                    <td><b>{l.action}</b></td>
                    <td className="t-mono">{l.symbol || '—'}</td>
                    <td className="t-body-sm">{l.details}</td>
                    <td><Badge variant={l.severity === 'CRITICAL' || l.severity === 'ERROR' ? 'danger' : l.severity === 'WARNING' ? 'warning' : 'info'}>{l.severity}</Badge></td>
                    <td className="t-body-sm text-faint" style={{ whiteSpace: 'nowrap' }}>{new Date(l.timestamp).toLocaleString('de-DE')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── Correlation Page ──────────────────────────────────────
function CorrelationPage() {
  const toast = useToast();
  const [assets, setAssets] = useState({});
  const [selected, setSelected] = useState(['BTC', 'ETH', 'SPY']);
  const [threshold, setThreshold] = useState(0.7);
  const [pricesText, setPricesText] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Api.correlationAssets()
      .then(d => setAssets(d.assets || {}))
      .catch(e => toast.push('error', `Assets laden: ${e.message}`));
  }, [toast]);

  // Generate a synthetic price series so the user can demo without uploading data
  const seedDemoPrices = () => {
    const days = 30;
    const obj = {};
    selected.forEach((sym, idx) => {
      const seed = sym.split('').reduce((s, c) => s + c.charCodeAt(0), 0) + idx;
      const series = [];
      let p = 100 + (seed % 50);
      for (let i = 0; i < days; i++) {
        p += (Math.sin((i + seed) / 3) + (Math.random() - 0.5)) * 1.5;
        series.push(+p.toFixed(2));
      }
      obj[sym] = series;
    });
    setPricesText(JSON.stringify(obj, null, 2));
  };

  const analyze = async () => {
    setBusy(true);
    try {
      let asset_prices;
      try { asset_prices = JSON.parse(pricesText); }
      catch { throw new Error('Preisdaten sind kein gültiges JSON'); }
      const r = await Api.correlationAnalyze({ asset_prices, threshold });
      setResult(r);
    } catch (e) {
      toast.push('error', e.message);
    } finally { setBusy(false); }
  };

  const toggleAsset = sym => setSelected(s => s.includes(sym) ? s.filter(x => x !== sym) : [...s, sym]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">ANALYSE</div>
          <h1 className="t-h1">Correlation Engine</h1>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1.1fr 1fr', gap: 16 }}>
        <Card title="Assets auswählen">
          <div className="t-body-sm text-muted mb-8">{selected.length} ausgewählt — min 2, max 10</div>
          <div className="row" style={{ flexWrap: 'wrap', gap: 6 }}>
            {Object.entries(assets).map(([sym, meta]) => (
              <button key={sym} type="button" onClick={() => toggleAsset(sym)}
                className={`btn btn-sm ${selected.includes(sym) ? 'btn-primary' : 'btn-secondary'}`}
                title={`${meta.name} · ${meta.type}`}>
                {sym}
              </button>
            ))}
          </div>
          <div className="row gap-8 mt-16">
            <button className="btn btn-secondary btn-sm" onClick={seedDemoPrices}>Demo-Preise generieren</button>
            <div className="field-group" style={{ flex: 1 }}>
              <label className="t-label">Schwelle ({threshold.toFixed(2)})</label>
              <input type="range" min="0" max="1" step="0.05" value={threshold}
                onChange={e => setThreshold(parseFloat(e.target.value))} />
            </div>
          </div>
        </Card>

        <Card title="Preisdaten (JSON · time-aligned arrays)">
          <textarea className="input mono" rows={10} value={pricesText}
            onChange={e => setPricesText(e.target.value)}
            placeholder='{"BTC": [100,101,...], "ETH": [...]}'
            style={{ resize: 'vertical', width: '100%' }}/>
          <button className="btn btn-primary mt-8" onClick={analyze} disabled={busy || !pricesText}>
            <Icon name="analytics"/> {busy ? 'Analysiere…' : 'Korrelation berechnen'}
          </button>
        </Card>
      </div>

      {result && (
        <Card title="Ergebnis" style={{ marginTop: 16 }}>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12 }}>
            <KpiCard label="Avg Correlation" value={result.avg_correlation?.toFixed(3)} cls={result.trade_eligible ? 'up' : 'down'} valCls={result.trade_eligible ? 'text-success' : 'text-warning'} meta={`Schwelle ${result.threshold}`} />
            <KpiCard label="High Pairs" value={result.high_correlation_pairs ?? '—'} cls="neutral" meta={`> ${result.threshold}`} />
            <KpiCard label="Low Pairs" value={result.low_correlation_pairs ?? '—'} cls="neutral" meta={`< -${result.threshold}`} />
            <KpiCard label="Trade Eligible" value={result.trade_eligible ? 'JA' : 'NEIN'} cls={result.trade_eligible ? 'up' : 'down'} valCls={result.trade_eligible ? 'text-success' : 'text-danger'} meta="Backend-Empfehlung" />
          </div>
          <div className="alert-banner alert-info mt-16">
            <Icon name="bell"/><div>{result.reasoning}</div>
          </div>
          <div className="t-label mt-16 mb-8">Pairwise</div>
          <table className="tbl">
            <thead><tr><th>Pair</th><th style={{ textAlign: 'right' }}>Correlation</th></tr></thead>
            <tbody>
              {Object.entries(result.correlation_matrix || {}).map(([p, c]) => (
                <tr key={p}>
                  <td className="t-mono">{p}</td>
                  <td className={`t-mono ${c >= result.threshold ? 'text-success' : c <= -result.threshold ? 'text-danger' : 'text-muted'}`} style={{ textAlign: 'right' }}>{c.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

// ─── Macro Page ────────────────────────────────────────────
function MacroPage() {
  const toast = useToast();
  const [events, setEvents] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [category, setCategory] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [a, b] = await Promise.all([
        Api.macroEvents({ category: category || undefined, limit: 50 }),
        Api.macroUpcoming({ hours: 168 }),
      ]);
      setEvents(a.events || []);
      setUpcoming(b.events || []);
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  }, [category, toast]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">CONTEXT</div>
          <h1 className="t-h1">Macro Events</h1>
        </div>
      </div>

      <Card title={`Anstehend (${upcoming.length}) · nächste 7 Tage`} style={{ marginBottom: 16 }}>
        {upcoming.length === 0 ? (
          <div className="t-body text-muted">Keine bevorstehenden Events.</div>
        ) : (
          <div style={{ overflowX: 'auto', margin: '0 -20px' }}>
            <table className="tbl">
              <thead><tr>
                <th style={{ paddingLeft: 20 }}>Wann</th><th>Event</th><th>Kategorie</th>
                <th>Impact</th><th>Score</th><th>Affects</th>
              </tr></thead>
              <tbody>
                {upcoming.map(e => (
                  <tr key={e.event_id}>
                    <td style={{ paddingLeft: 20 }} className="t-body-sm">{new Date(e.timestamp).toLocaleString('de-DE')}</td>
                    <td><b>{e.title}</b></td>
                    <td><Badge variant="neutral">{e.category}</Badge></td>
                    <td><Badge variant={e.impact === 'Critical' ? 'danger' : e.impact === 'High' ? 'warning' : 'info'}>{e.impact}</Badge></td>
                    <td className="t-mono">{e.score?.toFixed?.(0) ?? '—'}</td>
                    <td className="t-body-sm text-muted">{(e.assets_affected || []).join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title={`Historisch · ${events.length}`} action={
        <div className="row gap-8">
          <select className="select" value={category} onChange={e => setCategory(e.target.value)}>
            <option value="">Alle Kategorien</option>
            <option value="Monetary Policy">Monetary Policy</option>
            <option value="Fiscal Policy">Fiscal Policy</option>
            <option value="Geopolitical">Geopolitical</option>
            <option value="Economic Data">Economic Data</option>
            <option value="On-Chain">On-Chain</option>
          </select>
          <button className="btn btn-secondary btn-sm" onClick={load} disabled={busy}><Icon name="refresh"/> Reload</button>
        </div>
      }>
        {events.length === 0 ? (
          <div className="t-body text-muted">Keine Events.</div>
        ) : (
          <div style={{ overflowX: 'auto', margin: '0 -20px' }}>
            <table className="tbl">
              <thead><tr>
                <th style={{ paddingLeft: 20 }}>Datum</th><th>Event</th><th>Kategorie</th>
                <th>Impact</th><th>Direction</th><th>Score</th>
              </tr></thead>
              <tbody>
                {events.map(e => (
                  <tr key={e.event_id}>
                    <td style={{ paddingLeft: 20 }} className="t-body-sm">{new Date(e.timestamp).toLocaleDateString('de-DE')}</td>
                    <td><b>{e.title}</b><div className="t-body-sm text-faint">{e.description}</div></td>
                    <td><Badge variant="neutral">{e.category}</Badge></td>
                    <td><Badge variant={e.impact === 'Critical' ? 'danger' : e.impact === 'High' ? 'warning' : 'info'}>{e.impact}</Badge></td>
                    <td className={e.direction === 'Bullish' ? 'text-success' : e.direction === 'Bearish' ? 'text-danger' : 'text-muted'}>{e.direction}</td>
                    <td className="t-mono">{e.score?.toFixed?.(0) ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── Grader Page (7-Criteria Setup Quality) ────────────────
function GraderPage() {
  const toast = useToast();
  const [form, setForm] = useState({
    symbol: 'BTC', direction: 'LONG',
    entry_price: 42000, stop_loss_price: 40000, tp1_price: 45000, tp2_price: 48000,
    confidence: 70, risk_percent: 2, drawdown_stage: 1,
  });
  const [criteria, setCriteria] = useState({
    structural_level: true, liquidity_sweep: false, momentum: true,
    volume: true, risk_reward: true, macro_alignment: false, no_contradiction: true,
  });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const upd = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const updNum = k => e => upd(k, parseFloat(e.target.value) || 0);

  const submit = async () => {
    setBusy(true);
    try {
      const r = await Api.gradeSetup({ ...form, criteria });
      setResult(r);
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  };

  const labels = {
    structural_level: 'Structural Level (Support/Resistance)',
    liquidity_sweep:  'Liquidity Sweep bestätigt',
    momentum:         'Momentum bestätigt',
    volume:           'Volume bestätigt',
    risk_reward:      'R/R ≥ 1:3 (HARD GATE)',
    macro_alignment:  'Macro Environment aligned',
    no_contradiction: 'Keine Contradiction (On-Chain/Tech)',
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">QUALITY</div>
          <h1 className="t-h1">Trade Grader · 7 Criteria</h1>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card title="Setup Definition">
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="field-group">
              <label className="t-label">Symbol</label>
              <input className="input mono" value={form.symbol} onChange={e => upd('symbol', e.target.value.toUpperCase())} />
            </div>
            <div className="field-group">
              <label className="t-label">Direction</label>
              <select className="select" value={form.direction} onChange={e => upd('direction', e.target.value)}>
                <option>LONG</option><option>SHORT</option>
              </select>
            </div>
            <div className="field-group">
              <label className="t-label">Entry</label>
              <input className="input mono" type="number" value={form.entry_price} onChange={updNum('entry_price')} />
            </div>
            <div className="field-group">
              <label className="t-label">Stop Loss</label>
              <input className="input mono" type="number" value={form.stop_loss_price} onChange={updNum('stop_loss_price')} />
            </div>
            <div className="field-group">
              <label className="t-label">TP1 (2R)</label>
              <input className="input mono" type="number" value={form.tp1_price} onChange={updNum('tp1_price')} />
            </div>
            <div className="field-group">
              <label className="t-label">TP2 (3R)</label>
              <input className="input mono" type="number" value={form.tp2_price} onChange={updNum('tp2_price')} />
            </div>
            <div className="field-group">
              <label className="t-label">Confidence (%)</label>
              <input className="input mono" type="number" value={form.confidence} onChange={updNum('confidence')} />
            </div>
            <div className="field-group">
              <label className="t-label">Risk per Trade (%)</label>
              <input className="input mono" type="number" step="0.5" value={form.risk_percent} onChange={updNum('risk_percent')} />
            </div>
            <div className="field-group">
              <label className="t-label">Drawdown Stage (1=Normal, 4=Emergency)</label>
              <input className="input mono" type="number" min="1" max="5" value={form.drawdown_stage} onChange={updNum('drawdown_stage')} />
            </div>
          </div>
        </Card>

        <Card title="7 Kriterien">
          <div className="col gap-8">
            {Object.entries(labels).map(([k, l]) => (
              <label key={k} className="row gap-12" style={{ alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--neutral-700)', cursor: 'pointer' }}>
                <input type="checkbox" checked={criteria[k]} onChange={e => setCriteria(c => ({ ...c, [k]: e.target.checked }))} />
                <span className={k === 'risk_reward' ? 'text-warning' : ''}>{l}</span>
              </label>
            ))}
          </div>
          <button className="btn btn-primary mt-16" onClick={submit} disabled={busy}>
            <Icon name="zap"/> {busy ? 'Bewerte…' : 'Setup bewerten'}
          </button>
        </Card>
      </div>

      {result && (
        <Card title="Ergebnis" style={{ marginTop: 16 }}>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12 }}>
            <KpiCard label="Grade" value={result.grade} cls={['A+','A'].includes(result.grade) ? 'up' : result.grade === 'B' ? 'neutral' : 'down'} valCls={['A+','A'].includes(result.grade) ? 'text-success' : result.grade === 'B' ? '' : 'text-warning'} meta={`Score ${result.setup_score}/7`} />
            <KpiCard label="Tradeable?" value={result.tradeable ? 'JA' : 'NEIN'} cls={result.tradeable ? 'up' : 'down'} valCls={result.tradeable ? 'text-success' : 'text-danger'} meta={`Stage ${form.drawdown_stage}`} />
            <KpiCard label="Position Size" value={result.position_size?.toFixed?.(2) ?? '—'} cls="neutral" meta={`${form.risk_percent}% Risk`} />
            <KpiCard label="Confidence" value={`${result.confidence?.toFixed?.(0) ?? '—'}%`} cls="neutral" meta="vom Trader" />
          </div>
        </Card>
      )}
    </div>
  );
}

// ─── Settings ──────────────────────────────────────────────
function Settings({ onReconfigure }) {
  const toast = useToast();
  const [healthy, setHealthy] = useState(null);
  const [risk, setRisk] = useState(null);

  useEffect(() => {
    Api.health().then(() => setHealthy(true)).catch(() => setHealthy(false));
    Api.riskStatus().then(setRisk).catch(() => {});
  }, []);

  const reset = () => {
    if (confirm('Alle gespeicherten Verbindungsdaten löschen?')) {
      Config.clear(); toast.push('info', 'Konfiguration gelöscht'); onReconfigure();
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">KONFIGURATION</div>
          <h1 className="t-h1">Settings</h1>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <Card title="Backend Connection" action={<Badge variant={healthy ? 'success' : 'danger'}>
          <span className={`dot ${healthy ? 'live' : 'crit'}`} style={{ marginRight: 6 }}></span>
          {healthy ? 'ONLINE' : 'OFFLINE'}
        </Badge>}>
          <KvList items={[
            ['Base URL', Config.baseUrl],
            ['API Key', Config.apiKey ? `••••${Config.apiKey.slice(-4)}` : '(nicht gesetzt)'],
            ['Session ID', Config.sessionId || '(nicht gesetzt)'],
          ]}/>
          <div className="row gap-8 mt-16">
            <button className="btn btn-secondary" onClick={onReconfigure}>Neu konfigurieren</button>
            <button className="btn btn-ghost" onClick={reset}>Reset</button>
          </div>
        </Card>

        <Card title="Risk Engine Status">
          {risk ? (
            <pre style={{ fontFamily: 'var(--font-mono)', fontSize: 11, whiteSpace: 'pre-wrap', color: 'var(--neutral-300)' }}>
              {JSON.stringify(risk, null, 2)}
            </pre>
          ) : <div className="t-body text-muted">Lade…</div>}
        </Card>
      </div>

      <Card title="Backend-Endpunkte" style={{ marginTop: 16 }}>
        <div className="t-body-sm text-muted mb-8">
          Diese UI ist verbunden mit den FastAPI-Endpunkten aus <span className="t-mono">app/main.py</span>.
        </div>
        <KvList items={[
          ['GET /health', 'Liveness'],
          ['POST /api/v1/brokers/setup', 'Session erstellen'],
          ['GET /api/v1/brokers/{sid}/quote', 'Live Quote'],
          ['POST /api/v1/orders/submit', 'Order mit Idempotency-Key'],
          ['GET /api/v1/orders/{id}', 'Order Status'],
          ['POST /api/v1/orders/{id}/cancel', 'Cancel'],
          ['GET /api/v1/positions', 'Positions + Drawdown'],
          ['GET /api/v1/audit', 'Audit Trail'],
          ['GET /api/risk/status', 'Risk Engine'],
          ['POST /api/risk/pre-trade-check', 'Pre-Trade Validation'],
          ['POST /api/backtest', 'Backtest'],
        ]}/>
        <div className="alert-banner alert-warn mt-16">
          <Icon name="alert"/>
          <div>
            <b>CORS:</b> Backend muss <span className="t-mono">CORS_ORIGINS={location.origin}</span> in <span className="t-mono">.env</span> haben,
            sonst blockt der Browser die Requests.
          </div>
        </div>
      </Card>
    </div>
  );
}

// ─── Halt Modal (real cancel-all) ──────────────────────────
function HaltModal({ open, onClose, positions }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const execute = async () => {
    setBusy(true); setResult(null);
    try {
      const res = await Api.haltSession();
      setResult(res);
      toast.push(
        res.failed.length === 0 ? 'success' : 'warn',
        `Halt: ${res.cancelled.length} cancelled · ${res.failed.length} failed`
      );
    } catch (e) {
      toast.push('error', `Halt fehlgeschlagen: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="row gap-12 mb-16">
          <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'rgba(244,67,54,0.15)', display: 'grid', placeItems: 'center', color: 'var(--danger-500)' }}>
            <Icon name="halt"/>
          </div>
          <div>
            <div className="t-h4">Emergency Halt</div>
            <div className="t-body-sm text-muted">
              Storniert alle offenen Orders ({positions.length} Positionen) und versetzt die Session in den HALTED-Zustand.
            </div>
          </div>
        </div>

        {!result && (
          <div className="alert-banner alert-warn mb-16">
            <Icon name="alert"/>
            <div>Diese Aktion ist nicht reversibel. Neue Orders werden anschließend von der Risk-Engine blockiert, bis du die Session manuell wieder freigibst.</div>
          </div>
        )}

        {result && (
          <div className={`alert-banner mb-16 ${result.failed.length === 0 ? 'alert-info' : 'alert-warn'}`}>
            <Icon name={result.failed.length === 0 ? 'check' : 'alert'}/>
            <div>
              <div><b>{result.message}</b></div>
              {result.cancelled.length > 0 && (
                <div className="t-body-sm">Cancelled: {result.cancelled.length} order(s)</div>
              )}
              {result.failed.length > 0 && (
                <div className="t-body-sm text-warning">
                  Failed: {result.failed.map(f => f.order_id).join(', ')}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="row gap-8">
          <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Schließen</button>
          {!result && (
            <button className="btn btn-danger" style={{ flex: 2 }} onClick={execute} disabled={busy}>
              <Icon name="halt"/> {busy ? 'Halt läuft…' : 'EMERGENCY HALT bestätigen'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Shell ─────────────────────────────────────────────────
function Shell() {
  const [page, setPage] = useState('dashboard');
  const [setupOpen, setSetupOpen] = useState(!Config.isReady());
  const [haltOpen, setHaltOpen] = useState(false);
  const [now, setNow] = useState(new Date());
  const [refreshKey, setRefreshKey] = useState(0);
  const live = useLiveData();

  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id); }, [refreshKey]);

  const nav = [
    { k: 'dashboard',   label: 'Dashboard',        ic: 'dashboard' },
    { k: 'trade',       label: 'Trading Console',  ic: 'trade' },
    { k: 'risk',        label: 'Risk Management',  ic: 'risk' },
    { k: 'grader',      label: 'Trade Grader',     ic: 'zap' },
    { k: 'correlation', label: 'Correlation',      ic: 'analytics' },
    { k: 'macro',       label: 'Macro Events',     ic: 'bell' },
    { k: 'audit',       label: 'Audit & History',  ic: 'analytics' },
    { k: 'settings',    label: 'Settings',         ic: 'settings' },
  ];

  const ready = Config.isReady();

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">TC</div>
          <div>
            <div className="brand-name">TRADE-CLAW</div>
            <div className="brand-sub">v4.0 · LIVE</div>
          </div>
        </div>
        <div className="topbar-right">
          <div className="connection-pill">
            <span className={`dot ${ready ? 'live' : 'crit'}`}></span>
            {ready ? `Session ${Config.sessionId.slice(0,8)}…` : 'Nicht verbunden'}
          </div>
          {live.lastUpdate && <div className="timestamp">Updated {live.lastUpdate.toLocaleTimeString('de-DE')}</div>}
          <button className="icon-btn" title="Reconfigure" onClick={() => setSetupOpen(true)}><Icon name="settings"/></button>
        </div>
      </header>

      <aside className="sidebar">
        <div className="nav-section">Module</div>
        {nav.map(n => (
          <button key={n.k} className={`nav-item ${page===n.k ? 'active' : ''}`} onClick={() => setPage(n.k)} data-screen-label={n.label}>
            <span className="ic"><Icon name={n.ic}/></span>{n.label}
          </button>
        ))}
        <div className="nav-spacer"></div>
        <div className="nav-footer">
          <div className="t-label mb-8">Live Snapshot</div>
          <div className="kpi-mini"><span className="text-muted">Positionen</span><span className="v">{live.positions.positions.length}</span></div>
          <div className="kpi-mini"><span className="text-muted">Unreal P&L</span><span className={`v ${pnlClass(live.positions.total_unrealized_pnl)}`}>{fmtMoney(live.positions.total_unrealized_pnl)}</span></div>
          <div className="kpi-mini"><span className="text-muted">Drawdown</span><span className="v">{num(live.positions.drawdown_pct).toFixed(2)}%</span></div>
          <div className="kpi-mini"><span className="text-muted">Halted</span><span className={`v ${live.positions.is_halted ? 'text-danger' : 'text-success'}`}>{live.positions.is_halted ? 'JA' : 'Nein'}</span></div>
        </div>
      </aside>

      <main className="main" data-screen-label={page}>
        {!ready && (
          <div className="alert-banner alert-warn mb-16">
            <Icon name="alert"/>
            <div>Bitte zuerst Backend-Verbindung konfigurieren. <button className="btn btn-ghost btn-sm" style={{ marginLeft: 12 }} onClick={() => setSetupOpen(true)}>Jetzt konfigurieren</button></div>
          </div>
        )}
        {page === 'dashboard'   && <Dashboard live={live} onHalt={() => setHaltOpen(true)} onNav={setPage} />}
        {page === 'trade'       && <TradingConsole live={live} />}
        {page === 'risk'        && <RiskManagement live={live} onHalt={() => setHaltOpen(true)} />}
        {page === 'grader'      && <GraderPage />}
        {page === 'correlation' && <CorrelationPage />}
        {page === 'macro'       && <MacroPage />}
        {page === 'audit'       && <AuditPage />}
        {page === 'settings'    && <Settings onReconfigure={() => setSetupOpen(true)} />}
      </main>

      <SetupModal open={setupOpen} onClose={() => setSetupOpen(false)} onDone={() => { setSetupOpen(false); setRefreshKey(k => k+1); }} />
      <HaltModal open={haltOpen} onClose={() => setHaltOpen(false)} positions={live.positions.positions} />
    </div>
  );
}

function App() { return <ToastHost><Shell /></ToastHost>; }

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
