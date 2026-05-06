# Trade-Claw Autopilot — Setup-Anleitung

End-to-End-Anleitung für TradingView-Webhook → Cloudflare-Tunnel → Trade-Claw-Autopilot.
Schrittweise, mit allen JSON-Beispielen, sodass du das später ohne Nachforschung wieder einrichten kannst.

> ⚠️ **Bevor du irgendetwas auf Live schaltest:** Erst Dry-Run, dann Backtest des aktiven ML-Modells (`Backtest`-Tab), dann erst Live. Niemals umgekehrt.

---

## Übersicht — wie das Ganze zusammenspielt

```
   TradingView (Pine-Alert)
         │
         │  HTTPS POST {"symbol":..., "side":..., ...}
         ▼
   Cloudflare-Tunnel  ──►  https://<dein-subdomain>.trycloudflare.com
         │
         │  forward to localhost:8000
         ▼
   Trade-Claw FastAPI  /api/v1/webhook/tradingview/<TV_WEBHOOK_SECRET>
         │
         ├──►  Secret-Check (Constant-Time)
         ├──►  Payload-Validation
         ├──►  Trade Grader (7-Kriterien → A+/A/B/...)
         ├──►  ML-Score (aktives Modell)
         ├──►  Risk-Engine (Drawdown, Position-Size, Halted?)
         └──►  Order-Submit (nur wenn alle Gates grün und Mode=live)
```

Alle Phasen lassen sich einzeln stoppen: Autopilot-`off` blockt den Webhook,
`dry_run` validiert ohne Submit, der UI-Halt-Button cancelt sofort alles.

---

## Schritt 1 — `.env` konfigurieren

Im Projekt-Root: `.env` öffnen und folgendes setzen.

```bash
# Pflicht: API-Key fürs eigene UI / API-Calls
TRADE_CLAW_API_KEY=ein-langer-zufallswert-deiner-wahl

# Pflicht: Webhook-Geheimnis. Der Wert wird Teil der URL und ist die einzige
# Authentisierung gegenüber TradingView. Generiere via:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
TV_WEBHOOK_SECRET=8eD2k7Pq-ReplaceMe-aZ4mB1s9XpHy3WgRtV0LfNcK6JuQ

# ML-Gate
#   off       → Score wird nur protokolliert, kein Block
#   advisory  → Score wird angezeigt, kein Block (Default — sicher zum Beobachten)
#   enforce   → unterhalb ML_THRESHOLD wird der Submit abgelehnt (erst aktivieren
#               wenn der Backtest des aktiven Modells positiv aussieht!)
ML_GATE_MODE=advisory
ML_THRESHOLD=0.5
```

> 🔒 Sicherheit: Niemals `.env` committen. Sie steht in `.gitignore`. Wenn du
> die Datei mit Cloud-Sync (Dropbox, OneDrive) liegen hast, achte darauf,
> dass nur dein Account Zugriff hat — der Inhalt ist im Klartext.

---

## Schritt 2 — Cloudflare-Tunnel installieren

Cloudflare-Tunnel (`cloudflared`) gibt deinem lokalen Server eine echte
HTTPS-URL, die TradingView erreichen kann. Kostenlos, kein Konto nötig für
„Quick Tunnels" (siehe Hinweis am Ende für persistente URLs).

### macOS

```bash
brew install cloudflared
```

### Windows

1. Lade `cloudflared.exe` von <https://github.com/cloudflare/cloudflared/releases>
2. Speichere es z.B. unter `C:\Users\simsi\bin\cloudflared.exe`
3. Optional: dieses Verzeichnis zur `PATH`-Variable hinzufügen, dann kannst
   du `cloudflared` direkt im Terminal aufrufen.

### Alternative: ngrok

Wenn du bereits einen ngrok-Account hast, geht das genauso:
`ngrok http 8000`. Du bekommst eine `https://<id>.ngrok-free.app`-URL. Der
Rest der Anleitung gilt analog.

---

## Schritt 3 — Trade-Claw starten + Tunnel hochziehen

**Terminal 1 — Trade-Claw:**

- Windows: Doppelklick auf `start-app.bat`
- macOS:   Doppelklick auf `start-app.command`

Sobald die UI im Browser öffnet (`http://localhost:8000/app/`), läuft der Backend-Port.

