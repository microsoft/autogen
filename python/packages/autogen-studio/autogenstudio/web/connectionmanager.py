from fastapi import WebSocket
from typing import Dict, List, Optional
import asyncio
import uuid
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"
    EXPIRED = "expired"


class Session:
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.status = SessionStatus.CREATED
        self.websocket: Optional[WebSocket] = None
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()
        self.messages: List[Dict] = []


class ConnectionManager:
    def __init__(self, session_timeout: int = 3600):  # 1 hour timeout
        self.sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self.session_timeout = session_timeout

        # Start cleanup task
        asyncio.create_task(self._cleanup_expired_sessions())

    async def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())

        async with self._lock:
            self.sessions[session_id] = Session(
                session_id=session_id,
                user_id=user_id
            )

        return session_id

    async def connect(self, session_id: str, websocket: WebSocket) -> bool:
        """Connect a WebSocket to a session"""
        async with self._lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]

            # Accept the WebSocket connection
            await websocket.accept()

            # Update session
            session.websocket = websocket
            session.status = SessionStatus.ACTIVE
            session.last_active = datetime.utcnow()

            return True

    async def disconnect(self, session_id: str) -> None:
        """Disconnect a session's WebSocket"""
        async with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                if session.websocket:
                    try:
                        await session.websocket.close()
                    except Exception:
                        pass
                    finally:
                        session.websocket = None

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists and is valid"""
        async with self._lock:
            return session_id in self.sessions and \
                self.sessions[session_id].status != SessionStatus.EXPIRED

    async def get_session_status(self, session_id: str) -> Optional[str]:
        """Get the status of a session"""
        async with self._lock:
            if session_id in self.sessions:
                return self.sessions[session_id].status
            return None

    async def update_session_status(self, session_id: str, status: str) -> bool:
        """Update a session's status"""
        async with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id].status = status
                self.sessions[session_id].last_active = datetime.utcnow()
                return True
            return False

    async def send_to_session(self, session_id: str, message: str) -> bool:
        """Send a message to a session's WebSocket if connected"""
        async with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                if session.websocket:
                    try:
                        await session.websocket.send_text(message)
                        session.last_active = datetime.utcnow()
                        return True
                    except Exception:
                        await self.disconnect(session_id)
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and clean up its resources"""
        async with self._lock:
            if session_id in self.sessions:
                await self.disconnect(session_id)
                del self.sessions[session_id]
                return True
            return False

    async def _cleanup_expired_sessions(self) -> None:
        """Periodically clean up expired sessions"""
        while True:
            try:
                current_time = datetime.utcnow()
                expired_sessions = []

                async with self._lock:
                    for session_id, session in self.sessions.items():
                        if (current_time - session.last_active).total_seconds() > self.session_timeout:
                            expired_sessions.append(session_id)

                    for session_id in expired_sessions:
                        await self.disconnect(session_id)
                        del self.sessions[session_id]

            except Exception as e:
                print(f"Error in session cleanup: {str(e)}")

            await asyncio.sleep(300)  # Run cleanup every 5 minutes
