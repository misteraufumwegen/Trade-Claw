// Trade-Claw — Mock data and small helpers

const FX_PAIRS = ['EUR/USD','GBP/USD','USD/JPY','USD/CHF','EUR/GBP','EUR/JPY','AUD/USD','NZD/USD','USD/CAD','GBP/JPY'];

const POSITIONS = [
  {
    id: 'p1', asset: 'EUR/USD', dir: 'BUY',
    entry: 1.0842, sl: 1.0815, tp: 1.0890,
    size: 2.1, pnl: 420, grade: 'A',
    timeOpen: '2h 15m', updated: 'jetzt',
  },
  {
    id: 'p2', asset: 'GBP/USD', dir: 'SELL',
    entry: 1.2650, sl: 1.2680, tp: 1.2590,
    size: 1.8, pnl: -185, grade: 'A+',
    timeOpen: '45m', updated: 'vor 3m',
  },
  {
    id: 'p3', asset: 'USD/JPY', dir: 'BUY',
    entry: 149.25, sl: 148.90, tp: 150.50,
    size: 2.3, pnl: 890, grade: 'B',
    timeOpen: '12m', updated: 'vor 1m',
  },
];

const MACRO_EVENTS = [
  { time: '12:30', when: 'in 5m', country: 'EU', event: 'EZB Zinsentscheidung', impact: 'HIGH', forecast: 'Erwartet: 4.50%' },
  { time: '13:00', when: 'in 35m', country: 'US', event: 'US Jobs Report (NFP)', impact: 'HIGH', forecast: 'Forecast: +150K' },
  { time: '14:30', when: 'in 95m', country: 'US', event: 'US CPI', impact: 'HIGH', forecast: 'Forecast: +0.3%' },
  { time: '16:00', when: 'in 125m', country: 'EU', event: 'EU Einzelhandelsumsätze', impact: 'MEDIUM', forecast: 'Forecast: −0.1%' },
  { time: '17:30', when: 'in 215m', country: 'CA', event: 'BoC Pressekonferenz', impact: 'MEDIUM', forecast: '' },
  { time: '21:00', when: 'in 5h', country: 'US', event: 'FOMC Minutes', impact: 'LOW', forecast: '' },
];

const ALERTS = [
  { type: 'critical', t: '12:45', msg: 'Drawdown −12.4% (Schwelle: −15%)' },
  { type: 'warning',  t: '12:43', msg: 'EUR-GBP Korrelation 88% (Max: 85%)' },
  { type: 'info',     t: '12:40', msg: 'Trade ausgeführt — EUR/USD, Grade A' },
  { type: 'info',     t: '12:35', msg: 'Macro Event — EZB Zinsentscheidung in 5m' },
  { type: 'info',     t: '12:22', msg: 'API Connection re-validiert' },
];

const TRADE_HISTORY = [
  { n: 37, asset: 'EUR/USD', dir: 'BUY',  entry: 1.0842, exit: 1.0867, sl: 1.0815, tp: 1.0890, pnl:  315, grade: 'A',  date: '28 Apr' },
  { n: 36, asset: 'GBP/USD', dir: 'SELL', entry: 1.2650, exit: 1.2620, sl: 1.2680, tp: 1.2590, pnl:  450, grade: 'A+', date: '28 Apr' },
  { n: 35, asset: 'USD/JPY', dir: 'BUY',  entry: 149.25, exit: 149.80, sl: 148.90, tp: 150.50, pnl:  275, grade: 'A',  date: '27 Apr' },
  { n: 34, asset: 'EUR/USD', dir: 'SELL', entry: 1.0890, exit: 1.0865, sl: 1.0915, tp: 1.0820, pnl:  180, grade: 'B',  date: '27 Apr' },
  { n: 33, asset: 'NZD/USD', dir: 'BUY',  entry: 0.6185, exit: 0.6195, sl: 0.6150, tp: 0.6220, pnl:   60, grade: 'B',  date: '26 Apr' },
  { n: 32, asset: 'AUD/CAD', dir: 'SELL', entry: 0.9142, exit: 0.9120, sl: 0.9165, tp: 0.9100, pnl: -110, grade: 'B',  date: '26 Apr' },
  { n: 31, asset: 'EUR/USD', dir: 'BUY',  entry: 1.0720, exit: 1.0695, sl: 1.0690, tp: 1.0750, pnl: -420, grade: 'A',  date: '25 Apr' },
  { n: 30, asset: 'GBP/JPY', dir: 'BUY',  entry: 190.30, exit: 188.90, sl: 192.50, tp: 185.00, pnl: -700, grade: 'A+', date: '24 Apr' },
  { n: 29, asset: 'USD/CHF', dir: 'BUY',  entry: 0.8820, exit: 0.8855, sl: 0.8790, tp: 0.8870, pnl:  220, grade: 'A',  date: '23 Apr' },
  { n: 28, asset: 'EUR/JPY', dir: 'SELL', entry: 161.20, exit: 160.40, sl: 161.80, tp: 159.50, pnl:  340, grade: 'A',  date: '22 Apr' },
];

// Correlation matrix: rows/cols share order
const CORR_ASSETS = ['EUR','GBP','USD','JPY','CHF','AUD','CAD'];
const CORR_MATRIX = [
  [100, 88, 12, 75, 45, 62, 38],
  [ 88,100,  8, 82, 52, 58, 42],
  [ 12,  8,100, 25, 78, 22, 65],
  [ 75, 82, 25,100, 38, 48, 35],
  [ 45, 52, 78, 38,100, 32, 60],
  [ 62, 58, 22, 48, 32,100, 55],
  [ 38, 42, 65, 35, 60, 55,100],
];

// Helpers
function fmtUsd(n) {
  const sign = n >= 0 ? '+' : '−';
  const abs = Math.abs(n);
  return `${sign}$${abs.toLocaleString('en-US',{minimumFractionDigits: abs % 1 ? 2 : 0, maximumFractionDigits: 2})}`;
}
function pnlClass(n) { return n > 0 ? 'text-success' : n < 0 ? 'text-danger' : 'text-muted'; }

function corrColor(v) {
  if (v >= 100) return { bg: 'var(--neutral-600)', fg: 'var(--neutral-400)' };
  if (v >= 90) return { bg: 'rgba(244,67,54,0.55)', fg: '#fff' };
  if (v >= 70) return { bg: 'rgba(255,152,0,0.50)', fg: '#fff' };
  if (v >= 50) return { bg: 'rgba(255,193,7,0.30)', fg: 'var(--warning-200)' };
  return { bg: 'rgba(76,175,80,0.20)', fg: 'var(--success-200)' };
}

// Tiny SVG sparkline
function makeSparkline(values, { width = 120, height = 32, stroke = '#42A5F5', fill = 'rgba(66,165,245,0.15)' } = {}) {
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const stepX = width / (values.length - 1);
  const points = values.map((v, i) => [i * stepX, height - ((v - min) / range) * height]);
  const path = points.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(' ');
  const area = `${path} L ${width} ${height} L 0 ${height} Z`;
  return `<svg class="spark" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
    <path d="${area}" fill="${fill}" />
    <path d="${path}" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  </svg>`;
}

Object.assign(window, {
  FX_PAIRS, POSITIONS, MACRO_EVENTS, ALERTS, TRADE_HISTORY,
  CORR_ASSETS, CORR_MATRIX, fmtUsd, pnlClass, corrColor, makeSparkline,
});
