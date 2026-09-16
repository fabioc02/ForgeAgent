import os
import sys
import json
import time
import uuid
import asyncio
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.hardware_detect import detect_hardware, get_model_for_mode
from server.llm_provider import LLMProvider
from server.agent import Agent
from server.tools.registry import get_all_tools


class AppState:
    def __init__(self):
        self.llm: Optional[LLMProvider] = None
        self.agent: Optional[Agent] = None
        self.hardware: Dict = {}
        self.websocket_connections: Dict[str, List[WebSocket]] = {}
        self.sessions_meta: Dict[str, Dict] = {}
        self.projects: Dict[str, Dict] = {}
        self.initialized = False
    
    def load_projects(self):
        projects_dir = os.path.abspath('Drive/projects')
        os.makedirs(projects_dir, exist_ok=True)
        for name in os.listdir(projects_dir):
            pdir = os.path.join(projects_dir, name)
            if os.path.isdir(pdir):
                self.projects[name] = {
                    'id': name,
                    'name': name,
                    'language': 'unknown',
                    'created_at': time.time(),
                    'tasks_count': 0,
                    'path': pdir
                }


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('[ForgeAgent] === INICIANDO ===', flush=True)
    
    state.hardware = detect_hardware()
    print('[ForgeAgent] Hardware: ' + json.dumps(state.hardware, indent=2), flush=True)
    
    # Usar modelo 7B AWQ (4.5GB, perfeito para T4)
    model_name = 'Qwen/Qwen2.5-Coder-7B-Instruct-GGUF'
    backend = 'transformers'
    
    print('[ForgeAgent] Modelo: ' + model_name, flush=True)
    print('[ForgeAgent] Backend: ' + backend, flush=True)
    
    try:
        print('[ForgeAgent] Carregando modelo...', flush=True)
        state.llm = LLMProvider(model_name=model_name, backend=backend)
        state.llm.initialize()
        
        tools = get_all_tools()
        state.agent = Agent(llm_provider=state.llm, tools=tools)
        state.initialized = True
        print('[ForgeAgent] OK - ' + str(len(tools)) + ' ferramentas carregadas', flush=True)
    except Exception as e:
        print('[ForgeAgent] ERRO: ' + str(e), flush=True)
        import traceback
        traceback.print_exc()
    
    state.load_projects()
    print('[ForgeAgent] ' + str(len(state.projects)) + ' projetos carregados', flush=True)
    print('[ForgeAgent] === PRONTO ===', flush=True)
    
    yield
    
    print('[ForgeAgent] Encerrando...', flush=True)


app = FastAPI(title='ForgeAgent', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class RunRequest(BaseModel):
    message: str
    project_id: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    language: str = 'cpp'


class TaskCreate(BaseModel):
    description: str


class BridgeExecute(BaseModel):
    command: str


@app.get('/api/health')
async def health():
    runtime_status = {
        'mode': state.hardware.get('mode', 'cpu'),
        'model': state.llm.model_name if state.llm else 'not_loaded',
        'backend': state.llm.backend if state.llm else 'none',
        'gpu_name': state.hardware.get('gpu_name'),
        'status': 'ready' if state.initialized else 'error'
    }
    return {
        'status': 'ok',
        'bridge_connected': False,
        'runtime': runtime_status,
        'hardware': state.hardware
    }


@app.get('/api/projects')
async def list_projects():
    return {'projects': list(state.projects.values())}


@app.post('/api/projects')
async def create_project(req: ProjectCreate):
    if not state.agent:
        raise HTTPException(503, 'Agente nao inicializado')
    
    result = state.agent.tools['create_project'](name=req.name, language=req.language)
    
    state.projects[req.name] = {
        'id': req.name,
        'name': req.name,
        'language': req.language,
        'created_at': time.time(),
        'tasks_count': 0,
        'path': os.path.abspath('Drive/projects/' + req.name)
    }
    
    return {'status': 'ok', 'result': result, 'project': state.projects[req.name]}


@app.get('/api/projects/{project_id}/tasks')
async def list_tasks(project_id: str):
    return {'tasks': []}


@app.post('/api/projects/{project_id}/tasks')
async def create_task(project_id: str, req: TaskCreate):
    return {'status': 'ok', 'task': {'id': str(uuid.uuid4())[:8], 'description': req.description}}


@app.post('/api/agent/run')
async def run_agent(req: RunRequest):
    if not state.agent or not state.initialized:
        raise HTTPException(503, 'Agente nao inicializado')
    
    session_id = state.agent.create_session(project_id=req.project_id)
    state.sessions_meta[session_id] = {
        'id': session_id,
        'created_at': time.time(),
        'status': 'running'
    }
    
    asyncio.create_task(run_agent_async(session_id, req.message))
    
    return {'status': 'ok', 'session_id': session_id}


async def run_agent_async(session_id: str, message: str):
    def event_callback(event):
        asyncio.create_task(broadcast_to_session(session_id, event))
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: state.agent.run(session_id, message, event_callback)
        )
        state.sessions_meta[session_id]['status'] = 'done'
    except Exception as e:
        print('[Agent] Erro: ' + str(e), flush=True)
        await broadcast_to_session(session_id, {
            'type': 'agent_message',
            'content': 'Erro: ' + str(e)
        })
        state.sessions_meta[session_id]['status'] = 'error'


async def broadcast_to_session(session_id: str, event: Dict):
    if session_id in state.websocket_connections:
        dead = []
        for ws in state.websocket_connections[session_id]:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            state.websocket_connections[session_id].remove(ws)


@app.post('/api/sessions/{session_id}/cancel')
async def cancel_session(session_id: str):
    if state.agent:
        state.agent.cancel_session(session_id)
    if session_id in state.sessions_meta:
        state.sessions_meta[session_id]['status'] = 'cancelled'
    return {'status': 'ok'}


@app.get('/api/sessions')
async def list_sessions():
    return {'sessions': list(state.sessions_meta.values())}


@app.get('/api/github/status')
async def github_status():
    return {'connected': False, 'repo': None, 'message': 'GitHub nao configurado'}


@app.get('/api/bridge/status')
async def bridge_status():
    return {'connected': False, 'message': 'Bridge local (Colab)'}


@app.post('/api/bridge/execute')
async def bridge_execute(req: BridgeExecute):
    if not state.agent:
        raise HTTPException(503, 'Agente nao inicializado')
    
    try:
        result = state.agent.tools['terminal'](command=req.command)
        return {'status': 'ok', 'output': result}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@app.get('/api/runtime')
async def runtime_status():
    if not state.llm:
        return {'status': 'not_initialized'}
    return state.llm.get_status()


@app.websocket('/ws/sessions/{session_id}')
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    if session_id not in state.websocket_connections:
        state.websocket_connections[session_id] = []
    state.websocket_connections[session_id].append(websocket)
    
    print('[WS] Conectado: sessao ' + session_id, flush=True)
    
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        state.websocket_connections[session_id].remove(websocket)
        print('[WS] Desconectado: sessao ' + session_id, flush=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    print('[Main] Iniciando servidor na porta ' + str(port), flush=True)
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=port,
        reload=False,
        log_level='info'
    )
