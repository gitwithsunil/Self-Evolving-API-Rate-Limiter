"""
Traffic Simulator
=================
Sends different traffic patterns to the rate limiter API.
Run this in a separate terminal while the server is running.

Usage:
    python simulator/traffic_sim.py [pattern]
    //will use only if you not testing on live sites.

Patterns:
    normal  — steady 1 req/sec per client (default)
    burst   — sudden spike to 20 req/sec
    attack  — sustained flood from one IP
    mixed   — cycles through all patterns automatically
    
"""

import sys
import time
import random
import threading
import requests

BASE_URL = "http://localhost:8000"
CLIENTS = ["alice", "bob", "charlie", "eve", "mallory"]


def send_request(client_id: str) -> dict:
    try:
        resp = requests.post(
            f"{BASE_URL}/api/request",
            json={"client_id": client_id},
            timeout=3
        )
        status = "✅ ALLOW" if resp.status_code == 200 else "❌ DENY "
        data = resp.json()
        print(f"  {status} | client={client_id:10s} | limit={data.get('limit'):3} | rate={data.get('current_rate', 0):.2f}/s")
        return data
    except Exception as e:
        print(f"  [error] {e}")
        return {}


def pattern_normal(duration=30):
    """Steady traffic — 1 req/sec from each of 3 clients."""
    print("\n[NORMAL] Steady traffic (1 req/s × 3 clients)")
    end = time.time() + duration
    while time.time() < end:
        for client in random.sample(CLIENTS[:3], 3):
            threading.Thread(target=send_request, args=(client,)).start()
            time.sleep(0.33)


def pattern_burst(duration=20):
    """Short burst — 15 req/s from one client."""
    print("\n[BURST] Spike traffic from 'eve'")
    end = time.time() + duration
    while time.time() < end:
        threading.Thread(target=send_request, args=("eve",)).start()
        time.sleep(0.07)


def pattern_attack(duration=30):
    """Sustained flood — 25 req/s from 'mallory'."""
    print("\n[ATTACK] Sustained flood from 'mallory'")
    end = time.time() + duration
    while time.time() < end:
        threading.Thread(target=send_request, args=("mallory",)).start()
        time.sleep(0.04)


def pattern_mixed():
    """Cycles through all patterns to show the system self-evolving."""
    print("\n[MIXED] Demo mode — cycling through all patterns")
    print("  Phase 1: Normal (30s)")
    pattern_normal(30)
    print("\n  Phase 2: Burst attack (20s)")
    pattern_burst(20)
    print("\n  Phase 3: Sustained DDoS (30s)")
    pattern_attack(30)
    print("\n  Phase 4: Recovery to normal (30s)")
    pattern_normal(30)
    print("\n[MIXED] Demo complete. Check the dashboard!")


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "normal"
    print(f"=== Self-Evolving Rate Limiter — Traffic Simulator ===")
    print(f"  Target: {BASE_URL}")
    print(f"  Pattern: {pattern}")
    print("=" * 53)

    if pattern == "normal":
        pattern_normal(60)
    elif pattern == "burst":
        pattern_burst(30)
    elif pattern == "attack":
        pattern_attack(60)
    elif pattern == "mixed":
        pattern_mixed()
    else:
        print(f"Unknown pattern '{pattern}'. Choose: normal | burst | attack | mixed")
        sys.exit(1)


if __name__ == "__main__":
    main()
