import os
import json
import time
import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from server.llm_provider import LLMProvider
from server.agent import Agent
from server.tools.registry import get_all_tools, get_tools_info

class AppState:
    def __init__(self):
        self.llm = None
        self.agent = None
        self.tools = None
        self.sessions_meta = {}

state = AppState()
_ws_clients: Dict[str, List] = {}

class ChatRequest(BaseModel):
    message: str
    project_id: str = None
    temperature: float = 0.2
    max_tokens: int = 4096

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[ForgeAgent] === INICIANDO ===", flush=True)
    try:
        import torch
        gpu_info = {
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "mode": "gpu" if torch.cuda.is_available() else "cpu"
        }
    except:
        gpu_info = {"gpu_available": False, "gpu_name": "CPU", "mode": "cpu"}
    print(f"[ForgeAgent] Hardware: {json.dumps(gpu_info, indent=2)}", flush=True)
    
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ForgeAgent] AVISO: GEMINI_API_KEY nao configurada", flush=True)
    else:
        try:
            state.llm = LLMProvider(model_name="gemini-2.5-pro", backend="gemini")
            state.llm.initialize(api_key=api_key)
            print(f"[ForgeAgent] Modelo: {state.llm.model_name}", flush=True)
        except Exception as e:
            print(f"[ForgeAgent] ERRO ao inicializar LLM: {e}", flush=True)
    
    state.tools = get_all_tools()
    print(f"[ForgeAgent] {len(state.tools)} ferramentas carregadas", flush=True)
    
    if state.llm:
        state.agent = Agent(state.llm, state.tools)
        print(f"[ForgeAgent] Agente criado", flush=True)
    
    projects_dir = "/content/ForgeAgent/Drive/projects"
    os.makedirs(projects_dir, exist_ok=True)
    projects_count = len([d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))])
    print(f"[ForgeAgent] {projects_count} projetos carregados", flush=True)
    print("[ForgeAgent] === PRONTO ===\n", flush=True)
    yield

app = FastAPI(title="ForgeAgent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    runtime = {}
    if state.llm:
        status = state.llm.get_status()
        runtime = {
            "mode": status.get("mode", "unknown"),
            "model": status.get("model", "unknown"),
            "backend": status.get("backend", "unknown"),
            "gpu_name": "NVIDIA L4" if status.get("mode") == "gpu" else "CPU",
            "status": "ready" if status.get("mode") != "error" else "error"
        }
    return {"status": "ok" if state.llm else "error", "bridge_connected": False, "runtime": runtime}

@app.get("/api/projects")
def get_projects():
    projects_dir = "/content/ForgeAgent/Drive/projects"
    os.makedirs(projects_dir, exist_ok=True)
    projects = []
    for name in os.listdir(projects_dir):
        project_dir = os.path.join(projects_dir, name)
        if os.path.isdir(project_dir):
            projects.append({"id": name, "name": name, "language": "unknown", "created_at": os.path.getctime(project_dir), "tasks_count": 0})
    return {"projects": projects}

@app.post("/api/agent/run")
def run_agent(req: ChatRequest):
    if not state.agent:
        raise HTTPException(status_code=503, detail="Agente nao inicializado")
    session_id = state.agent.create_session(project_id=req.project_id)
    def run():
        try:
            state.agent.run(session_id=session_id, user_message=req.message, event_callback=lambda evt: _broadcast_event(session_id, evt))
        except Exception as e:
            print(f"[Agent] Erro: {e}", flush=True)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return {"session_id": session_id}

@app.get("/api/tools")
def get_tools():
    return {"tools": get_tools_info()}

@app.websocket("/ws/sessions/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"[WS] Conectado: sessao {session_id}", flush=True)
    if session_id not in _ws_clients:
        _ws_clients[session_id] = []
    _ws_clients[session_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        pass
    finally:
        if session_id in _ws_clients:
            _ws_clients[session_id] = [w for w in _ws_clients[session_id] if w != websocket]

def _broadcast_event(session_id: str, event: Dict):
    if session_id in _ws_clients:
        for ws in _ws_clients[session_id]:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(ws.send_json(event), loop)
            except:
                pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
