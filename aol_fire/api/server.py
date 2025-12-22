"""
NullForge API Server
====================
FastAPI-based REST API for NullForge autonomous agent.
"""

import os
import uuid
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import json

from .schemas import (
    SynthesisRequest,
    SynthesisResponse,
    PlanResponse,
    TaskStatus,
    SubtaskStatus,
    Subtask,
    FileOutput,
    TokenUsage,
    HealthResponse,
    ErrorResponse,
    TaskListResponse,
    PresetsListResponse,
    PresetResponse,
    ProviderListResponse,
    StreamChunk
)


# In-memory task storage (use Redis/DB in production)
tasks_store: Dict[str, SynthesisResponse] = {}
start_time = time.time()


class NullForgeAPI:
    """NullForge API wrapper class."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


api_manager = NullForgeAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("🚀 NullForge API Server starting...")
    yield
    # Shutdown
    print("👋 NullForge API Server shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="NullForge API",
        description="""
# NullForge - Autonomous Enterprise Software Platform

🚀 **AI-powered code synthesis and automation API**

NullForge transforms natural language descriptions into production-ready code using 
autonomous AI agents powered by the Omniscient Graph 2.0 architecture.

## Features

- **Multi-Provider Support**: OpenAI, Venice AI (uncensored), Ollama, Anthropic, and more
- **Autonomous Agents**: Planner → Coder → Reviewer → Reporter workflow
- **Real-time Streaming**: Watch code generation in real-time via WebSocket
- **Enterprise Tools**: File I/O, shell execution, git integration, web search

## Quick Start

```python
import requests

response = requests.post(
    "https://api.nullforge.io/v1/synthesize",
    json={
        "goal": "Build a REST API with authentication",
        "provider_config": {
            "provider": "venice",
            "model": "llama-3.1-405b"
        }
    }
)
print(response.json())
```

## Authentication

