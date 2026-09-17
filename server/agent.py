import json
import re
import time
import uuid
from typing import List, Dict, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, agente autonomo de desenvolvimento.

REGRA ABSOLUTA: Use APENAS este formato para acoes, NUNCA outro:

[TOOL]{"tool": "nome", "args": {"param": "valor"}}[/TOOL]

EXEMPLOS CORRETOS:
[TOOL]{"tool": "create_project", "args": {"name": "calc", "language": "cpp"}}[/TOOL]
[TOOL]{"tool": "write_file", "args": {"path": "/caminho/arquivo", "content": "codigo"}}[/TOOL]
[TOOL]{"tool": "bash", "args": {"command": "g++ main.cpp -o app"}}[/TOOL]
[TOOL]{"tool": "done", "args": {"summary": "Pronto"}}[/TOOL]

NUNCA USE:
- ```json { ... } ``` (ERRADO)
- {"tool": ...} sem [TOOL] (ERRADO)
- Texto explicativo antes do [TOOL] (ERRADO)

FERRAMENTAS:
- bash: {"command": "comando"}
- read_file: {"path": "caminho"}
- write_file: {"path": "caminho", "content": "texto"}
- list_dir: {"path": "."}
- create_project: {"name": "nome", "language": "cpp|python|html|java"}
- memory_save: {"key": "chave", "value": "valor"}
- memory_load: {"key": "chave"}
- memory_list: {}
- python_exec: {"code": "print(1)"}
- done: {"summary": "resumo final"}

REGRAS:
1. UMA acao por resposta. So uma linha [TOOL]...[/TOOL].
2. NUNCA alucine sucesso. So diga OK se a ferramenta retornou OK.
3. NUNCA repita acao que falhou mais de 2x.
4. Codigo COMPLETO, nunca esqueletos.
5. Se compilacao falhar: leia erro, corrija, recompile.
6. Use caminhos absolutos: /content/ForgeAgent/Drive/projects/...

FLUXO:
1. create_project
2. write_file (codigo completo)
3. bash (compilar/testar)
4. memory_save
5. done"""


class Agent:
    def __init__(self, llm_provider, tools=None):
        self.llm = llm_provider
        self.tools = tools or {}
        self.sessions = {}
        self.max_iterations = 30

    def create_session(self, project_id=None):
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = {
            "id": session_id,
            "project_id": project_id,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "status": "active",
            "created_at": time.time(),
            "action_count": 0,
            "consecutive_failures": 0
        }
        print(f"[Agent] Sessao criada: {session_id}", flush=True)
        return session_id

    def cancel_session(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "cancelled"

    def _parse_action(self, text):
        # Tentar JSON puro (compacto ou formatado)
        try:
            data = json.loads(text.strip())
            if "tool" in data:
                return data
        except json.JSONDecodeError:
            pass
        
        # Tentar JSON dentro de bloco de código markdown
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                if "tool" in data:
                    return data
            except json.JSONDecodeError:
                pass
        
        # Tentar JSON solto no texto (com quebras de linha)
        match = re.search(r'\{[\s\S]*?"tool"[\s\S]*?:[\s\S]*?"\w+"[\s\S]*?\}', text)
        if match:
            json_str = match.group(0)
            # Remover quebras de linha extras para facilitar parsing
            json_str = re.sub(r'\n\s*\n', '\n', json_str)
            try:
                data = json.loads(json_str)
                if "tool" in data:
                    return data
            except json.JSONDecodeError:
                pass
        
        return None

    def _execute_tool(self, action):
        tool_name = action.get("tool", "")
        args = action.get("args", {})
        if tool_name not in self.tools:
            return {"success": False, "error": f"Ferramenta desconhecida: {tool_name}"}
        try:
            result = self.tools[tool_name](**args)
            return {"success": True, "tool": tool_name, "result": result}
        except Exception as e:
            return {"success": False, "tool": tool_name, "error": str(e)}

    def run(self, session_id, user_message, event_callback=None):
        if session_id not in self.sessions:
            return "Sessao nao encontrada"
        session = self.sessions[session_id]
        if session["status"] != "active":
            return "Sessao nao ativa"
        session["messages"].append({"role": "user", "content": user_message})
        if event_callback:
            event_callback({"type": "user_message", "content": user_message})
        final_response = ""
        for iteration in range(self.max_iterations):
            if session["status"] == "cancelled":
                return "Sessao cancelada"
            print(f"[Agent] Iteracao {iteration + 1}/{self.max_iterations}", flush=True)
            try:
                response = self.llm.generate(
                    messages=session["messages"],
                    max_tokens=4096,
                    temperature=0.2
                )
            except Exception as e:
                error_msg = f"Erro ao gerar: {str(e)}"
                if event_callback:
                    event_callback({"type": "agent_message", "content": error_msg})
                return error_msg
            action = self._parse_action(response)
            if action:
                tool_name = action.get("tool", "unknown")
                if tool_name == "done":
                    summary = action.get("args", {}).get("summary", "Tarefa concluida")
                    final_response = summary
                    session["messages"].append({"role": "assistant", "content": response})
                    if event_callback:
                        event_callback({"type": "agent_message", "content": final_response})
                        event_callback({"type": "done"})
                    break
                session["action_count"] += 1
                print(f"[Agent] Acao #{session['action_count']}: {tool_name}", flush=True)
                if event_callback:
                    event_callback({"type": "tool_call", "tool": tool_name, "args": action.get("args", {})})
                result = self._execute_tool(action)
                if event_callback:
                    event_callback({
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": result.get("result", result.get("error", "")),
                        "success": result.get("success", False)
                    })
                if result["success"]:
                    session["consecutive_failures"] = 0
                    result_text = f"[TOOL_OK] {tool_name}: {result['result']}"
                else:
                    session["consecutive_failures"] += 1
                    result_text = f"[TOOL_ERROR] {tool_name}: {result['error']}"
                    if session["consecutive_failures"] >= 5:
                        final_response = f"Muitas falhas. Ultimo erro: {result['error']}"
                        if event_callback:
                            event_callback({"type": "agent_message", "content": final_response})
                            event_callback({"type": "done"})
                        break
                session["messages"].append({"role": "assistant", "content": response})
                session["messages"].append({"role": "tool", "content": result_text})
            else:
                final_response = response.strip()
                session["messages"].append({"role": "assistant", "content": final_response})
                if event_callback:
                    event_callback({"type": "agent_message", "content": final_response})
                    event_callback({"type": "done"})
                break
        if not final_response:
            final_response = f"Tarefa concluida apos {session['action_count']} acoes."
            if event_callback:
                event_callback({"type": "agent_message", "content": final_response})
                event_callback({"type": "done"})
        return final_response

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def get_all_sessions(self):
        return list(self.sessions.values())
