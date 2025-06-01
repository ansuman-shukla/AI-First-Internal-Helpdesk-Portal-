"""
WebSocket Connection Manager

This module manages WebSocket connections for real-time chat functionality
in the helpdesk system, including room management and message broadcasting.
"""

import logging
import json
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and room-based message broadcasting
    
    Handles multiple clients connected to different ticket chat rooms,
    with support for user authentication and role-based access.
    """

    def __init__(self):
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Room memberships: {room_id: {connection_id: user_info}}
        self.rooms: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # User to connection mapping: {user_id: connection_id}
        self.user_connections: Dict[str, str] = {}
        
        logger.info("WebSocket Connection Manager initialized")

    def _generate_connection_id(self, user_id: str, ticket_id: str) -> str:
        """Generate unique connection ID"""
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        return f"{user_id}_{ticket_id}_{timestamp}"

    def _get_room_id(self, ticket_id: str) -> str:
        """Generate room ID for a ticket"""
        return f"ticket_{ticket_id}"

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        user_role: str,
        ticket_id: str,
        username: str = None
    ) -> str:
        """
        Accept a new WebSocket connection and add to room
        
        Args:
            websocket: WebSocket connection
            user_id: ID of the connecting user
            user_role: Role of the connecting user
            ticket_id: ID of the ticket room to join
            username: Username of the connecting user
            
        Returns:
            str: Connection ID
        """
        await websocket.accept()
        
        connection_id = self._generate_connection_id(user_id, ticket_id)
        room_id = self._get_room_id(ticket_id)
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Add to room
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        
        user_info = {
            "user_id": user_id,
            "user_role": user_role,
            "username": username or f"User_{user_id[:8]}",
            "connected_at": datetime.utcnow().isoformat(),
            "ticket_id": ticket_id
        }
        
        self.rooms[room_id][connection_id] = user_info
        
        # Update user connection mapping
        if user_id in self.user_connections:
            # Disconnect previous connection for this user
            old_connection_id = self.user_connections[user_id]
            await self._disconnect_by_id(old_connection_id, "New connection established")
        
        self.user_connections[user_id] = connection_id
        
        logger.info(
            f"User {user_id} ({user_role}) connected to ticket {ticket_id} "
            f"(connection: {connection_id})"
        )
        
        # Notify room about new user
        await self._broadcast_to_room(
            room_id,
            {
                "type": "user_joined",
                "user_id": user_id,
                "username": user_info["username"],
                "user_role": user_role,
                "timestamp": user_info["connected_at"]
            },
            exclude_connection=connection_id
        )
        
        return connection_id

    async def disconnect(self, connection_id: str, reason: str = "Client disconnected"):
        """
        Disconnect a WebSocket connection
        
        Args:
            connection_id: ID of the connection to disconnect
            reason: Reason for disconnection
        """
        await self._disconnect_by_id(connection_id, reason)

    async def _disconnect_by_id(self, connection_id: str, reason: str):
        """Internal method to disconnect by connection ID"""
        if connection_id not in self.active_connections:
            return
        
        # Get user info before removing
        user_info = None
        room_id = None
        
        for rid, room_members in self.rooms.items():
            if connection_id in room_members:
                user_info = room_members[connection_id]
                room_id = rid
                break
        
        # Remove from active connections
        websocket = self.active_connections.pop(connection_id, None)
        
        # Remove from room
        if room_id and connection_id in self.rooms.get(room_id, {}):
            self.rooms[room_id].pop(connection_id)
            
            # Clean up empty room
            if not self.rooms[room_id]:
                self.rooms.pop(room_id)
        
        # Remove from user connections mapping
        if user_info:
            user_id = user_info["user_id"]
            if self.user_connections.get(user_id) == connection_id:
                self.user_connections.pop(user_id, None)
        
        # Close WebSocket if still open
        if websocket:
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket {connection_id}: {e}")
        
        logger.info(
            f"Disconnected {connection_id} - Reason: {reason} "
            f"(User: {user_info['user_id'] if user_info else 'unknown'})"
        )
        
        # Notify room about user leaving
        if room_id and user_info:
            await self._broadcast_to_room(
                room_id,
                {
                    "type": "user_left",
                    "user_id": user_info["user_id"],
                    "username": user_info["username"],
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]):
        """
        Send a message to a specific connection
        
        Args:
            connection_id: Target connection ID
            message: Message to send
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
                logger.debug(f"Sent personal message to {connection_id}")
            except WebSocketDisconnect:
                await self._disconnect_by_id(connection_id, "WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                await self._disconnect_by_id(connection_id, f"Send error: {e}")

    async def broadcast_to_ticket(
        self,
        ticket_id: str,
        message: Dict[str, Any],
        exclude_user_id: Optional[str] = None
    ):
        """
        Broadcast a message to all users in a ticket room
        
        Args:
            ticket_id: ID of the ticket
            message: Message to broadcast
            exclude_user_id: User ID to exclude from broadcast
        """
        room_id = self._get_room_id(ticket_id)
        exclude_connection = None
        
        if exclude_user_id and exclude_user_id in self.user_connections:
            exclude_connection = self.user_connections[exclude_user_id]
        
        await self._broadcast_to_room(room_id, message, exclude_connection)

    async def _broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude_connection: Optional[str] = None
    ):
        """
        Internal method to broadcast to a room
        
        Args:
            room_id: ID of the room
            message: Message to broadcast
            exclude_connection: Connection ID to exclude
        """
        if room_id not in self.rooms:
            logger.debug(f"Room {room_id} not found for broadcast")
            return
        
        room_members = self.rooms[room_id]
        disconnected_connections = []
        
        for connection_id, user_info in room_members.items():
            if connection_id == exclude_connection:
                continue
                
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                try:
                    await websocket.send_text(json.dumps(message))
                except WebSocketDisconnect:
                    disconnected_connections.append(connection_id)
                except Exception as e:
                    logger.error(f"Error broadcasting to {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            await self._disconnect_by_id(connection_id, "Connection lost during broadcast")
        
        active_count = len(room_members) - len(disconnected_connections)
        if exclude_connection:
            active_count -= 1
            
        logger.debug(f"Broadcasted to {active_count} connections in room {room_id}")

    def get_room_members(self, ticket_id: str) -> List[Dict[str, Any]]:
        """
        Get list of users currently in a ticket room
        
        Args:
            ticket_id: ID of the ticket
            
        Returns:
            List of user info dictionaries
        """
        room_id = self._get_room_id(ticket_id)
        
        if room_id not in self.rooms:
            return []
        
        return list(self.rooms[room_id].values())

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)

    def get_room_count(self) -> int:
        """Get total number of active rooms"""
        return len(self.rooms)


# Global connection manager instance
connection_manager = ConnectionManager()