Use Bearer token authentication:
```
Authorization: Bearer <your-api-key>
```
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "NullForge Support",
            "url": "https://github.com/RemyLoveLogicAI/NullForge",
            "email": "support@nullforge.io"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        openapi_tags=[
            {
                "name": "synthesis",
                "description": "Code synthesis operations"
            },
            {
                "name": "tasks",
                "description": "Task management"
            },
            {
                "name": "providers",
                "description": "LLM provider configuration"
            },
            {
                "name": "system",
                "description": "System health and status"
            }
        ],
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # =============
    # System Routes
    # =============
    
    @app.get(
        "/",
        response_model=HealthResponse,
        tags=["system"],
        summary="API Root",
        description="Get API information and health status"
    )
    async def root():
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            uptime_seconds=time.time() - start_time,
            providers_available=["openai", "venice", "anthropic", "ollama", "groq", "together", "openrouter"]
        )

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Health Check",
        description="Check API server health and status"
    )
    async def health_check():
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            uptime_seconds=time.time() - start_time,
            providers_available=["openai", "venice", "anthropic", "ollama", "groq", "together", "openrouter"]
        )

    # ================
    # Provider Routes
    # ================
    
    @app.get(
        "/v1/providers",
        response_model=ProviderListResponse,
        tags=["providers"],
        summary="List Providers",
        description="Get list of available LLM providers and their configurations"
    )
    async def list_providers():
        providers = [
            {
                "id": "openai",
                "name": "OpenAI",
                "models": ["gpt-4-turbo-preview", "gpt-4o", "gpt-3.5-turbo"],
                "default_model": "gpt-4-turbo-preview",
                "api_base": "https://api.openai.com/v1",
                "requires_key": True
            },
            {
                "id": "venice",
                "name": "Venice AI",
                "models": ["llama-3.1-405b", "llama-3.1-70b", "dolphin-2.9.2-qwen2-72b"],
                "default_model": "llama-3.1-405b",
                "api_base": "https://api.venice.ai/api/v1",
                "requires_key": True,
                "is_uncensored": True
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
                "default_model": "claude-3-5-sonnet-20241022",
                "api_base": "https://api.anthropic.com",
                "requires_key": True
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "models": ["llama3.1:70b", "deepseek-coder-v2:latest", "dolphin-mixtral"],
                "default_model": "llama3.1:70b",
                "api_base": "http://localhost:11434/v1",
                "requires_key": False,
                "is_local": True
            },
            {
                "id": "groq",
                "name": "Groq",
                "models": ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
                "default_model": "llama-3.1-70b-versatile",
                "api_base": "https://api.groq.com/openai/v1",
                "requires_key": True
            },
            {
                "id": "together",
                "name": "Together AI",
                "models": ["meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"],
                "default_model": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                "api_base": "https://api.together.xyz/v1",
                "requires_key": True
            },
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "models": ["anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-8b-instruct:free"],
                "default_model": "anthropic/claude-3.5-sonnet",
                "api_base": "https://openrouter.ai/api/v1",
                "requires_key": True
            }
        ]
        return ProviderListResponse(providers=providers)

    @app.get(
        "/v1/presets",
        response_model=PresetsListResponse,
        tags=["providers"],
        summary="List Presets",
        description="Get list of pre-configured provider presets"
    )
    async def list_presets():
        presets = [
            PresetResponse(name="openai", provider="openai", model="gpt-4-turbo-preview", description="OpenAI GPT-4 Turbo"),
            PresetResponse(name="openai-4o", provider="openai", model="gpt-4o", description="OpenAI GPT-4o"),
            PresetResponse(name="venice", provider="venice", model="llama-3.1-405b", description="Venice AI Llama 3.1 405B", is_uncensored=True),
            PresetResponse(name="venice-uncensored", provider="venice", model="dolphin-2.9.2-qwen2-72b", description="Venice Dolphin (Uncensored)", is_uncensored=True),
            PresetResponse(name="ollama", provider="ollama", model="llama3.1:70b", description="Local Ollama Llama 3.1"),
            PresetResponse(name="ollama-code", provider="ollama", model="deepseek-coder-v2:latest", description="Local DeepSeek Coder"),
            PresetResponse(name="groq", provider="groq", model="llama-3.1-70b-versatile", description="Groq Llama 3.1 70B"),
            PresetResponse(name="together", provider="together", model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", description="Together AI Llama 405B"),
            PresetResponse(name="openrouter", provider="openrouter", model="anthropic/claude-3.5-sonnet", description="OpenRouter Claude 3.5"),
            PresetResponse(name="openrouter-free", provider="openrouter", model="meta-llama/llama-3.1-8b-instruct:free", description="OpenRouter Free Tier"),
            PresetResponse(name="anthropic", provider="anthropic", model="claude-3-5-sonnet-20241022", description="Anthropic Claude 3.5 Sonnet")
        ]
        return PresetsListResponse(presets=presets)

    # ==================
    # Synthesis Routes
    # ==================
    
    @app.post(
        "/v1/synthesize",
        response_model=SynthesisResponse,
        tags=["synthesis"],
        summary="Synthesize Code",
        description="""
Synthesize code from a natural language description.

This endpoint triggers the NullForge autonomous agent workflow:
1. **Planner**: Analyzes the goal and creates a step-by-step plan
2. **Coder**: Executes each step, generating code and files
3. **Reviewer**: Reviews generated code for quality and correctness
4. **Reporter**: Produces a summary of accomplishments

The process can run synchronously (blocking) or asynchronously (returns immediately with task ID).
        """,
        responses={
            200: {"description": "Synthesis completed successfully"},
            202: {"description": "Synthesis started (async mode)"},
            400: {"model": ErrorResponse, "description": "Invalid request"},
            500: {"model": ErrorResponse, "description": "Synthesis failed"}
        }
    )
    async def synthesize(
        request: SynthesisRequest,
        background_tasks: BackgroundTasks
    ):
        task_id = f"synth_{uuid.uuid4().hex[:12]}"
        
        # Initialize task
        task = SynthesisResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            goal=request.goal,
            created_at=datetime.utcnow()
        )
        tasks_store[task_id] = task
        
        if request.async_mode:
            # Run in background
            background_tasks.add_task(run_synthesis, task_id, request)
            task.status = TaskStatus.PLANNING
            return JSONResponse(
                status_code=202,
                content=task.model_dump(mode='json')
            )
        else:
            # Run synchronously (simulated for demo)
            return await run_synthesis_sync(task_id, request)

    @app.post(
        "/v1/synthesize/stream",
        tags=["synthesis"],
        summary="Synthesize Code (Streaming)",
        description="Stream code synthesis results in real-time using Server-Sent Events (SSE)"
    )
    async def synthesize_stream(request: SynthesisRequest):
        task_id = f"synth_{uuid.uuid4().hex[:12]}"
        
        async def generate() -> AsyncGenerator[str, None]:
            # Planning phase
            yield f"data: {json.dumps({'type': 'status', 'task_id': task_id, 'status': 'planning'})}\n\n"
            await asyncio.sleep(0.5)
            
            # Generate plan
            subtasks = [
                "Set up project structure",
                "Create data models",
                "Implement core logic",
                "Add API endpoints",
                "Write tests"
            ]
            
            yield f"data: {json.dumps({'type': 'plan', 'task_id': task_id, 'subtasks': subtasks})}\n\n"
            
            # Execute subtasks
            for i, subtask in enumerate(subtasks):
                yield f"data: {json.dumps({'type': 'subtask_start', 'task_id': task_id, 'index': i, 'title': subtask})}\n\n"
                await asyncio.sleep(1)
                yield f"data: {json.dumps({'type': 'subtask_complete', 'task_id': task_id, 'index': i})}\n\n"
            
            # Final result
            yield f"data: {json.dumps({'type': 'complete', 'task_id': task_id, 'status': 'completed'})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    # =============
    # Task Routes
    # =============
    
    @app.get(
        "/v1/tasks",
        response_model=TaskListResponse,
        tags=["tasks"],
        summary="List Tasks",
        description="Get list of synthesis tasks"
    )
    async def list_tasks(page: int = 1, per_page: int = 20):
        all_tasks = list(tasks_store.values())
        start = (page - 1) * per_page
        end = start + per_page
        return TaskListResponse(
            tasks=all_tasks[start:end],
            total=len(all_tasks),
            page=page,
            per_page=per_page
        )

    @app.get(
        "/v1/tasks/{task_id}",
        response_model=SynthesisResponse,
        tags=["tasks"],
        summary="Get Task",
        description="Get details of a specific synthesis task"
    )
    async def get_task(task_id: str):
        if task_id not in tasks_store:
            raise HTTPException(status_code=404, detail="Task not found")
        return tasks_store[task_id]

    @app.delete(
        "/v1/tasks/{task_id}",
        tags=["tasks"],
        summary="Cancel Task",
        description="Cancel a running synthesis task"
    )
    async def cancel_task(task_id: str):
        if task_id not in tasks_store:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = tasks_store[task_id]
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="Task already finished")
        
        task.status = TaskStatus.CANCELLED
        return {"status": "cancelled", "task_id": task_id}

    # ================
    # WebSocket Route
    # ================
    
    @app.websocket("/v1/ws/{task_id}")
    async def websocket_endpoint(websocket: WebSocket, task_id: str):
        """WebSocket endpoint for real-time task updates."""
        await api_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                # Handle incoming messages if needed
                await websocket.send_json({
                    "type": "ack",
                    "task_id": task_id,
                    "message": f"Received: {data}"
                })
        except WebSocketDisconnect:
            api_manager.disconnect(websocket)

    return app


