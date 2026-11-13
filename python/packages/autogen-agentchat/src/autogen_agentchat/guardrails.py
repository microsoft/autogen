import sqlite3
import re
import os
from typing import Tuple, List

class SecurityGuardrailException(Exception):
    pass

class GuardrailState:
    def __init__(self, db_path: str = "autogen_guardrail_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_state (
                    agent_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    violation_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def get_state(self, agent_id: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state FROM agent_state WHERE agent_id = ?", (agent_id,))
            row = cursor.fetchone()
            return row[0] if row else "CLEAN"

    def mark_restricted(self, agent_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_state (agent_id, state, violation_count) 
                VALUES (?, 'RESTRICTED', 1) 
                ON CONFLICT(agent_id) DO UPDATE SET 
                state='RESTRICTED', violation_count=violation_count+1
            """, (agent_id,))
            conn.commit()

    def reset_state(self, agent_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE agent_state SET state='CLEAN' WHERE agent_id = ?", (agent_id,))
            conn.commit()


class GuardrailInterceptor:
    def __init__(self):
        self.state_manager = GuardrailState()
        
        # Destructive commands that require hard gates
        self.destructive_patterns = [
            r"\brm\s+-rf\b",
            r"\brmdir\b",
            r"\bdel\s+",
            r"\bterraform\s+(apply|destroy)\b",
            r"\baws\s+.*(delete|rm|terminate|drop)\b",
            r"\bdrop\s+table\b",
            r"\bos\.remove\b",
            r"\bos\.system\(['\"]rm\b",
            r"\bshutil\.rmtree\b",
        ]

    def check_blast_radius(self, code: str) -> bool:
        """Returns True if code has more than one destructive command."""
        match_count = 0
        for pattern in self.destructive_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            match_count += sum(1 for _ in matches)
            
        if match_count > 1:
            return False # Exceeds blast radius
        return True
        
    def is_destructive(self, code: str) -> bool:
        for pattern in self.destructive_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False

    def analyze_and_gate(self, agent_name: str, code: str) -> Tuple[bool, str]:
        """
        Returns (is_approved, reason).
        Throws SecurityGuardrailException if hard block is required.
        """
        # 1. Check Persistent State
        current_state = self.state_manager.get_state(agent_name)
        if current_state == "RESTRICTED":
            raise SecurityGuardrailException(f"Agent '{agent_name}' is in RESTRICTED state due to past violations. Human reset required.")

        # 2. Check Blast Radius
        if not self.check_blast_radius(code):
            self.state_manager.mark_restricted(agent_name)
            raise SecurityGuardrailException("BLAST RADIUS EXCEEDED: Multiple destructive commands detected in a single turn. Agent state is now RESTRICTED.")

        # 3. Mandatory Dry-Run / Human Auth for Destructive Actions
        if self.is_destructive(code):
            print("\n" + "="*60)
            print("CRITICAL ALERT: DESTRUCTIVE ACTION DETECTED")
            print("="*60)
            print(f"Agent '{agent_name}' is attempting to execute:")
            print(code)
            print("="*60)
            print("MANDATORY DRY-RUN ACTIVE. This action could cause data loss.")
            approval = input("Type 'CONFIRM' to approve this execution: ").strip()
            
            if approval != 'CONFIRM':
                self.state_manager.mark_restricted(agent_name)
                raise SecurityGuardrailException("Human denied the destructive action. Agent state is now RESTRICTED.")

        return True, "Code cleared by Deterministic Guardrails."
