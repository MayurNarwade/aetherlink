"""
Signaling service for WebSocket event handling.

Validates and creates messages for WebRTC negotiation.
"""

import json
import logging
from app.core.constants import WebSocketEvent, ErrorCode

logger = logging.getLogger(__name__)


class SignalingService:
    """Handles WebSocket signaling message validation and creation."""

    def __init__(self, peer_service):
        self.peer_service = peer_service

    async def handle_offer(self, session_id: str, peer_id: str, data: dict) -> bool:
        """
        Validate and store an offer.

        Returns:
            True if valid, False otherwise
        """
        try:
            offer = data.get("offer")
            if not offer:
                logger.warning(f"Offer missing from message")
                return False

            if isinstance(offer, str):
                offer = json.loads(offer)

            # Validate SDP
            if not offer.get("sdp") or not offer.get("type"):
                logger.warning(f"Invalid offer structure")
                return False

            # Store on peer
            peer = self.peer_service.get_peer(session_id, peer_id)
            if peer:
                peer.set_remote_sdp(offer["sdp"])

            logger.info(f"✓ Offer validated: {session_id}/{peer_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle offer: {e}")
            return False

    async def handle_answer(self, session_id: str, peer_id: str, data: dict) -> bool:
        """
        Validate and store an answer.

        Returns:
            True if valid, False otherwise
        """
        try:
            answer = data.get("answer")
            if not answer:
                logger.warning(f"Answer missing from message")
                return False

            if isinstance(answer, str):
                answer = json.loads(answer)

            # Validate SDP
            if not answer.get("sdp") or not answer.get("type"):
                logger.warning(f"Invalid answer structure")
                return False

            # Store on peer
            peer = self.peer_service.get_peer(session_id, peer_id)
            if peer:
                peer.set_remote_sdp(answer["sdp"])

            logger.info(f"✓ Answer validated: {session_id}/{peer_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle answer: {e}")
            return False

    async def handle_ice_candidate(
        self, session_id: str, peer_id: str, data: dict
    ) -> bool:
        """
        Validate and store an ICE candidate.

        Returns:
            True if valid, False otherwise
        """
        try:
            candidate_data = data.get("candidate")
            if not candidate_data:
                return False

            if isinstance(candidate_data, str):
                candidate_data = json.loads(candidate_data)

            # Validate
            if not candidate_data.get("candidate"):
                return False

            # Store on peer
            peer = self.peer_service.get_peer(session_id, peer_id)
            if peer:
                peer.add_ice_candidate_remote(candidate_data)

            return True

        except Exception as e:
            logger.warning(f"Invalid ICE candidate: {e}")
            return False

    @staticmethod
    def create_peer_joined_message(peer_count: int) -> dict:
        """Create peer_joined notification."""
        return {
            "event": WebSocketEvent.PEER_JOINED,
            "peer_count": peer_count,
        }

    @staticmethod
    def create_peer_left_message(peer_count: int) -> dict:
        """Create peer_left notification."""
        return {
            "event": WebSocketEvent.PEER_LEFT,
            "peer_count": peer_count,
        }

    @staticmethod
    def create_offer_message(offer: dict) -> dict:
        """Create offer message."""
        return {
            "event": WebSocketEvent.OFFER,
            "offer": offer,
        }

    @staticmethod
    def create_answer_message(answer: dict) -> dict:
        """Create answer message."""
        return {
            "event": WebSocketEvent.ANSWER,
            "answer": answer,
        }

    @staticmethod
    def create_ice_candidate_message(candidate: dict) -> dict:
        """Create ICE candidate message."""
        return {
            "event": WebSocketEvent.ICE_CANDIDATE,
            "candidate": candidate,
        }

    @staticmethod
    def create_error_message(error_code: str, message: str) -> dict:
        """Create error message."""
        return {
            "event": WebSocketEvent.ERROR,
            "error_code": error_code,
            "message": message,
        }
