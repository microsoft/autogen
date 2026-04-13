import json
import hashlib
import logging
import asyncio
import time
import os
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from copy import deepcopy

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
    """
    def __init__(self, workflow_instance, state_path: str = "graph_state.json"):
        self._workflow = workflow_instance
        self._state_path = state_path
        self._lock = asyncio.Lock()
        # Transient keys to exclude from state
        self._transient_keys = {
            '_lock', '_stop_event', 'client', 'socket', 'thread',
            'lock', '_condition', '_loop', '_event_loop', 'executor', 'ssl_context'
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
        """Recursive sanitization handling Dicts, Lists, Objects, and __slots__."""
        if depth > 50: return str(obj)
        
        if hasattr(obj, "get_state"):
            return obj.get_state()
            
        elif isinstance(obj, dict):
            return {k: self._sanitize_state(v, depth+1) for k, v in obj.items()
                    if k not in self._transient_keys and not k.startswith('_threading')}
                    
        elif isinstance(obj, list):
            return [self._sanitize_state(i, depth+1) for i in obj]
            
        # Handle __dict__ AND __slots__
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
                if k in self._transient_keys or k.startswith('_threading'): continue
                if 'lock' in str(type(v)).lower(): continue
                if 'condition' in str(type(v)).lower(): continue
                safe_dict[k] = self._sanitize_state(v, depth+1)
            return safe_dict
            
        # Atomic types or unknowns
        t_str = str(type(obj)).lower()
        if 'lock' in t_str or 'condition' in t_str: return None
        
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)

    async def _capture_topology(self) -> Dict[str, Any]:
        """Captures topology safely. REPLACES deepcopy with sanitize."""
        return {
            "remaining": self._sanitize_state(self._get_attr_robust(self._workflow, "remaining", {})),
            "enqueued_any": self._sanitize_state(self._get_attr_robust(self._workflow, "enqueued_any", {})),
            "ready": self._sanitize_state(self._get_attr_robust(self._workflow, "ready", [])),
            "current_node": getattr(self._workflow, "current_node_id", None),
            "timestamp": time.time()
        }

    def _restore_topology(self, snapshot: Dict[str, Any]):
        """Restores topology robustly."""
        self._set_attr_robust(self._workflow, "remaining", snapshot["remaining"])
        self._set_attr_robust(self._workflow, "enqueued_any", snapshot["enqueued_any"])
        self._set_attr_robust(self._workflow, "ready", snapshot["ready"])
        self._workflow.current_node_id = snapshot["current_node"]

    @asynccontextmanager
    async def atomic_transition(self):
        """Transactional Context Manager with Strict Rollback."""
        async with self._lock:
            # 1. Capture Pre-State
            self._pre_transaction_snapshot = await self._capture_topology()
            try:
                yield self
                await self._commit_to_disk()
            except (KeyboardInterrupt, asyncio.CancelledError) as e:
                logger.warning(f"INTERRUPT: Rolling back state to T-{time.time()}")
                if self._pre_transaction_snapshot:
                    self._restore_topology(self._pre_transaction_snapshot)
                raise e
            finally:
                self._pre_transaction_snapshot = None

    async def _commit_to_disk(self):
        """Atomic Write with Zero-Capitulation."""
        try:
            topology = await self._capture_topology()
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
            
        except Exception as e:
            logger.critical(f"PERSISTENCE FAILURE: {e}")
            raise OperationalIschemiaError(f"CRITICAL: Failed to persist state: {e}")

    def load_and_heal(self) -> None:
        """Ischemia Repair Protocol."""
        if not os.path.exists(self._state_path): return
        
        try:
            with open(self._state_path, "r") as f:
                envelope = json.load(f)
            
            # Integrity Gate
            canonical = json.dumps(envelope["data"], sort_keys=True, default=str)
            if hashlib.sha256(canonical.encode()).hexdigest() != envelope["hash"]:
                raise IntegrityViolationError(f"State file {self._state_path} corrupted. Hash mismatch.")
            
            topo = envelope["data"]["topology"]
            
            # Zombie Detection
            remaining = topo.get("remaining", {})
            ready = topo.get("ready", [])
            has_work = any(any(c > 0 for c in t.values()) for t in remaining.values())
            is_zombie = has_work and len(ready) == 0
            
            if is_zombie:
                logger.warning("ZOMBIE STATE DETECTED. INJECTING ADRENALINE.")
                for agent, tasks in remaining.items():
                    if any(c > 0 for c in tasks.values()):
                        topo["ready"].append(agent)
                        if agent in topo["enqueued_any"]:
                            for t in topo["enqueued_any"][agent]:
                                topo["enqueued_any"][agent][t] = True
                                break
                        break
                        
            self._restore_topology(topo)
            logger.info("GRAPH STATE RESTORED & HEALED.")
            
        except Exception as e:
            logger.critical(f"FATAL LOAD ERROR: {e}")
            raise e
