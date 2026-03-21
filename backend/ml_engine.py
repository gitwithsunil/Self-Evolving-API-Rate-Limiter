import time
import threading
import math
from datetime import datetime
from collections import deque


class MLEvolutionEngine:
    """
    Self-evolving intelligence layer.

    Uses two mechanisms:
    1. Z-score anomaly detector  — flags abnormal traffic spikes in real time
    2. Q-learning RL agent       — learns which limit setting minimises
                                   deny-rate while blocking abuse

    Every EVAL_INTERVAL seconds, the engine:
      - Calculates current traffic stats
      - Runs anomaly detection
      - Picks an RL action (tighten / hold / relax)
      - Applies the new limit via rate_limiter.set_limit()
      - Logs the decision to evolution_history
    """

    EVAL_INTERVAL = 8      # seconds between evaluations
    WINDOW_SIZE = 30       # samples kept for z-score baseline

    # RL: discrete action space
    ACTIONS = [-3, -1, 0, +1, +3]   # delta to apply to current limit
    ALPHA = 0.3                       # learning rate
    GAMMA = 0.7                       # discount factor
    EPSILON = 0.15                    # exploration rate

    def __init__(self, rate_limiter, telemetry):
        self.rate_limiter = rate_limiter
        self.telemetry = telemetry
        self.lock = threading.Lock()

        self._running = True
        self._evolution_history = []

        # Rolling baseline for z-score (request rates)
        self._rate_history = deque(maxlen=self.WINDOW_SIZE)

        # Q-table: state (str) -> list of Q values per action
        self._q_table = {}

        # Track last state/action for Q update
        self._last_state = None
        self._last_action_idx = None
        self._last_limit = rate_limiter.limit

    # ------------------------------------------------------------------ #
    #  Background loop                                                     #
    # ------------------------------------------------------------------ #

    def run_loop(self):
        while self._running:
            time.sleep(self.EVAL_INTERVAL)
            try:
                self._evaluate()
            except Exception as e:
                print(f"[MLEngine] Error: {e}")

    def _evaluate(self):
        stats = self.telemetry.get_stats()
        current_limit = self.rate_limiter.limit

        total = stats.get("total_requests", 0)
        denied = stats.get("denied_requests", 0)
        recent_rate = stats.get("recent_rate", 0.0)

        if total == 0:
            return

        deny_ratio = denied / total if total > 0 else 0.0

        # ── Anomaly detection ──────────────────────────────────────────
        self._rate_history.append(recent_rate)
        anomaly, z_score = self._z_score_anomaly(recent_rate)
        traffic_label = self._classify_traffic(recent_rate, deny_ratio, anomaly)

        # ── RL state representation ────────────────────────────────────
        state = self._encode_state(traffic_label, deny_ratio, current_limit)

        # ── Q update for previous step ─────────────────────────────────
        if self._last_state is not None:
            reward = self._compute_reward(deny_ratio, current_limit, self._last_limit)
            self._q_update(self._last_state, self._last_action_idx, reward, state)

        # ── Pick action ────────────────────────────────────────────────
        action_idx = self._epsilon_greedy(state)
        delta = self.ACTIONS[action_idx]
        new_limit = max(1, current_limit + delta)

        # ── Apply if changed ───────────────────────────────────────────
        reason = self._build_reason(traffic_label, anomaly, z_score, deny_ratio, delta)

        if new_limit != current_limit or anomaly:
            self.rate_limiter.set_limit(new_limit)
            self._log_evolution(
                old_limit=current_limit,
                new_limit=new_limit,
                traffic_label=traffic_label,
                deny_ratio=deny_ratio,
                z_score=z_score,
                anomaly=anomaly,
                reason=reason,
            )

        self._last_state = state
        self._last_action_idx = action_idx
        self._last_limit = current_limit

    # ------------------------------------------------------------------ #
    #  Anomaly detection                                                   #
    # ------------------------------------------------------------------ #

    def _z_score_anomaly(self, current_rate: float) -> tuple[bool, float]:
        if len(self._rate_history) < 5:
            return False, 0.0
        mean = sum(self._rate_history) / len(self._rate_history)
        variance = sum((x - mean) ** 2 for x in self._rate_history) / len(self._rate_history)
        std = math.sqrt(variance) if variance > 0 else 0.001
        z = (current_rate - mean) / std
        return abs(z) > 2.0, round(z, 3)

    def _classify_traffic(self, rate, deny_ratio, anomaly) -> str:
        if anomaly and deny_ratio > 0.4:
            return "attack"
        elif anomaly and rate > 2.0:
            return "burst"
        elif deny_ratio > 0.3:
            return "heavy"
        elif rate < 0.1:
            return "quiet"
        else:
            return "normal"

    # ------------------------------------------------------------------ #
    #  RL helpers                                                          #
    # ------------------------------------------------------------------ #

    def _encode_state(self, traffic_label, deny_ratio, limit) -> str:
        deny_bucket = "low" if deny_ratio < 0.1 else ("mid" if deny_ratio < 0.4 else "high")
        limit_bucket = "low" if limit <= 5 else ("mid" if limit <= 15 else "high")
        return f"{traffic_label}_{deny_bucket}_{limit_bucket}"

    def _epsilon_greedy(self, state) -> int:
        import random
        if state not in self._q_table:
            self._q_table[state] = [0.0] * len(self.ACTIONS)
        if random.random() < self.EPSILON:
            return random.randint(0, len(self.ACTIONS) - 1)
        q_vals = self._q_table[state]
        return q_vals.index(max(q_vals))

    def _compute_reward(self, deny_ratio, current_limit, last_limit) -> float:
        """
        Reward signal:
          +2  for low deny ratio (system is responsive)
          -3  for high deny ratio (too strict)
          -1  for very low limit (over-restriction)
          +0.5 stability bonus for not changing limit
        """
        reward = 0.0
        if deny_ratio < 0.05:
            reward += 2.0
        elif deny_ratio > 0.5:
            reward -= 3.0
        elif deny_ratio > 0.3:
            reward -= 1.0
        if current_limit < 3:
            reward -= 1.0
        if current_limit == last_limit:
            reward += 0.5
        return reward

    def _q_update(self, state, action_idx, reward, next_state):
        if state not in self._q_table:
            self._q_table[state] = [0.0] * len(self.ACTIONS)
        if next_state not in self._q_table:
            self._q_table[next_state] = [0.0] * len(self.ACTIONS)
        old_q = self._q_table[state][action_idx]
        max_next = max(self._q_table[next_state])
        self._q_table[state][action_idx] = old_q + self.ALPHA * (
            reward + self.GAMMA * max_next - old_q
        )

    # ------------------------------------------------------------------ #
    #  Logging                                                             #
    # ------------------------------------------------------------------ #

    def _build_reason(self, label, anomaly, z, deny_ratio, delta) -> str:
        parts = [f"Traffic: {label}"]
        if anomaly:
            parts.append(f"anomaly detected (z={z})")
        parts.append(f"deny ratio={round(deny_ratio * 100, 1)}%")
        if delta > 0:
            parts.append(f"relaxing limit by {delta}")
        elif delta < 0:
            parts.append(f"tightening limit by {abs(delta)}")
        else:
            parts.append("limit unchanged")
        return " | ".join(parts)

    def _log_evolution(self, **kwargs):
        with self.lock:
            self._evolution_history.append({
                **kwargs,
                "timestamp": datetime.utcnow().isoformat(),
            })
            # Keep last 200 events
            if len(self._evolution_history) > 200:
                self._evolution_history.pop(0)

    # ------------------------------------------------------------------ #
    #  Public getters                                                      #
    # ------------------------------------------------------------------ #

    def get_state(self) -> dict:
        return {
            "q_table_size": len(self._q_table),
            "rate_history": list(self._rate_history),
            "last_state": self._last_state,
            "eval_interval": self.EVAL_INTERVAL,
        }

    def get_evolution_history(self) -> list:
        with self.lock:
            return list(self._evolution_history)

    def reset(self):
        with self.lock:
            self._evolution_history.clear()
            self._rate_history.clear()
            self._q_table.clear()
            self._last_state = None
            self._last_action_idx = None

    def stop(self):
        self._running = False