**Terminal 2 — Tunnel:**

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflared gibt dir eine URL wie:

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at:                                          |
|  https://surprised-elements-buying-iv.trycloudflare.com                                    |
+--------------------------------------------------------------------------------------------+
```

Diese URL ist deine **Webhook-Basis**. Hänge dahinter:

```
https://surprised-elements-buying-iv.trycloudflare.com/api/v1/webhook/tradingview/<TV_WEBHOOK_SECRET>
```

Notiere dir die volle URL — die brauchst du in TradingView.

> 💡 Quick Tunnels ändern ihre URL bei jedem Neustart von `cloudflared`.
> Wenn du eine **stabile** URL willst (z.B. weil dein Bot 24/7 laufen soll),
> brauchst du einen Cloudflare-Account + eine eigene Domain. Doku:
> <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/>

---

## Schritt 4 — Webhook lokal testen (vor TradingView)

Bevor du in TradingView die Alerts setzt, vergewissere dich, dass der
Webhook-Pfad funktioniert. Im Trade-Claw-UI: Sidebar → **ML & Autopilot**:

1. Mode auf **Dry-Run** stellen
2. Session auswählen (oder neu erstellen, Mock-Broker reicht)
3. Im Terminal:

```bash
SECRET=8eD2k7Pq-ReplaceMe-aZ4mB1s9XpHy3WgRtV0LfNcK6JuQ
curl -X POST "http://localhost:8000/api/v1/webhook/tradingview/$SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EUR_USD",
    "side": "BUY",
    "entry": 1.0850,
    "stop_loss": 1.0820,
    "take_profit": 1.0920,
    "size": 1000,
    "grading_criteria": {
      "structural_level": true,
      "liquidity_sweep": true,
      "momentum": true,
      "volume": true,
      "macro_alignment": true,
      "no_contradiction": true
    },
    "macro_aligned": true,
    "confidence": 80
  }'
```

Erwartete Antwort (Auszug):

```json
{
  "decision": "approved_dry_run",
  "grade": "A+",
  "score_7": 7,
  "size": 1000,
  ...
}
```

Wenn du stattdessen `"decision": "rejected"` mit `"reasons": ["autopilot session_id not configured"]` siehst → im UI eine Session auswählen und nochmal probieren.

Sobald das funktioniert, ersetze in `curl` die URL durch die Cloudflared-URL — gleich antworten? Dann ist der Tunnel ok und du kannst weiter zu TradingView.

---

## Schritt 5 — TradingView-Alert konfigurieren

### 5.1 — Alert öffnen

In TradingView:

1. Chart öffnen (z.B. EURUSD, BTCUSD, XAUUSD)
2. Auf das Glockensymbol klicken oder `Alt+A`
3. **„Alert Erstellen"**

### 5.2 — Trigger-Bedingung

- **Bedingung:** Wähle einen Indikator oder „Crossing Up/Down" auf einem
  Strategy- oder Pine-Indicator. Wenn du keine Strategie hast, geht auch
  ein einfacher Crossover (RSI < 30, EMA-Cross, etc.).
- **Optionen → „Webhook URL":**
  ```
  https://surprised-elements-buying-iv.trycloudflare.com/api/v1/webhook/tradingview/8eD2k7Pq-ReplaceMe-aZ4mB1s9XpHy3WgRtV0LfNcK6JuQ
  ```
- **Nachricht (Body):** Hier kommt das JSON aus Schritt 6 hin. TradingView
  Pine-Variablen wie `{{close}}`, `{{ticker}}`, `{{strategy.order.action}}`
  werden zur Laufzeit ersetzt.

### 5.3 — Wichtig: Notification-Setup

Setze **NUR** „Webhook URL" als Notification — keine E-Mail, keine
Push-Notification, sonst sendet TradingView den Alert mehrfach.

### 5.4 — Trigger-Frequenz

- „Once Per Bar Close" (empfohlen) → ein Trade pro fertigem Candle
- „Once Per Bar" → kann pro Candle mehrfach feuern, vorsichtig

---

## Schritt 6 — Pine-Alert-JSON-Vorlagen

Trade-Claw akzeptiert diese Felder:

| Feld | Pflicht | Beschreibung |
|------|---------|--------------|
| `symbol` | ja | Symbol-Code, MUSS zum Broker passen (Mock akzeptiert `EUR_USD`, `BTC_USD`, etc.) |
| `side` | ja | `BUY` oder `SELL` (auch `LONG` / `SHORT` werden akzeptiert) |
| `entry` | ja | Einstiegspreis |
| `stop_loss` | ja | SL-Preis |
| `take_profit` | ja | TP-Preis |
| `size` | nein | Position-Size; wenn weggelassen, rechnet Trade-Claw 2% Risk |
| `confidence` | nein | 0–100, beeinflusst den Grade |
| `grading_criteria` | nein | Boolean-Map mit den 7 Kriterien |
| `macro_aligned` | nein | Macro-Aligned-Flag (überschreibt grading_criteria.macro_alignment) |

### 6.1 — Forex (Long, EURUSD)

```json
{
  "symbol": "EUR_USD",
  "side": "BUY",
  "entry": {{close}},
  "stop_loss": {{close}} - 0.0030,
  "take_profit": {{close}} + 0.0090,
  "size": 1000,
  "confidence": 75,
  "grading_criteria": {
    "structural_level": true,
    "liquidity_sweep": true,
    "momentum": true,
    "volume": true,
    "macro_alignment": true,
    "no_contradiction": true
  },
  "macro_aligned": true
}
```

> R/R hier: 30 Pips Risk vs 90 Pips Reward = 1:3. Trade-Claw blockt sonst
> wegen R/R-Hard-Gate.

### 6.2 — Forex (Short, GBPUSD)

```json
{
  "symbol": "GBP_USD",
  "side": "SELL",
  "entry": {{close}},
  "stop_loss": {{close}} + 0.0040,
  "take_profit": {{close}} - 0.0120,
  "size": 1000,
  "confidence": 70,
  "grading_criteria": {
    "structural_level": true,
    "liquidity_sweep": true,
    "momentum": true,
    "volume": true,
    "macro_alignment": false,
    "no_contradiction": true
  }
}
```

### 6.3 — Crypto (Long, BTCUSD)

```json
{
  "symbol": "BTC_USD",
  "side": "BUY",
  "entry": {{close}},
  "stop_loss": {{close}} * 0.97,
  "take_profit": {{close}} * 1.09,
  "confidence": 80,
  "grading_criteria": {
    "structural_level": true,
    "liquidity_sweep": true,
    "momentum": true,
    "volume": true,
    "macro_alignment": true,
    "no_contradiction": true
  },
  "macro_aligned": true
}
```

> 3% SL + 9% TP = 1:3 R/R. Crypto-Volatilität braucht typischerweise
> wider gesetzte Stops als Forex.

### 6.4 — Crypto (Short, ETHUSD)

```json
{
  "symbol": "ETH_USD",
  "side": "SELL",
  "entry": {{close}},
  "stop_loss": {{close}} * 1.03,
  "take_profit": {{close}} * 0.91,
  "confidence": 70
}
```

### 6.5 — Edelmetalle (Long, XAUUSD = Gold)

```json
{
  "symbol": "XAU_USD",
  "side": "BUY",
  "entry": {{close}},
  "stop_loss": {{close}} - 15,
  "take_profit": {{close}} + 45,
  "size": 0.1,
  "confidence": 75,
  "grading_criteria": {
    "structural_level": true,
    "momentum": true,
    "volume": true,
    "macro_alignment": true
  },
  "macro_aligned": true
}
```

> 15 USD SL + 45 USD TP = 1:3. Gold wird typisch in Lots à 100 oz gehandelt;
> `size: 0.1` = 10 oz = 1 Mini-Lot. Bei deinem Live-Broker passt du das an.

### 6.6 — Strategy-Plugin-Variante (`{{strategy.order.action}}`)

Wenn du eine Pine-Strategy mit `strategy.entry()` / `strategy.exit()` hast,
kannst du den Side dynamisch befüllen:

```json
{
  "symbol": "{{ticker}}",
  "side": "{{strategy.order.action}}",
  "entry": {{strategy.order.price}},
  "stop_loss": {{plot_0}},
  "take_profit": {{plot_1}},
  "confidence": 75
}
```

Voraussetzung: Im Pine-Script die zwei `plot()`-Calls als SL/TP exposen.
Beispiel:

```pine
//@version=5
strategy("Trade-Claw Sender", overlay=true)
length = input.int(20, "EMA")
ema = ta.ema(close, length)
longCondition  = ta.crossover(close, ema)
shortCondition = ta.crossunder(close, ema)

