"""
PiyP Reference Manager Backend.

FastAPI application with 6 API routers:
- Papers API: Paper management and metadata
- Search API: Multi-modal search (traditional, RAG, KG)
- Citations API: Citation generation and export
- Collections API: Paper organization
- Tasks API: Async task tracking
- Expansion API: Knowledge gap analysis and expansion

Real-time features via WebSocket for progress updates.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio
from datetime import datetime
from typing import Dict, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration
from .config import get_settings

# Import API routers
from .api.papers import router as papers_router
from .api.search import router as search_router
from .api.citations import router as citations_router
from .api.collections import router as collections_router
from .api.tasks import router as tasks_router
from .api.expansion import router as expansion_router

# Import services
from .services.agent_client import AgentClient

# Settings
settings = get_settings()

# FastAPI app
app = FastAPI(
    title="PiyP Reference Manager API",
    description="Backend API for PiyP Reference Manager with multi-modal search and agent coordination",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect WebSocket for user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Clean up empty user connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections for a user"""
        if user_id not in self.active_connections:
            return
        
        # Send to all user connections
        disconnected = set()
        
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except:
                # Mark for removal
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.active_connections[user_id].discard(connection)
    
    async def broadcast_to_user(self, user_id: str, event: str, data: dict):
        """Broadcast event to user"""
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_personal_message(message, user_id)

# Global connection manager
manager = ConnectionManager()

# API routers
app.include_router(papers_router, prefix="/api/papers", tags=["papers"])
app.include_router(search_router, prefix="/api/search", tags=["search"])  
app.include_router(citations_router, prefix="/api/citations", tags=["citations"])
app.include_router(collections_router, prefix="/api/collections", tags=["collections"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(expansion_router, prefix="/api/expansion", tags=["expansion"])

# Root endpoints
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "PiyP Reference Manager API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test agent connectivity
        agent_client = AgentClient()
        agent_status = await agent_client.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "agents": agent_status
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial connection message
        await manager.send_personal_message({
            "event": "connected",
            "message": "WebSocket connection established",
            "user_id": user_id
        }, user_id)
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_json()
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to ping
                    await manager.send_personal_message({
                        "event": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                
                elif message_type == "subscribe":
                    # Subscribe to specific events
                    events = message.get("events", [])
                    await manager.send_personal_message({
                        "event": "subscribed",
                        "events": events
                    }, user_id)
                
                else:
                    # Unknown message type
                    await manager.send_personal_message({
                        "event": "error",
                        "message": f"Unknown message type: {message_type}"
                    }, user_id)
                    
            except Exception as e:
                logger.error(f"WebSocket message handling error: {str(e)}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        manager.disconnect(websocket, user_id)

# Task progress WebSocket endpoint
@app.websocket("/ws/tasks/{task_id}")
async def task_websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task progress updates"""
    await websocket.accept()
    
    try:
        # Send initial task status
        agent_client = AgentClient()
        task_status = await agent_client.get_task_status(task_id)
        
        if task_status:
            await websocket.send_json({
                "type": "status",
                "task_id": task_id,
                **task_status
            })
        
        # Monitor task progress
        while True:
            # Check task status periodically
            await asyncio.sleep(2)
            
            task_status = await agent_client.get_task_status(task_id)
            
            if not task_status:
                # Task not found or completed
                await websocket.send_json({
                    "type": "error",
                    "message": "Task not found or completed"
                })
                break
            
            # Send status update
            await websocket.send_json({
                "type": "progress", 
                "task_id": task_id,
                **task_status
            })
            
            # Check if task is completed
            if task_status.get("status") in ["completed", "failed", "cancelled"]:
                await websocket.send_json({
                    "type": "completed",
                    "task_id": task_id,
                    **task_status
                })
                break
                
    except WebSocketDisconnect:
        logger.info(f"Task WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"Task WebSocket error: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting PiyP Reference Manager API")
    
    # Initialize agent client
    agent_client = AgentClient()
    await agent_client.initialize()
    
    logger.info("PiyP Reference Manager API started successfully")

# Shutdown event
@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down PiyP Reference Manager API")
    
    # Clean up WebSocket connections
    for user_id in list(manager.active_connections.keys()):
        for connection in list(manager.active_connections[user_id]):
            try:
                await connection.close()
            except:
                pass
        manager.active_connections[user_id].clear()
    
    logger.info("PiyP Reference Manager API shutdown complete")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Export connection manager for use in routers
__all__ = ["app", "manager"]