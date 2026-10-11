from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict, Any, List
import os

from .agent import VoiceAgent
from .config import AgentConfig, BASE_DIR

app = FastAPI(
    title="Home Credit LAP Voice Agent API",
    description="Backend API and State Machine Engine for AI Voice Qualification Agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

voice_agent = VoiceAgent()

class SessionStartRequest(BaseModel):
    customer_name: Optional[str] = None
    language_to_speak: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    customer_name: Optional[str] = None
    language_to_speak: Optional[str] = None

class ConfigUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    customer_name: Optional[str] = None
    agent_name: Optional[str] = None
    agent_gender: Optional[str] = None
    language_to_speak: Optional[str] = None
    additional_context_from_rag: Optional[str] = None

@app.get("/api/health")
async def health_check():
    return {"status": "online", "service": "Home Credit LAP Voice Agent"}

@app.post("/api/session/start")
async def start_session(req: Optional[SessionStartRequest] = None):
    voice_agent.reset_session()
    if req:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if updates:
            voice_agent.update_config(updates)
    result = voice_agent.process_customer_turn("")
    return result

@app.post("/api/session/reset")
async def reset_session():
    voice_agent.reset_session()
    return {"message": "Session reset successfully", "state": voice_agent.state_machine.state.to_dict()}

@app.post("/api/chat")
async def chat_turn(req: ChatRequest):
    updates = {}
    if req.customer_name:
        updates["customer_name"] = req.customer_name
    if req.language_to_speak:
        updates["language_to_speak"] = req.language_to_speak
    if updates:
        voice_agent.update_config(updates)
    result = voice_agent.process_customer_turn(req.message)
    return result

@app.get("/api/state")
async def get_current_state():
    return {
        "state": voice_agent.state_machine.state.to_dict(),
        "rendered_prompt": voice_agent.render_system_prompt()
    }

@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    voice_agent.update_config(updates)
    return {
        "message": "Configuration updated successfully",
        "config": updates,
        "rendered_prompt": voice_agent.render_system_prompt()
    }

@app.get("/api/prompt")
async def get_prompt():
    return {
        "raw_prompt": voice_agent.config.get_system_prompt(),
        "rendered_prompt": voice_agent.render_system_prompt()
    }

@app.get("/api/test-scenarios/run-all")
async def run_test_scenarios():
    import test_scenarios
    test_results = test_scenarios.run_all_evaluation_tests()
    return test_results

FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/style.css")
    async def serve_css():
        return FileResponse(FRONTEND_DIR / "style.css")

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(FRONTEND_DIR / "app.js")
