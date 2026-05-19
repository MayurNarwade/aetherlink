"""
Pydantic schemas for WebSocket signaling validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""

    type: str
    data: dict = Field(default_factory=dict)


class JoinMessage(BaseModel):
    """WebSocket join event."""

    type: str = "join"
    session_id: str
    peer_id: str
    peer_token: str


class PeerJoinedMessage(BaseModel):
    """WebSocket peer_joined event (broadcast to other peer)."""

    type: str = "peer_joined"
    peer_id: str
    session_id: str


class OfferMessage(BaseModel):
    """WebSocket offer event (SDP offer from initiator)."""

    type: str = "offer"
    sdp: str
    sender_peer_id: str


class AnswerMessage(BaseModel):
    """WebSocket answer event (SDP answer from responder)."""

    type: str = "answer"
    sdp: str
    sender_peer_id: str


class ICECandidateMessage(BaseModel):
    """WebSocket ICE candidate event."""

    type: str = "ice_candidate"
    candidate: str  # JSON stringified ICECandidate
    sdp_mid: Optional[str] = None
    sdp_mline_index: Optional[int] = None
    sender_peer_id: str


class PeerLeftMessage(BaseModel):
    """WebSocket peer_left event (broadcast when peer disconnects)."""

    type: str = "peer_left"
    peer_id: str


class HeartbeatMessage(BaseModel):
    """WebSocket heartbeat/ping to keep connection alive."""

    type: str = "heartbeat"
    timestamp: int


class ErrorMessage(BaseModel):
    """WebSocket error event."""

    type: str = "error"
    code: str
    message: str
    details: Optional[dict] = None
