"""
NullForge Real-time WebSocket Hub
State of the Art real-time collaboration

Features:
- Multi-user collaboration rooms
- Real-time code sharing
- Live cursor tracking
- Presence awareness
- Chat and comments
- Operation transforms for conflict resolution
- Event broadcasting
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib

try:
    from fastapi import WebSocket, WebSocketDisconnect
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


class MessageType(Enum):
    """Types of WebSocket messages."""
    # Connection
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    
    # Room management
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    ROOM_STATE = "room_state"
    
    # Presence
    PRESENCE_UPDATE = "presence_update"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    
    # Code collaboration
    CODE_CHANGE = "code_change"
    CODE_SYNC = "code_sync"
    
    # Task collaboration
    TASK_START = "task_start"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_ERROR = "task_error"
    
    # Chat
    CHAT_MESSAGE = "chat_message"
    COMMENT = "comment"
    
    # System
    ERROR = "error"
    NOTIFICATION = "notification"


@dataclass
class ClientInfo:
    """Information about a connected client."""
    client_id: str
    user_id: Optional[str] = None
    username: str = "Anonymous"
    color: str = "#667eea"
    cursor_position: Optional[Dict[str, int]] = None
    selection: Optional[Dict[str, Any]] = None
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    rooms: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "username": self.username,
            "color": self.color,
            "cursor_position": self.cursor_position,
            "selection": self.selection,
            "connected_at": self.connected_at,
            "last_active": self.last_active,
            "rooms": list(self.rooms),
            "metadata": self.metadata
        }


@dataclass
class Room:
    """A collaboration room."""
    room_id: str
    name: str
    clients: Dict[str, ClientInfo] = field(default_factory=dict)
    code: str = ""
    language: str = "python"
    task_id: Optional[str] = None
    task_status: str = "idle"
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "clients": {cid: c.to_dict() for cid, c in self.clients.items()},
            "code": self.code,
            "language": self.language,
            "task_id": self.task_id,
            "task_status": self.task_status,
            "created_at": self.created_at,
            "client_count": len(self.clients),
            "metadata": self.metadata
        }


@dataclass
class Message:
    """A WebSocket message."""
    type: MessageType
    payload: Dict[str, Any] = field(default_factory=dict)
    sender_id: Optional[str] = None
    room_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "sender_id": self.sender_id,
            "room_id": self.room_id,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        })
    
    @classmethod
    def from_json(cls, data: str) -> "Message":
        parsed = json.loads(data)
        return cls(
            type=MessageType(parsed["type"]),
            payload=parsed.get("payload", {}),
            sender_id=parsed.get("sender_id"),
            room_id=parsed.get("room_id"),
            timestamp=parsed.get("timestamp", datetime.now().isoformat()),
            message_id=parsed.get("message_id", str(uuid.uuid4()))
        )


class OperationTransform:
    """
    Simple operation transform for conflict resolution.
    
    Handles concurrent text edits by transforming operations.
    """
    
    @staticmethod
    def transform_insert(op1: Dict[str, Any], op2: Dict[str, Any]) -> Dict[str, Any]:
        """Transform insert operation against another insert."""
        pos1 = op1["position"]
        pos2 = op2["position"]
        
        if pos1 <= pos2:
            return op1
        else:
            return {**op1, "position": pos1 + len(op2.get("text", ""))}
    
    @staticmethod
    def transform_delete(op1: Dict[str, Any], op2: Dict[str, Any]) -> Dict[str, Any]:
        """Transform delete operation against another operation."""
        pos1 = op1["position"]
        length1 = op1["length"]
        
        if op2.get("type") == "insert":
            pos2 = op2["position"]
            if pos2 <= pos1:
                return {**op1, "position": pos1 + len(op2.get("text", ""))}
        elif op2.get("type") == "delete":
            pos2 = op2["position"]
            length2 = op2["length"]
            
            if pos2 + length2 <= pos1:
                return {**op1, "position": pos1 - length2}
            elif pos2 >= pos1 + length1:
                return op1
            else:
                # Overlapping deletes - complex case
                pass
        
        return op1
    
    @staticmethod
    def apply_operation(text: str, op: Dict[str, Any]) -> str:
        """Apply an operation to text."""
        op_type = op.get("type")
        pos = op.get("position", 0)
        
        if op_type == "insert":
            insert_text = op.get("text", "")
            return text[:pos] + insert_text + text[pos:]
        elif op_type == "delete":
            length = op.get("length", 0)
            return text[:pos] + text[pos + length:]
        elif op_type == "replace":
            length = op.get("length", 0)
            new_text = op.get("text", "")
            return text[:pos] + new_text + text[pos + length:]
        
        return text


class WebSocketHub:
    """
    Central hub for WebSocket connections and real-time collaboration.
    """
    
    def __init__(self):
        self.clients: Dict[str, ClientInfo] = {}
        self.rooms: Dict[str, Room] = {}
        self.connections: Dict[str, Any] = {}  # client_id -> WebSocket
        
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.operation_transform = OperationTransform()
        
        # Stats
        self.stats = {
            "total_connections": 0,
            "total_messages": 0,
            "rooms_created": 0
        }
    
    async def connect(
        self,
        websocket: Any,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        username: str = "Anonymous"
    ) -> str:
        """
        Handle new WebSocket connection.
        
        Returns:
            client_id
        """
        client_id = client_id or str(uuid.uuid4())
        
        # Create client info
        client = ClientInfo(
            client_id=client_id,
            user_id=user_id,
            username=username,
            color=self._generate_color(client_id)
        )
        
        self.clients[client_id] = client
        self.connections[client_id] = websocket
        self.stats["total_connections"] += 1
        
        # Send connection confirmation
        await self._send(client_id, Message(
            type=MessageType.CONNECT,
            payload={
                "client_id": client_id,
                "client_info": client.to_dict()
            }
        ))
        
        return client_id
    
    async def disconnect(self, client_id: str):
        """Handle client disconnection."""
        client = self.clients.get(client_id)
        if not client:
            return
        
        # Leave all rooms
        for room_id in list(client.rooms):
            await self.leave_room(client_id, room_id)
        
        # Remove client
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.connections:
            del self.connections[client_id]
    
    async def handle_message(self, client_id: str, data: str):
        """Handle incoming message from client."""
        try:
            message = Message.from_json(data)
            message.sender_id = client_id
            
            self.stats["total_messages"] += 1
            
            # Update client activity
            if client_id in self.clients:
                self.clients[client_id].last_active = datetime.now().isoformat()
            
            # Route message
            await self._route_message(message)
            
            # Call registered handlers
            handlers = self.message_handlers.get(message.type, [])
            for handler in handlers:
                await handler(message)
                
        except Exception as e:
            await self._send(client_id, Message(
                type=MessageType.ERROR,
                payload={"error": str(e)}
            ))
    
    async def _route_message(self, message: Message):
        """Route message to appropriate handler."""
        handlers = {
            MessageType.PING: self._handle_ping,
            MessageType.JOIN_ROOM: self._handle_join_room,
            MessageType.LEAVE_ROOM: self._handle_leave_room,
            MessageType.CURSOR_MOVE: self._handle_cursor_move,
            MessageType.SELECTION_CHANGE: self._handle_selection_change,
            MessageType.CODE_CHANGE: self._handle_code_change,
            MessageType.CHAT_MESSAGE: self._handle_chat_message,
            MessageType.TASK_START: self._handle_task_start,
            MessageType.TASK_PROGRESS: self._handle_task_progress,
            MessageType.TASK_COMPLETE: self._handle_task_complete,
        }
        
        handler = handlers.get(message.type)
        if handler:
            await handler(message)
    
    async def _handle_ping(self, message: Message):
        """Handle ping message."""
        await self._send(message.sender_id, Message(
            type=MessageType.PONG,
            payload={"timestamp": datetime.now().isoformat()}
        ))
    
    async def _handle_join_room(self, message: Message):
        """Handle room join request."""
        client_id = message.sender_id
        room_id = message.payload.get("room_id")
        
        if not room_id:
            # Create new room
            room_id = str(uuid.uuid4())
            room = Room(
                room_id=room_id,
                name=message.payload.get("room_name", f"Room {room_id[:8]}")
            )
            self.rooms[room_id] = room
            self.stats["rooms_created"] += 1
        
        if room_id not in self.rooms:
            await self._send(client_id, Message(
                type=MessageType.ERROR,
                payload={"error": f"Room {room_id} not found"}
            ))
            return
        
        room = self.rooms[room_id]
        client = self.clients.get(client_id)
        
        if client:
            room.clients[client_id] = client
            client.rooms.add(room_id)
            
            # Send room state to joining client
            await self._send(client_id, Message(
                type=MessageType.ROOM_STATE,
                room_id=room_id,
                payload=room.to_dict()
            ))
            
            # Broadcast presence update
            await self._broadcast_to_room(room_id, Message(
                type=MessageType.PRESENCE_UPDATE,
                room_id=room_id,
                payload={
                    "action": "join",
                    "client": client.to_dict()
                }
            ), exclude=[client_id])
    
    async def leave_room(self, client_id: str, room_id: str):
        """Handle room leave."""
        room = self.rooms.get(room_id)
        client = self.clients.get(client_id)
        
        if room and client_id in room.clients:
            del room.clients[client_id]
            
            # Broadcast presence update
            await self._broadcast_to_room(room_id, Message(
                type=MessageType.PRESENCE_UPDATE,
                room_id=room_id,
                payload={
                    "action": "leave",
                    "client_id": client_id
                }
            ))
            
            # Remove empty rooms
            if not room.clients:
                del self.rooms[room_id]
        
        if client:
            client.rooms.discard(room_id)
    
    async def _handle_leave_room(self, message: Message):
        """Handle room leave request."""
        await self.leave_room(message.sender_id, message.room_id)
    
    async def _handle_cursor_move(self, message: Message):
        """Handle cursor movement."""
        client = self.clients.get(message.sender_id)
        if client:
            client.cursor_position = message.payload.get("position")
            
            # Broadcast to room
            if message.room_id:
                await self._broadcast_to_room(message.room_id, Message(
                    type=MessageType.CURSOR_MOVE,
                    room_id=message.room_id,
                    payload={
                        "client_id": message.sender_id,
                        "position": client.cursor_position,
                        "username": client.username,
                        "color": client.color
                    }
                ), exclude=[message.sender_id])
    
    async def _handle_selection_change(self, message: Message):
        """Handle selection change."""
        client = self.clients.get(message.sender_id)
        if client:
            client.selection = message.payload.get("selection")
            
            if message.room_id:
                await self._broadcast_to_room(message.room_id, Message(
                    type=MessageType.SELECTION_CHANGE,
                    room_id=message.room_id,
                    payload={
                        "client_id": message.sender_id,
                        "selection": client.selection,
                        "username": client.username,
                        "color": client.color
                    }
                ), exclude=[message.sender_id])
    
    async def _handle_code_change(self, message: Message):
        """Handle code change with operation transform."""
        room = self.rooms.get(message.room_id)
        if not room:
            return
        
        operation = message.payload.get("operation")
        if operation:
            # Apply operation to room's code
            room.code = self.operation_transform.apply_operation(room.code, operation)
            
            # Add to history
            room.history.append({
                "operation": operation,
                "sender_id": message.sender_id,
                "timestamp": message.timestamp
            })
            
            # Broadcast to other clients
            await self._broadcast_to_room(message.room_id, Message(
                type=MessageType.CODE_CHANGE,
                room_id=message.room_id,
                payload={
                    "operation": operation,
                    "sender_id": message.sender_id,
                    "code": room.code  # Include full code for sync
                }
            ), exclude=[message.sender_id])
    
    async def _handle_chat_message(self, message: Message):
        """Handle chat message."""
        client = self.clients.get(message.sender_id)
        
        # Broadcast to room
        if message.room_id:
            await self._broadcast_to_room(message.room_id, Message(
                type=MessageType.CHAT_MESSAGE,
                room_id=message.room_id,
                payload={
                    "sender_id": message.sender_id,
                    "username": client.username if client else "Unknown",
                    "message": message.payload.get("message"),
                    "timestamp": message.timestamp
                }
            ))
    
    async def _handle_task_start(self, message: Message):
        """Handle task start."""
        room = self.rooms.get(message.room_id)
        if room:
            room.task_id = message.payload.get("task_id")
            room.task_status = "running"
            
            await self._broadcast_to_room(message.room_id, Message(
                type=MessageType.TASK_START,
                room_id=message.room_id,
                payload=message.payload
            ))
    
    async def _handle_task_progress(self, message: Message):
        """Handle task progress update."""
        if message.room_id:
            await self._broadcast_to_room(message.room_id, Message(
                type=MessageType.TASK_PROGRESS,
                room_id=message.room_id,
                payload=message.payload
            ))
    
    async def _handle_task_complete(self, message: Message):
        """Handle task completion."""
        room = self.rooms.get(message.room_id)
        if room:
            room.task_status = "completed"
            room.code = message.payload.get("code", room.code)
            
            await self._broadcast_to_room(message.room_id, Message(
                type=MessageType.TASK_COMPLETE,
                room_id=message.room_id,
                payload=message.payload
            ))
    
    async def _send(self, client_id: str, message: Message):
        """Send message to a specific client."""
        websocket = self.connections.get(client_id)
        if websocket:
            try:
                await websocket.send_text(message.to_json())
            except Exception:
                await self.disconnect(client_id)
    
    async def _broadcast_to_room(
        self,
        room_id: str,
        message: Message,
        exclude: Optional[List[str]] = None
    ):
        """Broadcast message to all clients in a room."""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        exclude = exclude or []
        
        for client_id in room.clients:
            if client_id not in exclude:
                await self._send(client_id, message)
    
    async def broadcast(self, message: Message, exclude: Optional[List[str]] = None):
        """Broadcast message to all connected clients."""
        exclude = exclude or []
        
        for client_id in self.clients:
            if client_id not in exclude:
                await self._send(client_id, message)
    
    def on_message(self, message_type: MessageType):
        """Decorator to register message handler."""
        def decorator(func: Callable):
            if message_type not in self.message_handlers:
                self.message_handlers[message_type] = []
            self.message_handlers[message_type].append(func)
            return func
        return decorator
    
    def _generate_color(self, client_id: str) -> str:
        """Generate a consistent color for a client."""
        colors = [
            "#667eea", "#764ba2", "#22c55e", "#f59e0b",
            "#ef4444", "#06b6d4", "#8b5cf6", "#ec4899"
        ]
        hash_val = int(hashlib.md5(client_id.encode()).hexdigest(), 16)
        return colors[hash_val % len(colors)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hub statistics."""
        return {
            **self.stats,
            "active_connections": len(self.clients),
            "active_rooms": len(self.rooms),
            "clients": [c.to_dict() for c in self.clients.values()],
            "rooms": [r.to_dict() for r in self.rooms.values()]
        }
    
    def create_room(
        self,
        name: str,
        code: str = "",
        language: str = "python"
    ) -> Room:
        """Create a new room."""
        room = Room(
            room_id=str(uuid.uuid4()),
            name=name,
            code=code,
            language=language
        )
        self.rooms[room.room_id] = room
        self.stats["rooms_created"] += 1
        return room


