# SERL — Self-Evolving API Rate Limiter

> A rate limiter that uses machine learning to automatically tune its own security limits — no manual configuration needed.

---

## What is this project?

A normal rate limiter blocks users after a fixed number of requests (like 10 per minute) — forever. It never changes.

**SERL is different.** It watches live traffic, detects attacks automatically, and adjusts its own limits every 8 seconds using machine learning. During an attack it tightens the limit. When traffic is normal it relaxes back — all by itself.

---

## Live Demo

🌐 **Website:** https://gsunilkumarreddy23.pythonanywhere.com

The demo website has a login and signup page protected by SERL. Try logging in normally — it works fine. Try spamming it — you get blocked.

---

## How It Works

```
Requests come in
      ↓
Rate Limiter checks (Token Bucket or Sliding Window)
      ↓
Telemetry records every request
      ↓
ML Engine runs every 8 seconds
  → Z-Score detects if traffic is abnormal
  → Q-Learning agent decides: tighten / hold / relax
      ↓
Limit updates automatically
      ↓
Dashboard shows everything live
```

---

## Features

- **Token Bucket Algorithm** — allows short bursts, blocks floods instantly
- **Sliding Window Algorithm** — strict rolling window counter
- **Z-Score Anomaly Detection** — detects traffic spikes automatically
- **Q-Learning RL Agent** — learns optimal limits over time
- **Live Dashboard** — real-time charts, evolution log, request feed
- **Traffic Simulator** — generates normal, burst, attack, and mixed patterns
- **Switch Algorithm Live** — toggle between Token Bucket and Sliding Window from the dashboard

---

## Project Structure

```
SERL/
├── backend/
│   ├── main.py          → FastAPI server (all API endpoints)
│   ├── rate_limiter.py  → Token Bucket + Sliding Window algorithms
│   ├── ml_engine.py     → Z-Score detection + Q-Learning agent
│   └── telemetry.py     → Records and stores all request logs
├── frontend/
│   └── dashboard.html   → Live dashboard (open in browser)
├── simulator/
│   ├── traffic_sim.py   → Sends traffic to local rate limiter
│   └── brute_sim.py     → Simulates brute force on live website
├── run.py               → Start the server
├── requirements.txt     → Python dependencies
└── README.md
```

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core language |
| FastAPI | Backend API server |
| Q-Learning | RL agent for auto-tuning |
| Z-Score Statistics | Anomaly detection |
| Chart.js | Live dashboard charts |
| Flask | Demo website (on PythonAnywhere) |
| ngrok | Tunnel local server to internet |

---

## Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/gsunilkumarreddy23/SERL.git
cd SERL
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
NOTE: run each file in different Terminal 
also RUN ngrok before starting the attck 

### 4. Start the rate limiter
```bash
python run.py
```
Server starts at: `http://localhost:8000`

API docs at: `http://localhost:8000/docs`

### 5. Open the dashboard
Double click `frontend/dashboard.html` in your browser.

### 6. Run the traffic simulator
```bash
# Normal traffic(For Better result run any one attack)
python simulator/traffic_sim.py normal

# Brute force attack
python simulator/traffic_sim.py attack

# Full demo (cycles through all patterns)
python simulator/traffic_sim.py mixed
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/request` | Submit a request (rate limited) |
| GET | `/api/status` | Current config, ML state, live stats |
| GET | `/api/logs` | Recent request log |
| GET | `/api/evolution-history` | ML limit change history |
| POST | `/api/reset` | Reset all state |

---

## Demo — What to Watch

**Phase 1 — Normal traffic:**
Dashboard shows steady green charts. Deny ratio near 0%.

**Phase 2 — Brute force attack:**
Deny ratio spikes. Evolution Log shows ML tightening the limit automatically.
```
↓ Limit: 10 → 7 | ATTACK | anomaly detected (z=3.2)
↓ Limit: 7  → 4 | ATTACK | deny ratio=58.3%
Here You can try login to my refered website , It will show acess blocked/IP blocked 
```

**Phase 3 — Recovery:**
Attack stops. ML agent relaxes the limit back up automatically.
```
↑ Limit: 4 → 7  | NORMAL | deny ratio=1.8%
↑ Limit: 7 → 9  | NORMAL | limit unchanged
```

---

## Algorithms Explained

### Token Bucket
Each client gets a bucket of 10 tokens. Every request uses 1 token. Bucket refills slowly over time. If empty → blocked.
- Best for: Login and signup protection

### Sliding Window
Counts requests made in the last 10 seconds. If count exceeds limit → blocked. Old requests automatically drop off.
- Best for: Strict API rate enforcement

### Z-Score Anomaly Detection
Maintains a rolling average of request rates. If current rate deviates more than 2 standard deviations → anomaly flagged → limit tightened.

### Q-Learning Agent
Learns by trial and error every 8 seconds:
- **State:** traffic label + deny ratio + current limit
- **Actions:** adjust limit by -3, -1, 0, +1, +3
- **Reward:** +2 for low deny ratio, -3 for over-blocking
- Builds a Q-table over time — gets smarter with more traffic

---


## License

This project is built for academic/research purposes under NIST University lab guidelines.
