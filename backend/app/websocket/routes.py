"""
WebSocket signaling endpoint.

Handles offer/answer/ICE relay and peer lifecycle events.
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.config import config
from app.core.constants import WebSocketEvent, ErrorCode
from app.models.session import SessionStore
from app.services.session import SessionService
from app.services.peer import PeerService
from app.websocket.manager import ConnectionManager
from app.websocket.signaling import SignalingService
from app.utils.redis_client import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Global instances
connection_manager = ConnectionManager()
peer_service = PeerService()


async def get_session_service() -> SessionService:
    """Get session service."""
    redis = await get_redis()
    store = SessionStore(redis)
    return SessionService(store)


@router.websocket("/ws/signal")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Query(...),
    peer_id: str = Query(...),
    token: str = Query(...),
):
    """
    WebSocket signaling endpoint.

    Query parameters:
        - session_id: Session identifier
        - peer_id: Peer identifier
        - token: WebSocket auth token

    Events:
        - join: Peer joining (server sends peer_joined to others)
        - offer: WebRTC offer (relayed to other peer)
        - answer: WebRTC answer (relayed to other peer)
        - ice_candidate: ICE candidate (relayed to other peer)
        - heartbeat: Ping (server responds with pong)
        - error: Error notification from frontend
    """
    service = await get_session_service()
    signaling = SignalingService(peer_service)

    # Verify peer token
    if not await service.verify_peer_token(session_id, peer_id, token):
        await websocket.close(code=4001, reason="Unauthorized")
        logger.warning(f"✗ Unauthorized WebSocket: {session_id}/{peer_id}")
        return

    # Connect
    await connection_manager.connect(session_id, peer_id, websocket)
    peer_service.initialize_peer(session_id, peer_id)

    try:
        # Notify other peer that this peer joined
        peer_count = connection_manager.get_peer_count(session_id)
        await connection_manager.broadcast(
            session_id,
            signaling.create_peer_joined_message(peer_count),
            exclude_peer=peer_id,
        )

        # Listen for messages
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if not event:
                logger.warning(f"Message without event from {session_id}/{peer_id}")
                continue

            # Handle events
            if event == WebSocketEvent.OFFER:
                if not await signaling.handle_offer(session_id, peer_id, data):
                    await websocket.send_json(
                        signaling.create_error_message(
                            ErrorCode.INVALID_OFFER, "Invalid offer format"
                        )
                    )
                    continue

                # Relay to other peer
                other_peer = (
                    connection_manager.get_peers_in_session(session_id) - {peer_id}
                )
                if other_peer:
                    await connection_manager.send_to_peer(
                        session_id,
                        list(other_peer)[0],
                        signaling.create_offer_message(json.loads(data["offer"])),
                    )

            elif event == WebSocketEvent.ANSWER:
                if not await signaling.handle_answer(session_id, peer_id, data):
                    await websocket.send_json(
                        signaling.create_error_message(
                            ErrorCode.INVALID_ANSWER, "Invalid answer format"
                        )
                    )
                    continue

                # Relay to other peer
                other_peer = (
                    connection_manager.get_peers_in_session(session_id) - {peer_id}
                )
                if other_peer:
                    await connection_manager.send_to_peer(
                        session_id,
                        list(other_peer)[0],
                        signaling.create_answer_message(json.loads(data["answer"])),
                    )

            elif event == WebSocketEvent.ICE_CANDIDATE:
                if not await signaling.handle_ice_candidate(session_id, peer_id, data):
                    logger.warning(f"Invalid ICE candidate from {session_id}/{peer_id}")
                    continue

                # Relay to other peer
                other_peer = (
                    connection_manager.get_peers_in_session(session_id) - {peer_id}
                )
                if other_peer:
                    await connection_manager.send_to_peer(
                        session_id,
                        list(other_peer)[0],
                        signaling.create_ice_candidate_message(
                            json.loads(data["candidate"])
                        ),
                    )

            elif event == WebSocketEvent.HEARTBEAT:
                # Echo heartbeat
                await websocket.send_json({"event": "pong"})
                # Update peer heartbeat
                session = await service.get_session(session_id)
                if session:
                    session.update_peer_heartbeat(peer_id)
                    await service.store.update_session(
                        session, config.SESSION_TTL_SECONDS
                    )

            else:
                logger.warning(f"Unknown event from {session_id}/{peer_id}: {event}")

    except WebSocketDisconnect:
        logger.info(f"✓ Disconnected: {session_id}/{peer_id}")

    except Exception as e:
        logger.error(f"WebSocket error {session_id}/{peer_id}: {e}")

    finally:
        # Cleanup
        connection_manager.disconnect(session_id, peer_id)
        peer_service.remove_peer(session_id, peer_id)

        # Notify remaining peers
        peer_count = connection_manager.get_peer_count(session_id)
        if peer_count > 0:
            await connection_manager.broadcast(
                session_id,
                signaling.create_peer_left_message(peer_count),
            )

        # Remove peer from session
        session = await service.get_session(session_id)
        if session:
            await service.remove_peer(session_id, peer_id, config.SESSION_TTL_SECONDS)
