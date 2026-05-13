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

  // New session form — broker types discovered from backend on open
  const [brokerType, setBrokerType] = useState(Config.brokerType || 'mock');
  const [environment, setEnvironment] = useState(Config.environment || 'paper');
  const [brokerCatalog, setBrokerCatalog] = useState([]);
  const [credValues, setCredValues] = useState({});

  useEffect(() => {
    if (!open) return;
    Api.brokerTypes()
      .then(d => {
        setBrokerCatalog(d.brokers || []);
        if (!d.brokers.find(b => b.broker_type === brokerType) && d.brokers.length) {
          setBrokerType(d.brokers[0].broker_type);
        }
      })
      .catch(e => toast.push('error', `Broker-Typen laden: ${e.message}`));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const currentBroker = brokerCatalog.find(b => b.broker_type === brokerType);

  // Reset credential values when the selected broker changes so we don't
  // accidentally send Hyperliquid creds to Binance.
  useEffect(() => {
    if (!currentBroker) return;
    setCredValues(v => {
      const next = {};
      for (const f of currentBroker.credentials) next[f.name] = v[f.name] || '';
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brokerType]);

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
      // Build credentials dict from the dynamic form, dropping empty optional fields.
      const credentials = {};
      const missing = [];
      for (const f of currentBroker?.credentials || []) {
        const v = (credValues[f.name] || '').trim();
        if (v) credentials[f.name] = v;
        else if (f.required) missing.push(f.name);
      }
      if (missing.length) throw new Error(`Pflichtfelder fehlen: ${missing.join(', ')}`);
      if (Object.keys(credentials).length === 0) {
        // Mock broker accepts empty credentials but the API rejects empty objects;
        // pass a placeholder so validation goes through.
        credentials.api_key = 'auto';
      }
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
              <label className="t-label">Broker / Provider</label>
              <select className="select" value={brokerType} onChange={e => setBrokerType(e.target.value)}>
                {Object.entries(
                  brokerCatalog.reduce((acc, b) => {
                    (acc[b.category] = acc[b.category] || []).push(b);
                    return acc;
                  }, {})
                ).map(([cat, list]) => (
                  <optgroup key={cat} label={cat.toUpperCase()}>
                    {list.map(b => (
                      <option key={b.broker_type} value={b.broker_type}>
                        {b.label}{b.tags?.length ? `  ·  ${b.tags.join(', ')}` : ''}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              {currentBroker && (
                <div className="field-hint" style={{ marginTop: 6 }}>{currentBroker.description}</div>
              )}
              <div className="field-hint" style={{ marginTop: 4, opacity: 0.7 }}>
                Eigenen Broker hinzufügen? Plugin in <span className="t-mono">app/brokers/plugins/</span> ablegen — Anleitung in <span className="t-mono">docs/CUSTOM_BROKERS.md</span>.
              </div>
            </div>

            <div className="field-group mb-16">
              <label className="t-label">Modus</label>
              <div className="row" style={{ gap: 8 }}>
                {[
                  ['paper', 'Paper / Demo', 'Sandbox · kein echtes Geld', currentBroker?.paper_supported !== false],
                  ['live',  'Live · echtes Geld', 'Order-Routing an realen Account', currentBroker?.live_supported !== false],
                ].map(([k, l, sub, supported]) => (
                  <button key={k} type="button"
                    onClick={() => supported && setEnvironment(k)}
                    disabled={!supported}
                    className={`btn ${environment===k ? (k==='live'?'btn-danger':'btn-primary') : 'btn-secondary'}`}
                    style={{ flex: 1, textAlign: 'left', padding: '10px 12px', opacity: supported ? 1 : 0.5 }}>
                    <div><b>{l}{!supported ? ' (nicht verfügbar)' : ''}</b></div>
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

            {currentBroker && currentBroker.credentials.length > 0 && (
              <div className="field-group mb-16">
                <label className="t-label">Credentials</label>
                {currentBroker.credentials.map(f => (
                  <div key={f.name} style={{ marginBottom: 10 }}>
                    <label className="t-label" style={{ fontSize: 11, opacity: 0.7 }}>
                      {f.name}{f.required ? '' : '  (optional)'}
                    </label>
                    <input
                      className="input mono"
                      type={f.secret ? 'password' : 'text'}
                      placeholder={f.placeholder}
                      value={credValues[f.name] || ''}
                      onChange={e => setCredValues(v => ({ ...v, [f.name]: e.target.value }))}
                    />
                    {f.help && <div className="field-hint">{f.help}</div>}
                  </div>
                ))}
              </div>
            )}

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

// ─── ML & Autopilot Page ───────────────────────────────────
function MlAutopilotPage() {
  const toast = useToast();
  const [mlState, setMlState] = useState(null);
  const [outcomes, setOutcomes] = useState({ items: [], total: 0, summary: {} });
  const [autopilot, setAutopilot] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [busy, setBusy] = useState({});
  const [bootstrapForm, setBootstrapForm] = useState({ period: '2y', epochs: 200 });
  const [closeForm, setCloseForm] = useState({});

  const refresh = useCallback(async () => {
    try {
      const [s, o, a, c] = await Promise.all([
        Api.mlStatus(),
        Api.mlOutcomes({ limit: 100 }),
        Api.autopilotStatus(),
        Api.mlCheckpoints(),
      ]);
      setMlState(s); setOutcomes(o); setAutopilot(a); setCheckpoints(c.checkpoints || []);
    } catch (e) {
      toast.push('error', `Reload: ${e.message}`);
    }
  }, [toast]);

  useEffect(() => { refresh(); }, [refresh]);

  const setBusyKey = (k, v) => setBusy(b => ({ ...b, [k]: v }));

  const retrain = async () => {
    setBusyKey('retrain', true);
    try {
      const r = await Api.mlRetrain({ epochs: 200, activate: true });
      toast.push('success', `Retrain ✓ samples=${r.samples} acc=${(r.final_accuracy*100).toFixed(1)}%`);
      await refresh();
    } catch (e) { toast.push('error', e.message); }
    finally { setBusyKey('retrain', false); }
  };

  const bootstrap = async () => {
    setBusyKey('bootstrap', true);
    try {
      const r = await Api.mlBootstrap({
        period: bootstrapForm.period,
        epochs: parseInt(bootstrapForm.epochs) || 200,
      });
      toast.push('success',
        `Bootstrap ✓ ${r.samples} Samples · ${r.symbols_processed.length} Symbols · acc=${(r.final_accuracy*100).toFixed(1)}%`);
      await refresh();
    } catch (e) { toast.push('error', `Bootstrap: ${e.message}`); }
    finally { setBusyKey('bootstrap', false); }
  };

  const setAutopilotMode = async mode => {
    if (mode === 'live') {
      const ok = confirm(
        'AUTOPILOT auf LIVE schalten?\n\n' +
        'Eingehende TradingView-Signale werden automatisch zu Orders. ' +
        'Risk-Engine + ML-Gate filtern weiterhin, aber es gibt keine manuelle Bestätigung mehr pro Trade.'
      );
      if (!ok) return;
    }
    try {
      const r = await Api.autopilotConfigure({
        mode,
        session_id: Config.sessionId,
        threshold: autopilot?.threshold ?? 0.5,
      });
      setAutopilot(r);
      toast.push(mode === 'live' ? 'warn' : 'info', `Autopilot: ${mode}`);
    } catch (e) { toast.push('error', e.message); }
  };

  const closeTrade = async (orderId) => {
    const price = parseFloat(closeForm[orderId]);
    if (!price || price <= 0) { toast.push('warn', 'Schlusskurs eingeben'); return; }
    try {
      await Api.closeOrder(orderId, { closed_price: price });
      toast.push('success', `Order ${orderId.slice(0,8)}… geschlossen`);
      await refresh();
    } catch (e) { toast.push('error', e.message); }
  };

  const outcomeBadge = o => o === 'WIN' ? 'success' : o === 'LOSS' ? 'danger' : 'neutral';

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">SELF-LEARNING</div>
          <h1 className="t-h1">ML &amp; Autopilot</h1>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={refresh}><Icon name="refresh"/> Reload</button>
      </div>

      <div className="grid mb-16" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <Card title="Modell-Status">
          {mlState ? (
            <KvList items={[
              ['Model loaded', mlState.model_loaded ? '✓ ja' : '— nein'],
              ['Torch verfügbar', mlState.torch_available ? '✓' : '✗'],
              ['Checkpoint', mlState.checkpoint_path?.split(/[\\/]/).pop() || '—'],
              ['Geladen seit', mlState.loaded_at ? new Date(mlState.loaded_at).toLocaleString('de-DE') : '—'],
              ['Gate-Modus', mlState.gate_mode],
              ['Threshold', mlState.threshold?.toFixed?.(2) ?? '—'],
              ['Features', `${mlState.feature_count} Werte`],
            ]}/>
          ) : <div className="t-body text-muted">Lade…</div>}
          <div className="row gap-8 mt-16">
            <button className="btn btn-primary btn-sm" onClick={retrain} disabled={busy.retrain}>
              <Icon name="zap"/> {busy.retrain ? 'Trainiere…' : 'Auf Outcomes neu trainieren'}
            </button>
          </div>
        </Card>

        <Card title="Autopilot">
          {autopilot ? (
            <>
              <div className="row gap-8 mb-16">
                {[
                  ['off', 'Aus', 'btn-secondary'],
                  ['dry_run', 'Dry-Run', 'btn-primary'],
                  ['live', 'LIVE', 'btn-danger'],
                ].map(([k, l, cls]) => (
                  <button key={k} type="button"
                    className={`btn ${autopilot.mode === k ? cls : 'btn-ghost'} btn-sm`}
                    onClick={() => setAutopilotMode(k)} style={{ flex: 1 }}>
                    {l}
                  </button>
                ))}
              </div>
              <KvList items={[
                ['Status', autopilot.mode.toUpperCase()],
                ['Session', autopilot.session_id?.slice(0, 12) + '…' || '—'],
                ['Threshold', autopilot.threshold?.toFixed(2)],
                ['Erlaubte Grades', (autopilot.require_grade || []).join(', ')],
                ['Aktiv seit', autopilot.enabled_at ? new Date(autopilot.enabled_at).toLocaleString('de-DE') : '—'],
              ]}/>
              <div className="alert-banner alert-info mt-16">
                <Icon name="bell"/>
                <div>
                  <b>Webhook-URL:</b> <span className="t-mono">{Config.baseUrl}/api/v1/webhook/tradingview/&lt;TV_WEBHOOK_SECRET&gt;</span><br/>
                  Setze <span className="t-mono">TV_WEBHOOK_SECRET</span> in <span className="t-mono">.env</span>, dann via cloudflared/ngrok öffentlich tunneln.
                </div>
              </div>
            </>
          ) : <div className="t-body text-muted">Lade…</div>}
        </Card>
      </div>

      <Card title="Bootstrap (Phase 3) — synthetisches Training auf yfinance-Daten" style={{ marginBottom: 16 }}>
        <div className="t-body-sm text-muted mb-8">
          Lädt 2 Jahre OHLCV für Forex/Crypto/Metalle, generiert Setup-Kandidaten, simuliert Outcomes und trainiert eine Initialversion.
          Das ist dein Cold-Start-Workaround bevor genug Live-Outcomes gesammelt sind.
        </div>
        <div className="row gap-12">
          <div className="field-group" style={{ width: 100 }}>
            <label className="t-label">Period</label>
            <select className="select" value={bootstrapForm.period} onChange={e => setBootstrapForm(f => ({ ...f, period: e.target.value }))}>
              <option>1y</option><option>2y</option><option>5y</option>
            </select>
          </div>
          <div className="field-group" style={{ width: 100 }}>
            <label className="t-label">Epochs</label>
            <input className="input mono" type="number" value={bootstrapForm.epochs} onChange={e => setBootstrapForm(f => ({ ...f, epochs: e.target.value }))}/>
          </div>
          <button className="btn btn-primary" style={{ alignSelf: 'flex-end' }} onClick={bootstrap} disabled={busy.bootstrap}>
            <Icon name="zap"/> {busy.bootstrap ? 'Bootstrap läuft…' : 'Bootstrap starten (kann 1-2 Min dauern)'}
          </button>
        </div>
      </Card>

      <Card title={`Outcomes · ${outcomes.total} insgesamt`} action={
        <div className="row gap-8" style={{ fontSize: 12 }}>
          {Object.entries(outcomes.summary || {}).map(([k, v]) => (
            <Badge key={k} variant={outcomeBadge(k)}>{k}: {v}</Badge>
          ))}
        </div>
      } style={{ marginBottom: 16 }}>
        {outcomes.items.length === 0 ? (
          <div className="t-body text-muted" style={{ padding: '24px 0', textAlign: 'center' }}>Noch keine Outcomes — sobald du Trades schliesst, erscheinen sie hier.</div>
        ) : (
          <div style={{ overflowX: 'auto', margin: '0 -20px' }}>
            <table className="tbl">
              <thead><tr>
                <th style={{ paddingLeft: 20 }}>Order</th><th>Symbol</th><th>Side</th>
                <th>Entry</th><th>Outcome</th><th>P&amp;L</th><th>ML-Score</th><th>Aktion</th>
              </tr></thead>
              <tbody>
                {outcomes.items.map(o => (
                  <tr key={o.id}>
                    <td style={{ paddingLeft: 20 }} className="t-mono text-faint">{o.order_id?.slice(0, 12)}…</td>
                    <td className="t-mono">{o.symbol}</td>
                    <td><span className={`dir ${o.side.toLowerCase()}`}>{o.side}</span></td>
                    <td className="t-mono">{o.entry_price}</td>
                    <td>{o.outcome ? <Badge variant={outcomeBadge(o.outcome)}>{o.outcome}</Badge> : <span className="text-faint">offen</span>}</td>
                    <td className={`t-mono ${pnlClass(o.pnl)}`}>{o.pnl != null ? fmtMoney(o.pnl) : '—'}</td>
                    <td className="t-mono">{o.ml_score_at_submit?.toFixed?.(3) ?? '—'}</td>
                    <td>
                      {!o.outcome && (
                        <div className="row gap-4">
                          <input className="input mono" placeholder="Schlusskurs"
                            value={closeForm[o.order_id] || ''}
                            onChange={e => setCloseForm(f => ({ ...f, [o.order_id]: e.target.value }))}
                            style={{ width: 110, padding: '4px 6px' }}/>
                          <button className="btn btn-secondary btn-sm" onClick={() => closeTrade(o.order_id)}>
                            <Icon name="check"/> Schließen
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title={`Checkpoints (${checkpoints.length})`}>
        {checkpoints.length === 0 ? (
          <div className="t-body text-muted">Noch keine Checkpoints — Retrain oder Bootstrap legen sie an.</div>
        ) : (
          <table className="tbl">
            <thead><tr><th>Datei</th><th>Samples</th><th>Acc</th><th>Aktiv</th><th></th></tr></thead>
            <tbody>
              {checkpoints.map(c => (
                <tr key={c.checkpoint}>
                  <td className="t-mono">{c.checkpoint}</td>
                  <td>{c.samples ?? '—'}</td>
                  <td>{c.final_accuracy != null ? `${(c.final_accuracy * 100).toFixed(1)}%` : '—'}</td>
                  <td>{c.is_active ? <Badge variant="success">aktiv</Badge> : '—'}</td>
                  <td>
                    {!c.is_active && (
                      <button className="btn btn-ghost btn-sm" onClick={async () => {
                        await Api.mlActivateCheckpoint(c.checkpoint);
                        toast.push('success', `Aktiviert: ${c.checkpoint}`);
                        await refresh();
                      }}>Aktivieren</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

// ─── Backtest Page ─────────────────────────────────────────
function BacktestPage() {
  const toast = useToast();
  const [tab, setTab] = useState('insample');
  const [form, setForm] = useState({
    period: '2y', threshold: 0.5, starting_capital: 10000,
    risk_per_trade_pct: 0.02, rr: 3.0, symbolsText: '',
    train_fraction: 0.7, epochs: 200,
  });
  const [result, setResult] = useState(null);
  const [wfResult, setWfResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const upd = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const symbolsArr = () => form.symbolsText.trim()
    ? form.symbolsText.split(',').map(s => s.trim()).filter(Boolean)
    : null;

  const run = async () => {
    setBusy(true); setResult(null);
    try {
      const r = await Api.mlBacktest({
        symbols: symbolsArr(),
        period: form.period,
        threshold: parseFloat(form.threshold),
        starting_capital: parseFloat(form.starting_capital),
        risk_per_trade_pct: parseFloat(form.risk_per_trade_pct),
        rr: parseFloat(form.rr),
      });
      setResult(r);
      toast.push('success',
        `Backtest ✓ ${r.trades_taken} Trades · ROI ${r.roi_pct.toFixed(1)}% · Win-Rate ${(r.win_rate*100).toFixed(1)}%`);
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  };

  const runWf = async () => {
    setBusy(true); setWfResult(null);
    try {
      const r = await Api.mlWalkforward({
        symbols: symbolsArr(),
        period: form.period,
        train_fraction: parseFloat(form.train_fraction),
        threshold: parseFloat(form.threshold),
        starting_capital: parseFloat(form.starting_capital),
        risk_per_trade_pct: parseFloat(form.risk_per_trade_pct),
        rr: parseFloat(form.rr),
        epochs: parseInt(form.epochs) || 200,
      });
      setWfResult(r);
      toast.push(r.out_of_sample.roi_pct >= 0 ? 'success' : 'warn',
        `Walk-Forward · in ${r.in_sample.roi_pct.toFixed(1)}% / out ${r.out_of_sample.roi_pct.toFixed(1)}%`);
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  };

  // Tiny inline SVG sparkline for the equity curve — keeps the frontend
  // CDN-free; if you ever want a real chart, swap to Recharts here.
  const renderEquityCurve = curve => {
    if (!curve || curve.length < 2) return null;
    const w = 800, h = 200, pad = 30;
    const min = Math.min(...curve), max = Math.max(...curve);
    const range = max - min || 1;
    const stepX = (w - 2 * pad) / (curve.length - 1);
    const points = curve.map((v, i) => {
      const x = pad + i * stepX;
      const y = h - pad - ((v - min) / range) * (h - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    const startEq = curve[0], endEq = curve[curve.length - 1];
    const positive = endEq >= startEq;
    return (
      <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} style={{ background: 'var(--neutral-800)', borderRadius: 8 }}>
        <line x1={pad} y1={h-pad} x2={w-pad} y2={h-pad} stroke="var(--neutral-700)" />
        <line x1={pad} y1={pad}   x2={pad}   y2={h-pad} stroke="var(--neutral-700)" />
        <text x={pad+4} y={pad+12} fill="var(--neutral-400)" fontSize="11">${max.toFixed(0)}</text>
        <text x={pad+4} y={h-pad-4} fill="var(--neutral-400)" fontSize="11">${min.toFixed(0)}</text>
        <polyline fill="none" stroke={positive ? 'var(--success-500)' : 'var(--danger-500)'}
          strokeWidth="2" points={points}/>
        <line x1={pad} y1={h-pad-((startEq-min)/range)*(h-2*pad)} x2={w-pad}
          y2={h-pad-((startEq-min)/range)*(h-2*pad)} stroke="var(--neutral-600)" strokeDasharray="4,4"/>
      </svg>
    );
  };

  const renderConfigGrid = (extra) => (
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
      <div className="field-group">
        <label className="t-label">Symbole (kommasepariert, leer = Default)</label>
        <input className="input mono" value={form.symbolsText} onChange={e => upd('symbolsText', e.target.value)} placeholder="EURUSD=X,BTC-USD,GLD" />
      </div>
      <div className="field-group">
        <label className="t-label">Period</label>
        <select className="select" value={form.period} onChange={e => upd('period', e.target.value)}>
          <option>1y</option><option>2y</option><option>3y</option><option>5y</option><option>10y</option>
        </select>
      </div>
      <div className="field-group">
        <label className="t-label">Threshold ({parseFloat(form.threshold).toFixed(2)})</label>
        <input type="range" min="0" max="1" step="0.05" value={form.threshold} onChange={e => upd('threshold', e.target.value)} />
      </div>
      <div className="field-group">
        <label className="t-label">Startkapital ($)</label>
        <input className="input mono" type="number" value={form.starting_capital} onChange={e => upd('starting_capital', e.target.value)} />
      </div>
      <div className="field-group">
        <label className="t-label">Risk pro Trade (%)</label>
        <input className="input mono" type="number" step="0.005" value={form.risk_per_trade_pct} onChange={e => upd('risk_per_trade_pct', e.target.value)} />
      </div>
      <div className="field-group">
        <label className="t-label">R/R-Multiple</label>
        <input className="input mono" type="number" step="0.5" value={form.rr} onChange={e => upd('rr', e.target.value)} />
      </div>
      {extra}
    </div>
  );

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">VALIDATION</div>
          <h1 className="t-h1">ML Backtest</h1>
        </div>
      </div>

      <div className="tabs mb-16">
        <button className={`tab ${tab==='insample'?'active':''}`} onClick={() => setTab('insample')}>In-Sample (aktives Modell)</button>
        <button className={`tab ${tab==='walkforward'?'active':''}`} onClick={() => setTab('walkforward')}>Walk-Forward (echte OOS)</button>
      </div>

      {tab === 'insample' && (
        <>
          <div className="alert-banner alert-info mb-16">
            <Icon name="bell"/>
            <div>
              <b>In-Sample-Test:</b> der Backtester lädt yfinance-OHLCV und schickt jede Setup-Kandidate durchs <i>aktive</i> Modell.
              Wenn das Modell auf denselben Daten trainiert wurde, sind die Ergebnisse hier <i>optimistisch</i> — verwende den Walk-Forward-Tab für eine ehrliche Out-of-Sample-Validierung.
            </div>
          </div>

          <Card title="Konfiguration" style={{ marginBottom: 16 }}>
            {renderConfigGrid()}
            <button className="btn btn-primary mt-16" onClick={run} disabled={busy}>
              <Icon name="zap"/> {busy ? 'Backtest läuft… (1–2 Min)' : 'Backtest starten'}
            </button>
          </Card>

          {result && (
            <>
              <div className="kpi-grid mb-16">
                <KpiCard label="ROI" value={`${result.roi_pct.toFixed(1)}%`} cls={result.roi_pct >= 0 ? 'up' : 'down'} valCls={result.roi_pct >= 0 ? 'text-success' : 'text-danger'} meta={`$${result.starting_capital.toFixed(0)} → $${result.ending_capital.toFixed(0)}`} />
                <KpiCard label="Win-Rate" value={`${(result.win_rate*100).toFixed(1)}%`} cls="neutral" meta={`${result.wins} W / ${result.losses} L`} />
                <KpiCard label="Expectancy" value={`${result.expectancy_r.toFixed(2)}R`} cls={result.expectancy_r > 0 ? 'up' : 'down'} valCls={result.expectancy_r > 0 ? 'text-success' : 'text-danger'} meta={`R/R 1:${result.rr}`} />
                <KpiCard label="Trades" value={result.trades_taken} cls="neutral" meta={`${result.trades_skipped} skipped (${result.skipped_lowscore} low score)`} />
              </div>

              <Card title="Equity-Kurve" style={{ marginBottom: 16 }}>
                {renderEquityCurve(result.equity_curve)}
                <div className="t-body-sm text-muted mt-8">
                  {result.samples} Setup-Kandidaten · Symbole: {result.symbols_processed.join(', ')}
                </div>
              </Card>

              <Card title="Score-Verteilung (Modell-Konfidenz auf allen Kandidaten)">
                <div className="t-body-sm text-muted mb-8">
                  Median: {result.score_distribution?.length ? (result.score_distribution.slice().sort()[Math.floor(result.score_distribution.length/2)]).toFixed(3) : '—'}
                  {' · '}
                  Über Threshold ({result.threshold.toFixed(2)}): {result.score_distribution?.filter(s => s >= result.threshold).length || 0} / {result.score_distribution?.length || 0}
                </div>
                <div className="row" style={{ flexWrap: 'wrap', gap: 1 }}>
                  {(result.score_distribution || []).map((s, i) => (
                    <div key={i} title={s.toFixed(3)} style={{
                      width: 6, height: Math.max(4, s * 40),
                      background: s >= result.threshold ? 'var(--success-500)' : 'var(--neutral-600)',
                      borderRadius: 1,
                    }}/>
                  ))}
                </div>
              </Card>
            </>
          )}
        </>
      )}

      {tab === 'walkforward' && (
        <>
          <div className="alert-banner alert-info mb-16">
            <Icon name="bell"/>
            <div>
              <b>Walk-Forward:</b> chronologischer Train/Test-Split. Das Modell wird neu auf der ersten <span className="t-mono">{(form.train_fraction*100).toFixed(0)}%</span> der Daten trainiert und dann auf der restlichen <i>nie gesehenen</i> Periode getestet. Das ist die ehrliche Antwort auf „funktioniert das?".
            </div>
          </div>

          <Card title="Konfiguration" style={{ marginBottom: 16 }}>
            {renderConfigGrid(
              <>
                <div className="field-group">
                  <label className="t-label">Train-Anteil ({(parseFloat(form.train_fraction)*100).toFixed(0)}%)</label>
                  <input type="range" min="0.3" max="0.9" step="0.05" value={form.train_fraction} onChange={e => upd('train_fraction', e.target.value)}/>
                </div>
                <div className="field-group">
                  <label className="t-label">Epochs</label>
                  <input className="input mono" type="number" value={form.epochs} onChange={e => upd('epochs', e.target.value)}/>
                </div>
              </>
            )}
            <button className="btn btn-primary mt-16" onClick={runWf} disabled={busy}>
              <Icon name="zap"/> {busy ? 'Walk-Forward läuft…' : 'Walk-Forward starten'}
            </button>
          </Card>

          {wfResult && (
            <>
              <Card style={{ marginBottom: 16 }}>
                <div className="t-h4 mb-8">Verdict</div>
                <div className={`alert-banner ${
                  wfResult.honest_verdict.includes('OVERFIT') ? 'alert-critical' :
                  wfResult.honest_verdict.includes('PROMISING') ? 'alert-info' :
                  'alert-warn'
                }`}>
                  <Icon name={wfResult.honest_verdict.includes('PROMISING') ? 'check' : 'alert'}/>
                  <div>{wfResult.honest_verdict}</div>
                </div>
              </Card>

              <div className="grid mb-16" style={{ gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <Card title={`In-Sample (${wfResult.samples.train} samples)`}>
                  <div className="kpi-grid mb-8">
                    <KpiCard label="ROI" value={`${wfResult.in_sample.roi_pct.toFixed(1)}%`} cls={wfResult.in_sample.roi_pct >= 0 ? 'up' : 'down'} valCls={wfResult.in_sample.roi_pct >= 0 ? 'text-success' : 'text-danger'} meta={`${wfResult.in_sample.trades_taken} Trades`} />
                    <KpiCard label="Win-Rate" value={`${(wfResult.in_sample.win_rate*100).toFixed(0)}%`} cls="neutral" meta={`${wfResult.in_sample.wins}W / ${wfResult.in_sample.losses}L`} />
                  </div>
                  {renderEquityCurve(wfResult.in_sample.equity_curve)}
                </Card>

                <Card title={`Out-of-Sample (${wfResult.samples.test} samples)`}>
                  <div className="kpi-grid mb-8">
                    <KpiCard label="ROI" value={`${wfResult.out_of_sample.roi_pct.toFixed(1)}%`} cls={wfResult.out_of_sample.roi_pct >= 0 ? 'up' : 'down'} valCls={wfResult.out_of_sample.roi_pct >= 0 ? 'text-success' : 'text-danger'} meta={`${wfResult.out_of_sample.trades_taken} Trades`} />
                    <KpiCard label="Win-Rate" value={`${(wfResult.out_of_sample.win_rate*100).toFixed(0)}%`} cls="neutral" meta={`${wfResult.out_of_sample.wins}W / ${wfResult.out_of_sample.losses}L`} />
                  </div>
                  {renderEquityCurve(wfResult.out_of_sample.equity_curve)}
                </Card>
              </div>

              <Card title="Modell-Statistik">
                <KvList items={[
                  ['Trainings-Loss', wfResult.training.final_loss.toFixed(4)],
                  ['Trainings-Accuracy', `${(wfResult.training.final_accuracy*100).toFixed(1)}%`],
                  ['Trades skipped (in-sample)', wfResult.in_sample.trades_skipped],
                  ['Trades skipped (out-of-sample)', wfResult.out_of_sample.trades_skipped],
                  ['Expectancy in-sample', `${wfResult.in_sample.expectancy_r.toFixed(2)}R`],
                  ['Expectancy out-of-sample', `${wfResult.out_of_sample.expectancy_r.toFixed(2)}R`],
                ]}/>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  );
}

// ─── Broker hinzufügen Page ────────────────────────────────
function BrokersPage() {
  const toast = useToast();
  const [tab, setTab] = useState('ccxt');
  const [defs, setDefs] = useState([]);
  const [busy, setBusy] = useState(false);

  // CCXT tab state
  const [ccxtList, setCcxtList] = useState({ installed: false, exchanges: [] });
  const [ccxtForm, setCcxtForm] = useState({ exchange: '', label: '', tags: '' });
  const [ccxtFilter, setCcxtFilter] = useState('');

  // REST tab state — start from the example template
  const [restForm, setRestForm] = useState({
    broker_type: 'custom:my-broker',
    label: 'My Broker',
    description: '',
    tags: '',
    paper_supported: true,
    live_supported: true,
    config: '',
    credentials: '[\n  {"name":"api_key","secret":false,"placeholder":"API key"},\n  {"name":"secret_key","required":false,"secret":true,"placeholder":"API secret"}\n]',
    test_creds: '{"api_key":"test","secret_key":"test"}',
  });
  const [testResult, setTestResult] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [list, ccxt, tpl] = await Promise.all([
        Api.brokerDefs(),
        Api.ccxtExchanges(),
        Api.restTemplate(),
      ]);
      setDefs(list.defs || []);
      setCcxtList(ccxt);
      if (!restForm.config) {
        setRestForm(f => ({ ...f, config: JSON.stringify(tpl.example, null, 2) }));
      }
    } catch (e) { toast.push('error', `Reload: ${e.message}`); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast]);

  useEffect(() => { refresh(); }, [refresh]);

  const filteredCcxt = useMemo(() => {
    const f = ccxtFilter.toLowerCase().trim();
    return f ? ccxtList.exchanges.filter(e => e.includes(f)) : ccxtList.exchanges;
  }, [ccxtList.exchanges, ccxtFilter]);

  const addCcxt = async () => {
    if (!ccxtForm.exchange) { toast.push('warn', 'Exchange auswählen'); return; }
    setBusy(true);
    try {
      const res = await Api.addCcxtDef({
        exchange: ccxtForm.exchange,
        label: ccxtForm.label || undefined,
        tags: ccxtForm.tags ? ccxtForm.tags.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      });
      toast.push('success', `${res.broker_type} registriert`);
      setCcxtForm({ exchange: '', label: '', tags: '' });
      await refresh();
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  };

  const addRest = async () => {
    setBusy(true);
    try {
      let config, credentials;
      try { config = JSON.parse(restForm.config); }
      catch { throw new Error('Config ist kein gültiges JSON'); }
      try { credentials = restForm.credentials ? JSON.parse(restForm.credentials) : []; }
      catch { throw new Error('Credentials-Schema ist kein gültiges JSON'); }
      await Api.addRestDef({
        broker_type: restForm.broker_type,
        label: restForm.label,
        description: restForm.description,
        tags: restForm.tags ? restForm.tags.split(',').map(s => s.trim()).filter(Boolean) : undefined,
        paper_supported: restForm.paper_supported,
        live_supported: restForm.live_supported,
        config,
        credentials,
      });
      toast.push('success', `${restForm.broker_type} registriert`);
      await refresh();
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  };

  const testRest = async () => {
    setBusy(true); setTestResult(null);
    try {
      let config, credentials;
      try { config = JSON.parse(restForm.config); }
      catch { throw new Error('Config ist kein gültiges JSON'); }
      try { credentials = JSON.parse(restForm.test_creds); }
      catch { throw new Error('Test-Credentials sind kein gültiges JSON'); }
      const r = await Api.testRestDef({ config, credentials, paper: restForm.paper_supported });
      setTestResult(r);
      toast.push(r.ok ? 'success' : 'warn', r.ok ? 'Verbindung ok' : `Verbindung fehlgeschlagen (${r.stage})`);
    } catch (e) { toast.push('error', e.message); }
    finally { setBusy(false); }
  };

  const deleteDef = async (broker_type) => {
    if (!confirm(`Broker-Definition "${broker_type}" löschen?`)) return;
    try {
      await Api.deleteBrokerDef(broker_type);
      toast.push('info', `${broker_type} entfernt`);
      await refresh();
    } catch (e) { toast.push('error', e.message); }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">PROVIDER</div>
          <h1 className="t-h1">Broker hinzufügen</h1>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={refresh}><Icon name="refresh"/> Reload</button>
      </div>

      <div className="alert-banner alert-info mb-16">
        <Icon name="bell"/>
        <div>
          Hier registrierst du eigene Broker, ohne Code-Editing. Nach dem Speichern erscheinen sie sofort im Setup-Dropdown unter Kategorie <span className="t-mono">custom</span>.
          Beim nächsten Backend-Neustart werden sie automatisch aus der DB nachgeladen.
        </div>
      </div>

      <div className="tabs mb-16">
        <button className={`tab ${tab==='ccxt'?'active':''}`} onClick={() => setTab('ccxt')}>CCXT-Exchange</button>
        <button className={`tab ${tab==='rest'?'active':''}`} onClick={() => setTab('rest')}>Generic REST</button>
        <button className={`tab ${tab==='list'?'active':''}`} onClick={() => setTab('list')}>Bestehende ({defs.length})</button>
      </div>

      {tab === 'ccxt' && (
        <Card title="CCXT-Exchange auswählen">
          {!ccxtList.installed && (
            <div className="alert-banner alert-warn mb-16">
              <Icon name="alert"/>
              <div>CCXT ist nicht installiert. <span className="t-mono">pip install ccxt</span> im venv ausführen oder über <span className="t-mono">requirements.txt</span> nachziehen.</div>
            </div>
          )}
          {ccxtList.installed && (
            <>
              <div className="t-body-sm text-muted mb-8">
                {ccxtList.exchanges.length} Exchanges verfügbar. Filter eingeben, dann auswählen.
              </div>
              <input className="input mono mb-8" value={ccxtFilter} onChange={e => setCcxtFilter(e.target.value)} placeholder="Suche (binance, kraken, …)" />
              <div style={{ maxHeight: 220, overflowY: 'auto', border: '1px solid var(--neutral-700)', borderRadius: 4, padding: 8 }}>
                <div className="row" style={{ flexWrap: 'wrap', gap: 4 }}>
                  {filteredCcxt.slice(0, 200).map(name => (
                    <button key={name} type="button"
                      className={`btn btn-sm ${ccxtForm.exchange === name ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setCcxtForm(f => ({ ...f, exchange: name }))}>
                      {name}
                    </button>
                  ))}
                  {filteredCcxt.length > 200 && (
                    <div className="t-body-sm text-faint">+{filteredCcxt.length - 200} mehr — Filter eingrenzen</div>
                  )}
                </div>
              </div>

              <div className="grid mt-16" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="field-group">
                  <label className="t-label">Label (optional, default: Auto)</label>
                  <input className="input mono" value={ccxtForm.label} onChange={e => setCcxtForm(f => ({ ...f, label: e.target.value }))} placeholder={ccxtForm.exchange ? `${ccxtForm.exchange} (via CCXT)` : ''}/>
                </div>
                <div className="field-group">
                  <label className="t-label">Tags (kommasepariert)</label>
                  <input className="input mono" value={ccxtForm.tags} onChange={e => setCcxtForm(f => ({ ...f, tags: e.target.value }))} placeholder="crypto, spot"/>
                </div>
              </div>

              <button className="btn btn-primary mt-16" onClick={addCcxt} disabled={busy || !ccxtForm.exchange}>
                <Icon name="check"/> Hinzufügen{ccxtForm.exchange ? ` als ccxt:${ccxtForm.exchange}` : ''}
              </button>
            </>
          )}
        </Card>
      )}

      {tab === 'rest' && (
        <>
          <Card title="Metadaten" style={{ marginBottom: 16 }}>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="field-group">
                <label className="t-label">broker_type (eindeutige ID, lowercase)</label>
                <input className="input mono" value={restForm.broker_type} onChange={e => setRestForm(f => ({ ...f, broker_type: e.target.value.toLowerCase() }))} placeholder="custom:my-broker"/>
              </div>
              <div className="field-group">
                <label className="t-label">Label (Anzeige)</label>
                <input className="input mono" value={restForm.label} onChange={e => setRestForm(f => ({ ...f, label: e.target.value }))}/>
              </div>
              <div className="field-group">
                <label className="t-label">Beschreibung</label>
                <input className="input mono" value={restForm.description} onChange={e => setRestForm(f => ({ ...f, description: e.target.value }))}/>
              </div>
              <div className="field-group">
                <label className="t-label">Tags (kommasepariert)</label>
                <input className="input mono" value={restForm.tags} onChange={e => setRestForm(f => ({ ...f, tags: e.target.value }))}/>
              </div>
              <div className="field-group">
                <label className="t-label">Paper-Modus erlauben</label>
                <input type="checkbox" checked={restForm.paper_supported} onChange={e => setRestForm(f => ({ ...f, paper_supported: e.target.checked }))}/>
              </div>
              <div className="field-group">
                <label className="t-label">Live-Modus erlauben</label>
                <input type="checkbox" checked={restForm.live_supported} onChange={e => setRestForm(f => ({ ...f, live_supported: e.target.checked }))}/>
              </div>
            </div>
          </Card>

          <Card title="REST-Konfiguration (JSON)" style={{ marginBottom: 16 }}>
            <div className="t-body-sm text-muted mb-8">
              Endpoints, Auth-Methode, JSON-Pfade. Vorlage ist vorausgefüllt — passe URLs und Felder an deinen Broker an.
              Doku: <span className="t-mono">docs/CUSTOM_BROKERS.md</span>
            </div>
            <textarea className="input mono" rows={18} value={restForm.config} onChange={e => setRestForm(f => ({ ...f, config: e.target.value }))} style={{ resize: 'vertical', width: '100%' }}/>
          </Card>

          <Card title="Credential-Schema (JSON, optional)" style={{ marginBottom: 16 }}>
            <div className="t-body-sm text-muted mb-8">
              Beschreibt welche Felder die UI im Setup-Dialog anzeigt (api_key, secret_key, …). Lass es leer für Default (api_key + optional secret_key).
            </div>
            <textarea className="input mono" rows={5} value={restForm.credentials} onChange={e => setRestForm(f => ({ ...f, credentials: e.target.value }))} style={{ resize: 'vertical', width: '100%' }}/>
          </Card>

          <Card title="Verbindung testen" style={{ marginBottom: 16 }}>
            <div className="t-body-sm text-muted mb-8">
              Trade-Claw versucht <span className="t-mono">authenticate</span> + <span className="t-mono">balance</span> mit den unten eingegebenen Test-Credentials, ohne den Broker zu speichern.
            </div>
            <textarea className="input mono mb-8" rows={3} value={restForm.test_creds} onChange={e => setRestForm(f => ({ ...f, test_creds: e.target.value }))} style={{ resize: 'vertical', width: '100%' }} placeholder='{"api_key":"...","secret_key":"..."}'/>
            <button className="btn btn-secondary" onClick={testRest} disabled={busy}>
              <Icon name="check"/> Verbindung testen
            </button>
            {testResult && (
              <div className={`alert-banner mt-16 ${testResult.ok ? 'alert-info' : 'alert-critical'}`}>
                <Icon name={testResult.ok ? 'check' : 'alert'}/>
                <div>
                  {testResult.ok ? (
                    <>
                      <b>OK</b> — Authentifizierung erfolgreich.
                      {testResult.balance && Object.keys(testResult.balance).length > 0 && (
                        <pre style={{ fontSize: 11, marginTop: 8, fontFamily: 'var(--font-mono)' }}>
                          {JSON.stringify(testResult.balance, null, 2)}
                        </pre>
                      )}
                    </>
                  ) : (
                    <>
                      <b>{testResult.stage}</b> fehlgeschlagen: <span className="t-mono">{testResult.error}</span>
                    </>
                  )}
                </div>
              </div>
            )}
          </Card>

          <button className="btn btn-primary" onClick={addRest} disabled={busy}>
            <Icon name="check"/> Speichern &amp; registrieren
          </button>
        </>
      )}

      {tab === 'list' && (
        <Card title={`Eigene Broker (${defs.length})`}>
          {defs.length === 0 ? (
            <div className="t-body text-muted">Noch keine eigenen Broker definiert.</div>
          ) : (
            <table className="tbl">
              <thead><tr>
                <th>broker_type</th><th>Kind</th><th>Label</th><th>Tags</th>
                <th>Paper</th><th>Live</th><th></th>
              </tr></thead>
              <tbody>
                {defs.map(d => (
                  <tr key={d.id}>
                    <td className="t-mono">{d.broker_type}</td>
                    <td><Badge variant="neutral">{d.kind}</Badge></td>
                    <td>{d.label}</td>
                    <td className="t-body-sm">{(d.tags || []).join(', ') || '—'}</td>
                    <td>{d.paper_supported ? '✓' : '—'}</td>
                    <td>{d.live_supported ? '✓' : '—'}</td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => deleteDef(d.broker_type)}>
                        Löschen
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}

// ─── Safety Dashboard ──────────────────────────────────────
function ReadinessChecklist({ data }) {
  const cd = data.cooldown || {};
  const dr = data.dry_run || {};
  const ip = data.ip_allowlist || {};
  const overlay = data.macro_overlay || {};
  const ap = data.autopilot || {};
  const envBlock = data.environment || {};
  const audit = data.audit_chain || {};

  // Each check item has: label, ok (true/false), severity ('error'|'warn'),
  // detail (short why). Severity=warn means "advisory, not blocking".
  const checks = [
    { label: 'Dry-Run-Minimum erfüllt',
      ok: !!dr.live_transition_allowed,
      severity: 'error',
      detail: `${dr.current_count ?? 0}/${dr.min_required ?? 20} would-submit Trades` },
    { label: 'Kein Loss-Cooldown aktiv',
      ok: !cd.cooldown_until,
      severity: 'error',
      detail: cd.cooldown_until ? `Pause bis ${new Date(cd.cooldown_until).toLocaleString('de-DE')}` : 'Streak sauber' },
    { label: 'Autopilot session_id konfiguriert',
      ok: !!ap.session_id_set,
      severity: 'error',
      detail: ap.session_id_set ? 'gesetzt' : 'fehlt — Autopilot kennt keinen Broker' },
    { label: 'TV-Webhook-Secret gesetzt',
      ok: !!envBlock.tv_webhook_secret_set,
      severity: 'error',
      detail: envBlock.tv_webhook_secret_set ? 'gesetzt (.env)' : 'fehlt — Webhook deaktiviert' },
    { label: 'Audit-Chain intakt',
      ok: audit.valid !== false,
      severity: 'error',
      detail: audit.valid === false ? `Bruch bei id=${audit.first_break_id}` : `${audit.rows_checked ?? 0} Zeilen verifiziert` },
    { label: 'IP-Allowlist konfiguriert',
      ok: !!ip.configured,
      severity: 'warn',
      detail: ip.configured ? `${(ip.addresses || []).length} IPs erlaubt` : 'leer = allow-all (Defense-in-Depth fehlt)' },
    { label: 'Keine aktiven CRITICAL-Macro-Events',
      ok: (overlay.active_critical_events ?? 0) === 0,
      severity: 'warn',
      detail: overlay.active_critical_events > 0 ? `${overlay.active_critical_events} Event(s) blockieren Symbole` : 'ruhig' },
    { label: 'Volatilität normal (multiplier ×1.0)',
      ok: (overlay.volatility_multiplier ?? 1) >= 1.0,
      severity: 'warn',
      detail: `×${(overlay.volatility_multiplier ?? 1).toFixed(2)}` },
    { label: 'ML-Gate aktiv (advisory oder enforce)',
      ok: envBlock.ml_gate_mode !== 'off',
      severity: 'warn',
      detail: `ML_GATE_MODE=${envBlock.ml_gate_mode || '—'}` },
  ];

  const errorsOpen = checks.filter(c => !c.ok && c.severity === 'error').length;
  const warningsOpen = checks.filter(c => !c.ok && c.severity === 'warn').length;
  const ready = errorsOpen === 0;

  return (
    <Card title="Pre-Live Readiness" style={{ marginBottom: 16 }} action={
      <Badge variant={ready ? (warningsOpen === 0 ? 'success' : 'warning') : 'danger'}>
        {ready
          ? (warningsOpen === 0 ? 'ALLES GRÜN' : `${warningsOpen} WARNUNG(EN)`)
          : `${errorsOpen} BLOCKER`}
      </Badge>
    }>
      <div className="t-body-sm text-muted" style={{ marginBottom: 12 }}>
        Synthese aus den Gates unten. <b>Blocker</b> verhindern Live-Trading.{' '}
        <b>Warnungen</b> sind beratend — du kannst Live-Mode trotzdem aktivieren,
        sollst sie aber kennen.
      </div>
      <div style={{ display: 'grid', gap: 6 }}>
        {checks.map((c, i) => (
          <div key={i} className="row gap-8" style={{ alignItems: 'baseline' }}>
            <span style={{ minWidth: 18 }}>
              {c.ok
                ? <Icon name="check"/>
                : <span className={c.severity === 'error' ? 'text-danger' : 'text-warning'}>
                    <Icon name="x"/>
                  </span>}
            </span>
            <span className={c.ok ? '' : (c.severity === 'error' ? 'text-danger' : 'text-warning')}>
              {c.label}
            </span>
            <span className="t-body-sm text-muted" style={{ marginLeft: 'auto' }}>
              {c.detail}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function SafetyPage() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const res = await Api.safetyStatus();
      setData(res);
      setLastUpdate(new Date());
    } catch (e) {
      toast.push('error', e.message);
    } finally {
      setBusy(false);
    }
  }, [toast]);

  // Initial load + 10-second poll (state changes are slow — outcomes, macro polls)
  useEffect(() => {
    let stopped = false;
    let timer = null;
    const tick = async () => {
      if (stopped) return;
      try {
        const res = await Api.safetyStatus();
        if (!stopped) { setData(res); setLastUpdate(new Date()); }
      } catch { /* swallow; manual reload available */ }
      if (!stopped) timer = setTimeout(tick, 10000);
    };
    tick();
    return () => { stopped = true; if (timer) clearTimeout(timer); };
  }, []);

  if (!data) {
    return (
      <div className="page">
        <div className="page-head"><div><div className="breadcrumb">SAFETY</div><h1 className="t-h1">Safety Dashboard</h1></div></div>
        <div className="t-body text-muted">Lade Safety-Status…</div>
      </div>
    );
  }

  const cd = data.cooldown || {};
  const cdActive = !!cd.cooldown_until;
  const dr = data.dry_run || {};
  const drMet = !!dr.live_transition_allowed;
  const ip = data.ip_allowlist || {};
  const overlay = data.macro_overlay || {};
  const sl = data.sl_distance || {};

  const multClass = m => m >= 1.0 ? 'success' : m >= 0.7 ? 'info' : m >= 0.4 ? 'warning' : 'danger';

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="breadcrumb">SAFETY</div>
          <h1 className="t-h1">Safety Dashboard</h1>
          <div className="t-body-sm text-muted">
            Cross-cutting Gates: was kann einen Live-Trade jenseits der Risk-Engine blockieren.
          </div>
        </div>
        <div className="row gap-8">
          {lastUpdate && <div className="timestamp">Updated {lastUpdate.toLocaleTimeString('de-DE')}</div>}
          <button className="btn btn-secondary btn-sm" onClick={load} disabled={busy}>
            <Icon name="refresh"/> Reload
          </button>
        </div>
      </div>

      {/* Big top banner: live-transition allowance */}
      <div className={`alert-banner ${drMet ? 'alert-success' : 'alert-warn'} mb-16`}>
        <Icon name={drMet ? 'check' : 'lock'}/>
        <div>
          <b>Live-Transition {drMet ? 'erlaubt' : 'gesperrt'}.</b>{' '}
          {drMet
            ? `Du hast ${dr.current_count}/${dr.min_required} dry-run Trades — wechsel in den Live-Mode ist freigegeben.`
            : `Erst ${dr.current_count}/${dr.min_required} dry-run Trades gesammelt. Live-Mode bleibt gesperrt (oder force:true im API-Call).`}
        </div>
      </div>

      {/* Pre-Live Readiness Checklist — synthesis of everything below */}
      <ReadinessChecklist data={data} />


      <div className="grid mb-16" style={{ gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Cooldown */}
        <Card title="Consecutive-Loss Cooldown" action={
          <Badge variant={cdActive ? 'danger' : 'success'}>{cdActive ? 'AKTIV' : 'inaktiv'}</Badge>
        }>
          <KvList items={[
            ['Verlust-Streak', `${cd.consecutive_losses ?? 0} / ${cd.max_consecutive_losses ?? 3}`],
            ['Pause-Dauer', `${cd.cooldown_minutes ?? 60} min`],
            ['Pause bis', cd.cooldown_until ? new Date(cd.cooldown_until).toLocaleString('de-DE') : '—'],
          ]}/>
          <div className="t-body-sm text-muted" style={{ marginTop: 8 }}>
            Nach N Losses in Folge wird Trading für M Minuten pausiert. Ein Win resetet den Streak.
          </div>
        </Card>

        {/* SL distance */}
        <Card title="Stop-Loss Distance Cap">
          <KvList items={[
            ['Hard-Cap', `${(sl.cap_pct ?? 5).toFixed(1)} %`],
          ]}/>
          <div className="t-body-sm text-muted" style={{ marginTop: 8 }}>
            Orders mit SL weiter als <b>{(sl.cap_pct ?? 5).toFixed(1)}%</b> vom Entry werden von der Risk-Engine
            abgelehnt. Schützt vor fehlerhaften Webhook-Payloads und Modell-Bugs.
          </div>
        </Card>

        {/* Dry-Run minimum */}
        <Card title="Dry-Run Minimum" action={
          <Badge variant={drMet ? 'success' : 'warning'}>{drMet ? 'ERFÜLLT' : 'OFFEN'}</Badge>
        }>
          <KvList items={[
            ['Aktuell', `${dr.current_count ?? 0}`],
            ['Benötigt', `${dr.min_required ?? 20}`],
            ['Live-Schalter', drMet ? 'freigegeben' : 'gesperrt'],
          ]}/>
          <Progress
            pct={Math.min(100, ((dr.current_count ?? 0) / Math.max(1, dr.min_required ?? 20)) * 100)}
            variant={drMet ? 'success' : 'warning'}
          />
          <div className="t-body-sm text-muted" style={{ marginTop: 8 }}>
            Übergang von <code>dry_run → live</code> ist erst nach <b>{dr.min_required ?? 20}</b> would-submit-Trades
            erlaubt. Bypass: <code>{'{"mode":"live","force":true}'}</code>.
          </div>
        </Card>

        {/* Macro overlay */}
        <Card title="Macro Overlay" action={
          <Badge variant={multClass(overlay.volatility_multiplier ?? 1)}>
            ×{(overlay.volatility_multiplier ?? 1).toFixed(2)}
          </Badge>
        }>
          <KvList items={[
            ['Position-Size-Multiplier', `×${(overlay.volatility_multiplier ?? 1).toFixed(2)}`],
            ['Aktive CRITICAL-Events (24h)', `${overlay.active_critical_events ?? 0}`],
          ]}/>
          <div className="t-body-sm text-muted" style={{ marginTop: 8 }}>
            {overlay.volatility_reason || '—'}
          </div>
          <div className="t-body-sm text-muted" style={{ marginTop: 4 }}>
            Geo-Halt blockiert neue Entries wenn ein CRITICAL-Event das Symbol betrifft.
          </div>
        </Card>
      </div>

      {/* IP allowlist — full width */}
      <Card title="TradingView Webhook IP-Allowlist" action={
        <Badge variant={ip.configured ? 'success' : 'warning'}>
          {ip.configured ? 'KONFIGURIERT' : 'OFFEN'}
        </Badge>
      }>
        {ip.configured ? (
          <>
            <div className="t-body" style={{ marginBottom: 8 }}>Erlaubte IPs ({(ip.addresses || []).length}):</div>
            <div className="row gap-8" style={{ flexWrap: 'wrap' }}>
              {(ip.addresses || []).map(addr => (
                <code key={addr} className="badge badge-info">{addr}</code>
              ))}
            </div>
          </>
        ) : (
          <div className="t-body text-muted">
            Allowlist ist leer — Webhook akzeptiert Requests von jeder IP. Setze <code>TV_ALLOWED_IPS</code>{' '}
            in <code>.env</code> als Defense-in-Depth gegen Secret-Leaks.
          </div>
        )}
        <div className="t-body-sm text-muted" style={{ marginTop: 12 }}>
          Dokumentierte TradingView-IPs (Stand der Code-Defaults):
        </div>
        <div className="row gap-8" style={{ flexWrap: 'wrap', marginTop: 4 }}>
          {(ip.documented_tv_ips || []).map(addr => (
            <code key={addr} className="badge badge-neutral">{addr}</code>
          ))}
        </div>
        <div className="t-body-sm text-faint" style={{ marginTop: 8 }}>
          Cloudflare-Tunnel: der reale Client-IP wird via <code>CF-Connecting-IP</code>-Header gematcht.
        </div>
      </Card>

      <Card title="Audit-Log Chain-Integrity" style={{ marginTop: 16 }} action={
        <Badge variant={data.audit_chain?.valid === false ? 'danger' : 'success'}>
          {data.audit_chain?.valid === false ? 'BROKEN' : 'INTAKT'}
        </Badge>
      }>
        <KvList items={[
          ['Geprüfte Zeilen (letzte 200)', data.audit_chain?.rows_checked ?? 0],
          ['Erste defekte ID', data.audit_chain?.first_break_id ?? '—'],
        ]}/>
        {data.audit_chain?.first_break_reason && (
          <div className="alert-banner alert-critical mt-8">
            <Icon name="alert"/>
            <div>{data.audit_chain.first_break_reason}</div>
          </div>
        )}
        <div className="t-body-sm text-muted" style={{ marginTop: 8 }}>
          SHA-256 Hash-Chain über jede AuditLog-Zeile. Direkter DB-Zugriff
          (Edit/Delete/Insert) wird beim Walk erkannt. Voller Walk via{' '}
          <code>GET /api/v1/audit/verify</code>.
        </div>
      </Card>
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
    { k: 'autopilot',   label: 'ML & Autopilot',   ic: 'zap' },
    { k: 'backtest',    label: 'Backtest',         ic: 'analytics' },
    { k: 'risk',        label: 'Risk Management',  ic: 'risk' },
    { k: 'safety',      label: 'Safety Dashboard', ic: 'lock' },
    { k: 'grader',      label: 'Trade Grader',     ic: 'zap' },
    { k: 'correlation', label: 'Correlation',      ic: 'analytics' },
    { k: 'macro',       label: 'Macro Events',     ic: 'bell' },
    { k: 'audit',       label: 'Audit & History',  ic: 'analytics' },
    { k: 'brokers',     label: 'Broker hinzufügen', ic: 'globe' },
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
        {page === 'autopilot'   && <MlAutopilotPage />}
        {page === 'backtest'    && <BacktestPage />}
        {page === 'risk'        && <RiskManagement live={live} onHalt={() => setHaltOpen(true)} />}
        {page === 'safety'      && <SafetyPage />}
        {page === 'grader'      && <GraderPage />}
        {page === 'correlation' && <CorrelationPage />}
        {page === 'macro'       && <MacroPage />}
        {page === 'audit'       && <AuditPage />}
        {page === 'brokers'     && <BrokersPage />}
        {page === 'settings'    && <Settings onReconfigure={() => setSetupOpen(true)} />}
      </main>

      <SetupModal open={setupOpen} onClose={() => setSetupOpen(false)} onDone={() => { setSetupOpen(false); setRefreshKey(k => k+1); }} />
      <HaltModal open={haltOpen} onClose={() => setHaltOpen(false)} positions={live.positions.positions} />
    </div>
  );
}

function App() { return <ToastHost><Shell /></ToastHost>; }

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