if longCondition
    strategy.entry("L", strategy.long, comment="LONG")
if shortCondition
    strategy.entry("S", strategy.short, comment="SHORT")

atr = ta.atr(14)
sl = strategy.position_avg_price - atr * 1.5
tp = strategy.position_avg_price + atr * 4.5
plot(sl, "sl", color=color.red,   display=display.none)
plot(tp, "tp", color=color.green, display=display.none)
```

---

## Schritt 7 — Autopilot scharf stellen (graduell!)

Im UI: **Sidebar → ML & Autopilot**.

### Stufe 1 — `dry_run` (mind. 1 Tag)

- Mode → **Dry-Run**
- Beobachte den **Verlauf** (`history` im Status). Jeder eingehende Webhook
  schreibt einen Eintrag mit `decision`, `grade`, `score_7`, ggf. Reasons.
- Beobachtungspunkte:
  - Wieviele Signale kommen?
  - Wieviele werden vom Grader auf B/C runtergestuft (= im Live-Modus
    abgelehnt)?
  - Wie hoch ist der durchschnittliche ML-Score?

### Stufe 2 — Backtest des aktiven Modells

- Sidebar → **Backtest**
- Wähle „Symbole" passend zu deinem Stil (Default = Forex+Crypto+Metalle)
- Period 2y, Threshold 0.5
- Wenn das Resultat negativ ist (ROI < 0, Win-Rate niedrig), **bleib in
  Dry-Run und sammle mehr Live-Outcomes**, dann retraine. Aktiviere die
  Live-Stufe erst, wenn der Backtest zumindest knapp positiv ist.

### Stufe 3 — `live` (klein)

- Mode → **LIVE** (zweite Bestätigung im Browser-Dialog)
- ML_GATE_MODE in `.env` weiterhin auf `advisory` lassen
- Position-Size klein halten (z.B. 0.5% Risk statt 2%)
- Mehrere Tage live laufen lassen, Trades nachvollziehen

### Stufe 4 — `enforce`

- `.env`: `ML_GATE_MODE=enforce`, `ML_THRESHOLD=0.5` oder höher
- Trade-Claw neu starten
- Jetzt blockt die Risk-Engine Submits unter Threshold automatisch

---

## Notbremsen

| Was | Wie |
|-----|-----|
| Sofort alle Trades stoppen | UI: **Risk Management → EMERGENCY HALT**. Cancelt alle offenen Orders, setzt Session auf halted, Risk-Engine refused weitere Submits. |
| Webhook deaktivieren | `.env`: `TV_WEBHOOK_SECRET=` (leer). App neu starten. Alle eingehenden Webhooks → 401. |
| Autopilot pausieren | UI: **ML & Autopilot → Mode: Aus**. Webhooks werden empfangen, aber als `ignored` protokolliert. |
| Tunnel beenden | Terminal mit `cloudflared` → `Ctrl+C`. Sofort offline. |

---

## Troubleshooting

**TradingView sendet, aber Trade-Claw bekommt nichts**
- Cloudflared-Terminal: bekommt der Tunnel überhaupt Requests? (loggt jede Anfrage)
- TradingView-Alert: „History"-Reiter zeigt für jeden Alert den HTTP-Statuscode. 401 = falscher Secret. 422 = Payload kaputt.
- Ist Trade-Claw selbst noch erreichbar? `curl http://localhost:8000/health`

