import json
import re
import time
import uuid
from typing import List, Dict, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, um agente autonomo de desenvolvimento.

FORMATO DE ACAO (OBRIGATORIO):
Use o formato JSON dentro de um bloco de codigo:

    {{"tool": "nome", "args": {{"param": "valor"}}}}

FERRAMENTAS DISPONIVEIS:
- bash: executa comando no terminal. args: {{"command": "ls -la"}}
- read_file: le arquivo. args: {{"path": "caminho"}}
- write_file: escreve arquivo. args: {{"path": "caminho", "content": "texto"}}
- list_dir: lista diretorio. args: {{"path": "."}}
- create_project: cria projeto. args: {{"name": "nome", "language": "cpp"}}
- memory_save: salva na memoria. args: {{"key": "chave", "value": "valor"}}
- memory_load: carrega da memoria. args: {{"key": "chave"}}
- memory_list: lista chaves. args: {{}}
- python_exec: executa codigo Python. args: {{"code": "print(1)"}}
- done: finaliza tarefa. args: {{"summary": "resumo"}}

REGRAS CRITICAS:
1. NUNCA alucine sucesso. So diga que funcionou se a ferramenta retornou OK.
2. SEMPRE valide apos cada acao usando list_dir ou read_file.
3. NUNCA repita a mesma acao mais de 2 vezes. Se falhar, mude estrategia.
4. Escreva codigo COMPLETO, nunca esqueletos.
5. Uma acao por vez. Aguarde o resultado.
6. Se compilacao falhar: leia o erro, corrija o codigo, recompile.
7. Use caminhos absolutos: /content/ForgeAgent/Drive/projects/...

FLUXO OBRIGATORIO PARA PROJETOS:
1. create_project(name, language)
2. write_file(path, content_completo)
3. bash(command="g++ src/main.cpp -o app")
4. bash(command="./app") para testar
5. memory_save(key, value)
6. done(summary="resumo")

EXEMPLO:
Usuario: "crie calculadora em C++"
Agente responde com JSON:
    {{"tool": "create_project", "args": {{"name": "calc", "language": "cpp"}}}}

Apos OK, proxima acao:
    {{"tool": "write_file", "args": {{"path": "/content/ForgeAgent/Drive/projects/calc/src/main.cpp", "content": "#include <iostream>\\nint main(){{...}}"}}}}

E assim por diante ate o done final."""


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
        # Tentar JSON puro
        try:
            data = json.loads(text.strip())
            if "tool" in data:
                return data
        except json.JSONDecodeError:
            pass
        # Tentar JSON dentro de texto
        match = re.search(r'\{\s*"tool"\s*:', text)
        if match:
            start = match.start()
            # Encontrar o fim do JSON
            brace_count = 0
            end = start
            for i in range(start, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            try:
                return json.loads(text[start:end])
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
