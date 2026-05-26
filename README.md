# SERL — Self-Evolving API Rate Limiter

> A rate limiter that uses machine learning to automatically tune its own security limits in real time — no manual configuration needed.

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-teal)
![License](https://img.shields.io/badge/license-Academic-orange)

---

## What is this?

A normal rate limiter blocks users after a fixed number of requests — say 10 per minute — and that number never changes. If an attacker changes their pattern, the system cannot adapt.

**SERL is different.** It watches live traffic every 8 seconds, detects when something looks like an attack, and automatically adjusts its own blocking limit using machine learning. No human needs to touch anything.

> Think of it like a security guard who learns from experience. The more attacks he sees, the better he gets at stopping them.

---

## Live Demo

🌐 **Website:** https://gsunilkumarreddy23.pythonanywhere.com

The demo is a real Flask web app with a login and signup page. Try logging in normally — it works fine. Run the brute force simulator against it — you get blocked with HTTP 429. The dashboard on your local PC shows every decision the ML engine makes in real time.

---

## How it works — the full picture

```
                    ┌─────────────────────────────────┐
                    │         Your Flask Website       │
                    │   (hosted on PythonAnywhere)     │
                    └────────────┬────────────────────┘
                                 │ every login attempt
                                 ▼
                    ┌─────────────────────────────────┐
                    │       SERL Rate Limiter          │
                    │     (running on your PC)         │
                    │                                  │
                    │  1. Token Bucket checks request  │
                    │  2. Telemetry records the event  │
                    │  3. ML Engine evaluates every 8s │
                    │     → Z-Score: is this an attack?│
                    │     → Q-Learning: adjust limit?  │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │        Live Dashboard            │
                    │  Real-time charts, evolution log │
                    │  allow/deny feed, Q-states count │
                    └─────────────────────────────────┘
```

**In simple words:**
- Every login attempt goes through the rate limiter first
- The rate limiter decides: allow or block (HTTP 429)
- Everything is logged and sent to the ML engine
- The ML engine watches for patterns and changes the limit automatically
- The dashboard shows everything live as it happens

---

## Screenshots

### Normal login — user gets through
The login page shows the SERL status badge at the bottom. Green dot means the rate limiter is active. A real user logging in once uses 1 token from the bucket — no problem.

### Brute force blocked — attacker gets HTTP 429
When too many attempts fire from the same IP, the token bucket empties. The form shows the ACCESS BLOCKED message and the button is disabled. The attacker cannot submit any more requests.

### Live dashboard — attack in progress
- **Current Limit: 1** — ML tightened it from 10 down to 1 automatically
- **Deny Ratio: 73%** — 73 out of every 100 requests are being blocked
- **Recent Rate: 1.40 req/sec** — live traffic measurement
- **RL Q-States: 6** — the model has learned 6 different traffic situations so far
- The cyan line on the chart shows the request rate spiking above the red dashed limit line
- The bar chart shows red DENY bars dominating green ALLOW bars

### Recovery phase — system heals itself
After the attack slows down, the Q-learning agent sees the deny ratio dropping and relaxes the limit from 1 back up to 5 — automatically. Total requests climbed from 37 to 70 showing the system kept processing during the attack.

### ML Evolution Log + Request Log
Every decision the ML engine makes is recorded:
- `↓ Limit: 5 → 2 | HEAVY` — tightened because deny ratio was 71.8%
- `↓ Limit: 2 → 1 | HEAVY` — tightened again as attack continued
- `↑ Limit: 1 → 4 | HEAVY` — relaxed as traffic started easing

The request log shows each individual request — timestamp, client IP (49.42.233.190 in the demo), ALLOW or DENY badge, algorithm used, current limit, and rate per second.

---

## Features

| Feature | Description |
|---|---|
| Token Bucket Algorithm | Controls request flow — allows short bursts, blocks floods |
| Sliding Window Algorithm | Strict rolling window — switch live from the dashboard |
| Z-Score Anomaly Detection | Flags traffic spikes more than 2σ above average |
| Q-Learning RL Agent | Learns optimal limits by reward and penalty over time |
| Live Dashboard | Real-time charts, evolution log, request feed, algo switcher |
| Traffic Simulator | Generates normal, burst, attack, and mixed patterns |
| Switch Algorithm Live | Toggle between Token Bucket and Sliding Window with one click |
| Brute Force Simulator | Fires real login attempts at the live hosted website |
| ngrok Integration | Tunnels local rate limiter to the live PythonAnywhere site |

---

## Project Structure

```
SERL/
│
├── backend/
│   ├── __init__.py
│   ├── main.py          → FastAPI app — all API endpoints
│   │                      handles algo switching, request checking
│   ├── rate_limiter.py  → Token Bucket + Sliding Window algorithms
│   │                      thread-safe per-client state tracking
│   ├── ml_engine.py     → Z-Score anomaly detection + Q-Learning agent
│   │                      runs every 8 seconds in background thread
│   └── telemetry.py     → Records every request with full metadata
│                          provides stats and logs to dashboard
│
├── frontend/
│   └── dashboard.html   → Live dashboard — open in browser
│                          polls API every 2 seconds, no server needed
│
├── simulator/
│   ├── traffic_sim.py   → Sends traffic directly to local rate limiter
│   │                      patterns: normal, burst, attack, mixed
│   └── brute_sim.py     → Fires fake login attempts at live website
│                          phases: normal → brute force → recovery
│
├── run.py               → Starts the FastAPI server on port 8000
├── requirements.txt     → Python dependencies (FastAPI, uvicorn, requests)
└── README.md
```

---

## Algorithms explained

### Token Bucket (default)

```
Bucket starts with 10 tokens
Every request takes 1 token
Bucket refills slowly over time (1 token per second)
If bucket is empty → request is BLOCKED

Real user logs in once     → uses 1 token    → fine ✅
Attacker fires 50 requests → runs out at 10  → blocked ❌
```

Best for login and signup protection because real users rarely submit forms more than once or twice. Allows natural bursting behaviour while stopping floods.

### Sliding Window

```
Count requests in the last 10 seconds
If count > limit → BLOCK
Old requests automatically drop off as time passes

[sec1 sec2 sec3 sec4 sec5 sec6 sec7 sec8 sec9 sec10]
  req  req  req  req  req  req  req  req  req  req  req
  ← 11 requests in window, limit is 10 → BLOCKED ❌
```

Best for strict API enforcement where any burst is unacceptable. Switch to this live from the dashboard with the ⇄ SWITCH ALGO button.

---

## Machine Learning explained

### Z-Score Anomaly Detection

Maintains a rolling window of the last 30 request rates. Every 8 seconds it calculates:

```
z = (current_rate - mean) / standard_deviation

Normal rate average  = 1.0 req/sec
Sudden spike         = 15.0 req/sec
Z-score              = (15.0 - 1.0) / 3.6 = 3.8

3.8 > 2.0 threshold → ANOMALY DETECTED → traffic labelled ATTACK
```

### Q-Learning RL Agent

The agent runs every 8 seconds and picks one of 5 actions: adjust the limit by -3, -1, 0, +1, or +3.

```
State  = traffic_label + deny_ratio_bucket + limit_bucket
         e.g. "attack_high_mid"

Actions = [-3, -1, 0, +1, +3]   ← delta applied to current limit

Rewards:
  +2.0  deny ratio low      → system is responsive, good decision
  -3.0  deny ratio > 50%    → over-blocking or under-blocking, bad
  +0.5  limit stayed stable → stability bonus
  -1.0  limit dangerously low → penalise over-tightening
```

The agent builds a Q-table over time. Each new traffic situation it encounters becomes a new learned state. The Q-States counter on the dashboard shows how many it has learned.

### Traffic Classification

| Label | Condition | What the agent does |
|---|---|---|
| NORMAL | Low rate, low deny ratio | Relaxes limit gradually |
| QUIET | Rate below 0.05 req/sec | Holds limit, no action |
| BURST | Rate above 1.5 req/sec | Tightens limit slightly |
| HEAVY | Deny ratio above 30% | Tightens limit |
| ATTACK | Anomaly + deny ratio above 40% | Tightens limit aggressively |

---

## Setup and run

### 1. Clone the repo
```bash
git clone https://github.com/gsunilkumarreddy23/SERL.git
cd SERL
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the rate limiter server
```bash
python run.py
```

Server starts at `http://localhost:8000`

Interactive API docs at `http://localhost:8000/docs`

### 5. Open the dashboard
Double click `frontend/dashboard.html` in your browser.

The top right shows **LIVE** in green when connected to the server.

### 6. Run the traffic simulator
```bash
# Steady normal traffic (60 seconds)
python simulator/traffic_sim.py normal

# Sustained flood attack (60 seconds)
python simulator/traffic_sim.py attack

# Full demo — cycles normal → burst → attack → recovery
python simulator/traffic_sim.py mixed
```

---

## Running the live demo (with PythonAnywhere)

To show the rate limiter protecting a real hosted website:

**Step 1 — Start ngrok** to expose your local server to the internet:
```bash
.\ngrok http 8000
```
Copy the URL it gives you, e.g. `https://abc123.ngrok-free.app`

**Step 2 — Update PythonAnywhere** app.py with the ngrok URL:
```python
RATE_LIMITER_URL = "https://abc123.ngrok-free.app/api/request"
```
Then reload the web app on PythonAnywhere.

**Step 3 — Run the brute force simulator** against the live site:
```bash
python simulator/brute_sim.py https://gsunilkumarreddy23.pythonanywhere.com
```

Press ENTER when prompted. Watch the dashboard — every blocked attempt shows up in real time.

---

## API Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| POST | `/api/request` | Submit a request — rate limited, also handles algo switching |
| GET | `/api/status` | Returns current limit, algorithm, ML state, live stats |
| GET | `/api/logs?limit=100` | Recent request log with full metadata |
| GET | `/api/evolution-history` | Full history of ML-triggered limit changes |
| POST | `/api/reset` | Resets all state — telemetry, ML model, rate limiter |

---

## Demo walkthrough

What to show during a live evaluation:

**Phase 1 — Normal traffic (0–20s)**
Run `traffic_sim.py normal`. Dashboard shows steady low deny ratio, limit stays at 10, Q-states counter at 0. System is calm.

**Phase 2 — Brute force attack (20–50s)**
Simulator fires 12 requests per second. Watch the Evolution Log:
```
↓ Limit: 10 → 7 | ATTACK | anomaly detected (z=3.2)
↓ Limit: 7  → 4 | ATTACK | deny ratio=58.3%
↓ Limit: 4  → 1 | ATTACK | tightening limit by 3
```
Deny ratio climbs above 70%. Q-States counter grows as the agent learns new situations.

**Phase 3 — Recovery (50–70s)**
Attack stops. Watch the Evolution Log again:
```
↑ Limit: 1 → 4  | NORMAL | deny ratio=1.8% | relaxing by 3
↑ Limit: 4 → 7  | NORMAL | limit unchanged
```
Limit climbs back up automatically. No human touched anything.

**Show successful login**
Visit the live site, log in with valid credentials. Show the protected dashboard page that appears after login — proves legitimate users always get through.

---

## Key talking points

- The system detected the attack in under 8 seconds
- The limit adjusted itself — nobody changed any configuration
- The Q-table grows over time — the more traffic it sees, the smarter it gets
- Token Bucket and Sliding Window can be switched live with zero downtime
- Every single decision is logged with a reason — full audit trail

---

## Tech stack

| Technology | Version | Why |
|---|---|---|
| Python | 3.10+ | Core language |
| FastAPI | 0.111 | High-performance async API server |
| Uvicorn | 0.29 | ASGI server for FastAPI |
| Q-Learning | custom | RL agent for auto-tuning limits |
| Z-Score stats | stdlib math | Anomaly detection without heavy ML library |
| Chart.js | 4.4.1 | Live dashboard charts |
| Flask | 3.0.3 | Demo website frontend |
| ngrok | — | Public tunnel to local rate limiter |

---

## Limitations

- Data stored in memory — resets when server restarts
- Free PythonAnywhere hosting has limited capacity for heavy traffic
- Q-learning agent needs warm-up time — works better after seeing varied traffic
- ngrok URL changes every restart — must update PythonAnywhere app.py each session

---

## Team

| Roll Number | Institution |
|---|---|
| 202320117 | NIST Institute of Science and Technology |
| 202320115 | NIST Institute of Science and Technology |
| 202320147 | NIST Institute of Science and Technology |
| 202320108 | NIST Institute of Science and Technology |

**Guide:** Sir Bhabani Prasad Mishra

---

## References

```
[1] Preprints.org (2026). Design, Security Analysis, and Evaluation of
    Endpoint-Aware Token-Bucket Rate Limiting for Web APIs.
    Available at: https://www.preprints.org

[2] IJSAT Publication (2023). Hybrid Rate-Limiting Algorithms for
    Distributed Systems under High Traffic Spikes.
    International Journal of Science and Advanced Technology.
    Available at: https://www.ijsat.org

[3] MDPI Publication (2025). ML-Based Traffic Classification and
    Anomaly Detection for DDoS Mitigation. MDPI.
    Available at: https://www.mdpi.com
```

---

*Built as a research lab project — NIST Institute of Science and Technology*
