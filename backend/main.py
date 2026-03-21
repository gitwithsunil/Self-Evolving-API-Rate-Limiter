from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import threading
import json
import os
from datetime import datetime
from backend.rate_limiter import RateLimiterCore
from backend.ml_engine import MLEvolutionEngine
from backend.telemetry import TelemetryCollector

app = FastAPI(title="Self-Evolving API Rate Limiter", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
telemetry = TelemetryCollector()
rate_limiter = RateLimiterCore(telemetry=telemetry)
ml_engine = MLEvolutionEngine(rate_limiter=rate_limiter, telemetry=telemetry)

# Start ML engine background loop
ml_thread = threading.Thread(target=ml_engine.run_loop, daemon=True)
ml_thread.start()


@app.post("/api/request")
async def handle_request(request: Request):
    """Main endpoint — rate limits every incoming request."""
    client_ip = request.client.host
    body = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
        except Exception:
            body = {}

    client_id = body.get("client_id", client_ip)

    # ── Algorithm switch from dashboard ──────────────────────────────
    if body.get("algorithm"):
        new_algo = body.get("algorithm")
        if new_algo in ("token_bucket", "sliding_window"):
            rate_limiter.set_limit(rate_limiter.limit, algorithm=new_algo)
            return JSONResponse({
                "status": "algo_switched",
                "algorithm": new_algo,
                "limit": rate_limiter.limit,
            })

    # ── Normal rate limit check ───────────────────────────────────────
    allowed, info = rate_limiter.check(client_id)

    telemetry.record(
        client_id=client_id,
        allowed=allowed,
        algorithm=info["algorithm"],
        limit=info["limit"],
        current_rate=info["current_rate"],
    )

    if allowed:
        return JSONResponse({"status": "allowed", "client_id": client_id, **info})
    else:
        return JSONResponse({"status": "denied", "client_id": client_id, **info}, status_code=429)


@app.get("/api/status")
def get_status():
    """Returns current limiter config, ML model state, and live stats."""
    return {
        "limiter_config": rate_limiter.get_config(),
        "ml_state": ml_engine.get_state(),
        "stats": telemetry.get_stats(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/logs")
def get_logs(limit: int = 100):
    """Returns recent decision logs for the dashboard."""
    return {"logs": telemetry.get_recent_logs(limit)}


@app.get("/api/evolution-history")
def get_evolution_history():
    """Returns the history of ML-triggered limit changes."""
    return {"history": ml_engine.get_evolution_history()}


@app.post("/api/reset")
def reset():
    """Resets all state — useful for demos."""
    telemetry.reset()
    rate_limiter.reset()
    ml_engine.reset()
    return {"status": "reset complete"}