class CollaborationSession:
    """
    High-level collaboration session manager.
    
    Provides easy-to-use API for real-time collaboration.
    """
    
    def __init__(self, hub: WebSocketHub, room_id: str, client_id: str):
        self.hub = hub
        self.room_id = room_id
        self.client_id = client_id
    
    @property
    def room(self) -> Optional[Room]:
        """Get the current room."""
        return self.hub.rooms.get(self.room_id)
    
    @property
    def code(self) -> str:
        """Get current code in the room."""
        room = self.room
        return room.code if room else ""
    
    async def send_code_change(self, operation: Dict[str, Any]):
        """Send a code change operation."""
        message = Message(
            type=MessageType.CODE_CHANGE,
            room_id=self.room_id,
            sender_id=self.client_id,
            payload={"operation": operation}
        )
        await self.hub.handle_message(self.client_id, message.to_json())
    
    async def send_cursor_position(self, line: int, column: int):
        """Send cursor position update."""
        message = Message(
            type=MessageType.CURSOR_MOVE,
            room_id=self.room_id,
            sender_id=self.client_id,
            payload={"position": {"line": line, "column": column}}
        )
        await self.hub.handle_message(self.client_id, message.to_json())
    
    async def send_chat(self, text: str):
        """Send a chat message."""
        message = Message(
            type=MessageType.CHAT_MESSAGE,
            room_id=self.room_id,
            sender_id=self.client_id,
            payload={"message": text}
        )
        await self.hub.handle_message(self.client_id, message.to_json())
    
    async def start_task(self, task_id: str, description: str):
        """Start a collaborative task."""
        message = Message(
            type=MessageType.TASK_START,
            room_id=self.room_id,
            sender_id=self.client_id,
            payload={
                "task_id": task_id,
                "description": description
            }
        )
        await self.hub.handle_message(self.client_id, message.to_json())
    
    async def update_progress(self, progress: float, status: str):
        """Update task progress."""
        message = Message(
            type=MessageType.TASK_PROGRESS,
            room_id=self.room_id,
            sender_id=self.client_id,
            payload={
                "progress": progress,
                "status": status
            }
        )
        await self.hub.handle_message(self.client_id, message.to_json())
    
    async def complete_task(self, code: str, result: Dict[str, Any]):
        """Complete a task and share result."""
        message = Message(
            type=MessageType.TASK_COMPLETE,
            room_id=self.room_id,
            sender_id=self.client_id,
            payload={
                "code": code,
                "result": result
            }
        )
        await self.hub.handle_message(self.client_id, message.to_json())
    
    def get_collaborators(self) -> List[ClientInfo]:
        """Get list of collaborators in the room."""
        room = self.room
        if room:
            return list(room.clients.values())
        return []


# Global hub instance
_hub: Optional[WebSocketHub] = None


def create_hub() -> WebSocketHub:
    """Create or get the global WebSocket hub."""
    global _hub
    if _hub is None:
        _hub = WebSocketHub()
    return _hub