**Webhook kommt durch, aber `decision: ignored`**
- Autopilot ist auf `off`. UI → ML & Autopilot → Mode wechseln.

**Webhook kommt durch, aber `decision: rejected`**
- `reasons`-Feld lesen. Häufig:
  - `"autopilot session_id not configured"` → Im UI Session auswählen
  - `"grade B not in ('A+', 'A')"` → Setup hatte zu wenig Kriterien erfüllt; entweder mehr `grading_criteria: true` schicken oder im UI `require_grade` lockern
  - `"submit refused: Order rejected: ..."` → Risk-Engine hat geblockt; meist Drawdown- oder Halted-Limit

**Mock-Trades resolven nicht zu WIN/LOSS**
- Im UI **ML & Autopilot → Outcomes**: bleibt `outcome: open` für mehr als 10 Sek?
- Server-Log checken: `Outcome poller iteration failed`?
- Ist die `OUTCOME_POLL_SECONDS` in `.env` zu hoch?

**ML-Backtest sagt 0% ROI / 0 Trades**
- Threshold zu hoch. Im **Backtest**-Tab Threshold runter (0.3 erstmal), schauen wo die Score-Distribution liegt.

---

## Referenz: Webhook-Payload-Schema

Vollständige akzeptierte Form (alle Felder explizit):

```json
{
  "symbol": "EUR_USD",
  "side": "BUY",
  "entry": 1.0850,
  "stop_loss": 1.0820,
  "take_profit": 1.0920,
  "size": 1000,
  "confidence": 80,
  "grading_criteria": {
    "structural_level": true,
    "liquidity_sweep": true,
    "momentum": true,
    "volume": true,
    "risk_reward": true,
    "macro_alignment": true,
    "no_contradiction": true
  },
  "macro_aligned": true
}
```

`size` ist optional — wenn weggelassen, rechnet Trade-Claw aus dem
gemeldeten Account-Balance × 2% Risk / SL-Distanz die Größe selbst.

---

## Referenz: Antwort-Schema

```json
{
  "received_at": "2026-05-06T13:42:00.000Z",
  "mode": "live",
  "decision": "submitted",
  "reasons": [],
  "signal": {
    "symbol": "EUR_USD",
    "side": "BUY",
    "entry": 1.0850,
    "stop_loss": 1.0820,
    "take_profit": 1.0920,
    "size": 1000
  },
  "grade": "A+",
  "score_7": 7,
  "size": 1000,
  "order_id": "mock_b983256359a3",
  "ml_score": 0.95
}
```

Mögliche `decision`-Werte:

- `ignored` — Autopilot ist `off`
- `rejected` — Payload, Grade, Risk oder Submit hat geblockt; Details in `reasons`
- `approved_dry_run` — Pipeline grün, aber Mode ist `dry_run`, kein Submit
- `submitted` — Order tatsächlich an Broker geschickt
