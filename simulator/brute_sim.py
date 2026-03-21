"""
Brute Force Simulator — targets your live PythonAnywhere website.

Usage:
    python simulator/brute_sim.py https://YOUR_USERNAME.pythonanywhere.com

What it does:
    Phase 1 — Normal: 1 login/sec (should pass)
    Phase 2 — Brute force: rapid-fire wrong passwords (rate limiter blocks)
    Phase 3 — Recovery: back to normal (limiter relaxes)
"""

import sys
import time
import threading
import requests

def get_base_url():
    if len(sys.argv) > 1:
        return sys.argv[1].rstrip("/")
    return "http://localhost:5000"

BASE_URL = get_base_url()
LOGIN_URL = f"{BASE_URL}/login"

# Fake credentials to hammer the login form
USERNAMES = ["admin", "root", "user", "test", "alice", "bob", "administrator"]
PASSWORDS = ["password", "123456", "admin", "letmein", "qwerty", "password1"]

def attempt_login(username: str, password: str, label: str = "") -> int:
    try:
        resp = requests.post(
            LOGIN_URL,
            data={"username": username, "password": password},
            timeout=5,
            allow_redirects=False
        )
        code = resp.status_code
        icon = "✅" if code == 302 else ("❌ BLOCKED" if code == 429 else "✗ denied")
        print(f"  {icon} [{label}] {username}:{password} → HTTP {code}")
        return code
    except Exception as e:
        print(f"  [error] {e}")
        return 0


def phase_normal(duration=20):
    print(f"\n[PHASE 1] Normal traffic ({duration}s) — targeting {LOGIN_URL}")
    end = time.time() + duration
    i = 0
    while time.time() < end:
        u = USERNAMES[i % len(USERNAMES)]
        attempt_login(u, "wrongpassword", "normal")
        i += 1
        time.sleep(1.0)


def phase_brute(duration=30):
    print(f"\n[PHASE 2] BRUTE FORCE attack ({duration}s) — rapid fire!")
    end = time.time() + duration
    i = 0
    while time.time() < end:
        u = USERNAMES[i % len(USERNAMES)]
        p = PASSWORDS[i % len(PASSWORDS)]
        threading.Thread(target=attempt_login, args=(u, p, "attack")).start()
        i += 1
        time.sleep(0.5)   # ~2 req/sec


def phase_recovery(duration=20):
    print(f"\n[PHASE 3] Recovery — back to normal ({duration}s)")
    end = time.time() + duration
    i = 0
    while time.time() < end:
        u = USERNAMES[i % len(USERNAMES)]
        attempt_login(u, "slowattempt", "recovery")
        i += 1
        time.sleep(1.5)


def main():
    print("=" * 55)
    print("  SERL Brute Force Simulator")
    print(f"  Target: {LOGIN_URL}")
    print("=" * 55)
    print("\nWatch your local dashboard at:")
    print("  → Open frontend/dashboard.html in your browser")
    print("  → Make sure 'python run.py' is running locally\n")

    input("Press ENTER to start the simulation...")

    phase_normal(20)
    phase_brute(30)
    phase_recovery(20)

    print("\n[DONE] Simulation complete!")
    print("Check the Evolution Log in your dashboard to see")
    print("how the ML engine responded to the attack.")


if __name__ == "__main__":
    main()