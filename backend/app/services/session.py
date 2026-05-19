"""
Session service with lifecycle management.

Handles session creation, joining, peer management, and expiry.
"""

import logging
from datetime import datetime, timedelta
from app.core.config import config
from app.core.constants import SessionState
from app.models.session import Session, SessionStore
from app.utils.token_generator import generate_session_id, generate_otp

logger = logging.getLogger(__name__)


class SessionService:
    """Business logic for session management."""

    def __init__(self, store: SessionStore):
        self.store = store

    async def create_session(self) -> tuple[str, str, str]:
        """
        Create a new session.

        Returns:
            (session_id, otp, expires_at) tuple
        """
        session_id = generate_session_id()
        otp = generate_otp()

        session = await self.store.create_session(
            session_id,
            otp,
            config.SESSION_TTL_SECONDS,
        )

        logger.info(f"✓ Session created: {session_id}")
        return session_id, otp, session.expires_at

    async def get_session(self, session_id: str) -> Session:
        """Get session by ID."""
        session = await self.store.get_session(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None

        return session

    async def join_session(
        self, session_id: str, otp: str
    ) -> tuple[str, str, str]:
        """
        Join a session with OTP.

        Returns:
            (peer_id, peer_token, ws_url) tuple

        Raises:
            ValueError if session invalid, expired, or full
        """
        session = await self.get_session(session_id)

        if not session:
            raise ValueError("Session not found")

        if session.is_expired():
            raise ValueError("Session has expired")

        if not await self.store.verify_otp(session_id, otp):
            raise ValueError("Invalid OTP")

        if session.is_full():
            raise ValueError("Session is full")

        # Add peer
        peer_id, token = session.add_peer()

        # Update session
        await self.store.update_session(session, config.SESSION_TTL_SECONDS)

        logger.info(f"✓ Peer joined: {session_id}/{peer_id}")

        # Build WebSocket URL
        ws_protocol = "wss" if config.ENVIRONMENT == "production" else "ws"
        ws_host = config.WS_HOST or "localhost:8000"
        ws_url = f"{ws_protocol}://{ws_host}/ws/signal?session_id={session_id}&peer_id={peer_id}&token={token}"

        return peer_id, token, ws_url

    async def remove_peer(
        self, session_id: str, peer_id: str, ttl_seconds: int
    ) -> None:
        """Remove peer from session."""
        session = await self.get_session(session_id)

        if not session:
            return

        session.remove_peer(peer_id)
        await self.store.update_session(session, ttl_seconds)

        logger.info(f"✓ Peer removed: {session_id}/{peer_id}")

        # Auto-close if no peers left
        if session.get_peer_count() == 0:
            await self.store.delete_session(session_id)

    async def close_session(self, session_id: str) -> None:
        """Manually close a session."""
        session = await self.get_session(session_id)

        if not session:
            return

        session.state = SessionState.CLOSED
        await self.store.delete_session(session_id)

        logger.info(f"✓ Session closed: {session_id}")

    async def verify_peer_token(
        self, session_id: str, peer_id: str, token: str
    ) -> bool:
        """Verify peer token for WebSocket connection."""
        session = await self.get_session(session_id)

        if not session:
            return False

        if session.is_expired():
            return False

        if peer_id not in session.peers:
            return False

        peer = session.peers[peer_id]
        return peer.get("token") == token