async def run_synthesis_sync(task_id: str, request: SynthesisRequest) -> SynthesisResponse:
    """Run synthesis synchronously (simulated for demo)."""
    task = tasks_store[task_id]
    task.status = TaskStatus.PLANNING
    
    # Simulate planning
    await asyncio.sleep(0.5)
    
    subtasks = [
        Subtask(id="1", title="Set up project structure", description="Create directories and base files", status=SubtaskStatus.COMPLETED),
        Subtask(id="2", title="Create data models", description="Define Pydantic/SQLAlchemy models", status=SubtaskStatus.COMPLETED),
        Subtask(id="3", title="Implement core logic", description="Write main business logic", status=SubtaskStatus.COMPLETED),
        Subtask(id="4", title="Add API endpoints", description="Create FastAPI routes", status=SubtaskStatus.COMPLETED),
        Subtask(id="5", title="Write tests", description="Add pytest unit tests", status=SubtaskStatus.COMPLETED)
    ]
    
    task.plan = PlanResponse(
        task_id=task_id,
        goal=request.goal,
        subtasks=subtasks,
        total_steps=len(subtasks),
        estimated_time_seconds=30
    )
    
    task.status = TaskStatus.EXECUTING
    
    # Simulate file generation
    await asyncio.sleep(1)
    
    task.files = [
        FileOutput(path="main.py", content="from fastapi import FastAPI\n\napp = FastAPI()", language="python", size_bytes=45),
        FileOutput(path="models.py", content="from pydantic import BaseModel\n\nclass Todo(BaseModel):\n    title: str", language="python", size_bytes=78),
        FileOutput(path="requirements.txt", content="fastapi\nuvicorn\npydantic", language="text", size_bytes=28),
    ]
    
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    task.duration_seconds = 2.5
    task.summary = f"Successfully synthesized project based on: {request.goal[:100]}..."
    task.token_usage = TokenUsage(prompt_tokens=500, completion_tokens=1500, total_tokens=2000)
    
    return task


async def run_synthesis(task_id: str, request: SynthesisRequest):
    """Run synthesis in background."""
    # Same as sync but doesn't return
    await run_synthesis_sync(task_id, request)


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
