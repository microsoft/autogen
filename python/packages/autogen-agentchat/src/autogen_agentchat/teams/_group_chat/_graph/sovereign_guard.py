import asyncio
import hashlib
import json
import logging
import os
import time
from collections import Counter, deque
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

# ============================================================================
# SOVEREIGN CONFIGURATION
# ============================================================================
logger = logging.getLogger("autogen.sovereign_guard")

class IntegrityViolationError(Exception):
    """Raised when cryptographic verification fails."""
    pass

class OperationalIschemiaError(Exception):
    """Raised when the workflow circulation has stopped (Zombie State) or persistence failed."""
    pass

class SovereignGraphGuard:
    """
    GRANDMASTER CLASS: Transactional State Engine for AutoGen.

    Protocols:
    1. Attribute Agnosticism: Works regardless of AutoGen internal API shifts.
    2. Slot Awareness: Sanitizes optimized objects (__slots__).
    3. Safe Snapshotting: Prevents Deepcopy crashes on Locks.
    4. Zero-Capitulation: Crashes on corruption (never overwrites history).
    5. Structural Isomorphism: Maps internal state to serialized truth.
    """

    def __init__(self, workflow_instance, state_path: str = "graph_state.json"):
        self._workflow = workflow_instance
        self._state_path = state_path
        self._lock = asyncio.Lock()

        # EXTENDED TRANSIENT KEYS
        self._transient_keys = {
            "_lock", "_stop_event", "client", "socket", "thread",
            "lock", "_condition", "_loop", "_event_loop", "executor", "ssl_context"
        }
        self._pre_transaction_snapshot: Optional[Dict[str, Any]] = None

    def _get_attr_robust(self, obj: Any, attr_base: str, default=None) -> Any:
        """Sovereign Helper: Hunts for the attribute across private/public namespaces."""
        candidates = [attr_base, f"_{attr_base}", f"__{attr_base}"]
        for name in candidates:
            if hasattr(obj, name):
                return getattr(obj, name)
        return default

    def _set_attr_robust(self, obj: Any, attr_base: str, value: Any) -> bool:
        """Sovereign Helper: Sets the attribute on the first matching namespace."""
        candidates = [attr_base, f"_{attr_base}", f"__{attr_base}"]
        for name in candidates:
            if hasattr(obj, name):
                setattr(obj, name, value)
                return True
        return False

    def _sanitize_state(self, obj: Any, depth=0) -> Any:
        """Recursive sanitization handling Dicts, Lists, Objects, __slots__, and Deques."""
        if depth > 50: return str(obj)

        if hasattr(obj, "get_state"):
            return obj.get_state()
        elif isinstance(obj, dict):
            return {k: self._sanitize_state(v, depth+1) for k, v in obj.items()
                    if k not in self._transient_keys and not k.startswith("_threading")}
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return [self._sanitize_state(i, depth+1) for i in obj]
        elif isinstance(obj, deque):
             # Fix: Convert deque to list for JSON serialization
            return [self._sanitize_state(i, depth+1) for i in obj]
        elif isinstance(obj, Counter):
            return dict(obj)

        # Handle __dict__ AND __slots__ (Grandmaster Optimization)
        state_dict = {}
        if hasattr(obj, "__dict__"):
            state_dict.update(obj.__dict__)
        if hasattr(obj, "__slots__"):
            for slot in obj.__slots__:
                if hasattr(obj, slot):
                    state_dict[slot] = getattr(obj, slot)

        if state_dict:
            safe_dict = {}
            for k, v in state_dict.items():
                if k in self._transient_keys or k.startswith("_threading"): continue
                if "lock" in str(type(v)).lower(): continue
                if "condition" in str(type(v)).lower(): continue
                safe_dict[k] = self._sanitize_state(v, depth+1)
            return safe_dict

        # Atomic types or unknowns
        t_str = str(type(obj)).lower()
        if "lock" in t_str or "condition" in t_str: return None
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)

    async def _capture_topology(self) -> Dict[str, Any]:
        """
        Captures topology safely.
        REPLACES deepcopy with sanitize to prevent crashes on Agent locks.
        """
        # Robustly fetch attributes from GraphFlowManager
        remaining = self._get_attr_robust(self._workflow, "remaining", {})
        enqueued_any = self._get_attr_robust(self._workflow, "enqueued_any", {})
        ready = self._get_attr_robust(self._workflow, "ready", [])

        # Isomorphic Mapping: active_speakers -> active_nodes
        active_speakers = self._get_attr_robust(self._workflow, "active_speakers", [])

        return {
            "remaining": self._sanitize_state(remaining),
            "enqueued_any": self._sanitize_state(enqueued_any),
            "ready": self._sanitize_state(ready),
            "active_nodes": self._sanitize_state(active_speakers),
            "timestamp": time.time()
        }

    def _restore_topology(self, snapshot: Dict[str, Any]):
        """Restores topology robustly."""
        # Restore basic collections
        # We must re-cast to specific types if the manager expects them (e.g. Counter, deque)

        remaining_data = snapshot["remaining"]
        # GraphFlowManager expects _remaining to be Dict[str, Counter[str]]
        restored_remaining = {k: Counter(v) for k, v in remaining_data.items()}
        self._set_attr_robust(self._workflow, "remaining", restored_remaining)

        self._set_attr_robust(self._workflow, "enqueued_any", snapshot["enqueued_any"])

        ready_data = snapshot["ready"]
        # GraphFlowManager expects _ready to be deque
        self._set_attr_robust(self._workflow, "ready", deque(ready_data))

        # Restore active speakers
        active_nodes = snapshot.get("active_nodes", [])
        self._set_attr_robust(self._workflow, "active_speakers", active_nodes)

    @asynccontextmanager
    async def atomic_transition(self):
        """Transactional Context Manager with Strict Rollback."""
        async with self._lock:
            # 1. Capture Pre-State using Safe Sanitization
            self._pre_transaction_snapshot = await self._capture_topology()
            try:
                yield self
                await self._commit_to_disk()
            except (KeyboardInterrupt, asyncio.CancelledError) as e:
                logger.warning(f"⚠️ INTERRUPT: Rolling back state to T-{time.time()}")
                if self._pre_transaction_snapshot:
                    self._restore_topology(self._pre_transaction_snapshot)
                raise e
            finally:
                self._pre_transaction_snapshot = None

    async def _commit_to_disk(self):
        """Atomic Write with Zero-Capitulation (No Silent Failures)."""
        try:
            # Topology is already sanitized in _capture_topology
            topology = await self._capture_topology()

            # Robust Agent Capture: Try to find agents, but don't fail if missing.
            # GraphFlowManager doesn't store agent objects directly.
            # We skip 'agents' state if not found to avoid misleading partial state.
            raw_agents = getattr(self._workflow, "agent_states", getattr(self._workflow, "_agents", {}))
            agents = self._sanitize_state(raw_agents)

            full_state = {"version": "64.2", "topology": topology, "agents": agents}

            canonical = json.dumps(full_state, sort_keys=True, default=str)
            state_hash = hashlib.sha256(canonical.encode()).hexdigest()
            envelope = {"data": full_state, "hash": state_hash}

            tmp_path = f"{self._state_path}.tmp"
            with open(tmp_path, "w") as f:
                json.dump(envelope, f, indent=2)
                f.flush()
                os.fsync(f.fileno()) # IRON SEAL: Force physical disk write
            os.replace(tmp_path, self._state_path)

            # POSIX Durability: Sync parent directory to ensure rename is persisted
            if os.name == "posix":
                try:
                    parent_dir = os.path.dirname(os.path.abspath(self._state_path))
                    fd = os.open(parent_dir, os.O_RDONLY)
                    try:
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                except (OSError, IOError) as e:
                    logger.warning(f"⚠️ Directory sync failed: {e}")

        except Exception as e:
            logger.critical(f"🛑 PERSISTENCE FAILURE: {e}")
            raise OperationalIschemiaError(f"CRITICAL: Failed to persist state: {e}") from e

    def load_and_heal(self) -> None:
        """Ischemia Repair Protocol."""
        if not os.path.exists(self._state_path): return

        try:
            with open(self._state_path, "r") as f:
                envelope = json.load(f)

            # Integrity Gate
            canonical = json.dumps(envelope["data"], sort_keys=True, default=str)
            if hashlib.sha256(canonical.encode()).hexdigest() != envelope["hash"]:
                # HALT ON CORRUPTION. Do not overwrite history.
                raise IntegrityViolationError(f"State file {self._state_path} corrupted. Hash mismatch.")

            topo = envelope["data"]["topology"]

            # Zombie Detection
            remaining = topo.get("remaining", {})
            ready = topo.get("ready", [])
            active_nodes = topo.get("active_nodes", [])

            # "Ischemia" = Work exists, but no one is ready and no one is active.
            has_work = any(any(c > 0 for c in t.values()) for t in remaining.values())
            is_stalled = len(ready) == 0 and len(active_nodes) == 0
            is_zombie = has_work and is_stalled

            if is_zombie:
                logger.warning("⚡ ZOMBIE STATE DETECTED. INJECTING ADRENALINE.")
                # Strategy: If stalled, push the nodes with remaining work back into ready?
                # Or find the node that was supposed to be active.
                # Heuristic: Inject nodes that have work pending.
                for agent, tasks in remaining.items():
                    if any(c > 0 for c in tasks.values()):
                        # We verify if this agent is NOT in ready and NOT active
                        if agent not in ready and agent not in active_nodes:
                            topo["ready"].append(agent)
                            # Also reset enqueued_any if applicable
                            enqueued = topo.get("enqueued_any", {})
                            if agent in enqueued:
                                for t in enqueued[agent]:
                                    enqueued[agent][t] = True
                                    # We break after one trigger to avoid over-activation
                                    break
                        # Only inject one agent to restart flow? Or all?
                        # Injecting one is safer to avoid race conditions.
                        break

            self._restore_topology(topo)
            logger.info("✓ GRAPH STATE RESTORED & HEALED.")

        except Exception as e:
            logger.critical(f"⛔ FATAL LOAD ERROR: {e}")
            raise e
