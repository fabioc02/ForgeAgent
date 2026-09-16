import json
import re
import time
import uuid
from typing import List, Dict, Any, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, um AGENTE AUTONOMO de desenvolvimento de software.

FORMATO DE FERRAMENTA (OBRIGATORIO):
Para executar uma acao, responda APENAS com:
[tool]{"action": "nome", "args": {"param": "valor"}}[/tool]

OU (formato multi-linha tambem aceito):
[tool]
{"action": "nome", "args": {"param": "valor"}}
[/tool]

FLUXO OBRIGATORIO PARA PROJETOS:
1. create_project(name, language)
2. write_file(path, content_completo) - NUNCA esqueletos
3. compile_cpp/compile_java/terminal - COMPILAR
4. SE DER ERRO: read_file -> corrigir -> write_file -> RECOMPILAR (repita)
5. run_executable - TESTAR com valores reais
6. memory_save(key, value) - SALVAR
7. Responder ao usuario

PARA APPS LINUX:
- Usar GTK ou Qt para GUI
- Criar Makefile
- Compilar: g++ main.cpp -o app `pkg-config --cflags --libs gtk+-3.0`

REGRAS CRITICAS:
1. SEMPRE complete o fluxo inteiro. NUNCA pare no meio.
2. Escreva codigo COMPLETO, nunca "insira logica aqui".
3. Se compilacao falhar, LEIA O ERRO, CORRIJA, RECOMPILAR.
4. Salve na memoria ao concluir.
5. Use UMA ferramenta por vez."""


class Agent:
    def __init__(self, llm_provider, tools: Dict[str, Callable] = None):
        self.llm = llm_provider
        self.tools = tools or {}
        self.sessions: Dict[str, Dict] = {}
        self.max_iterations = 15

    def create_session(self, project_id: str = None) -> str:
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = {
            "id": session_id,
            "project_id": project_id,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "status": "active",
            "created_at": time.time()
        }
        print("[Agent] Sessao criada: " + session_id, flush=True)
        return session_id

    def cancel_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "cancelled"

    def _parse_tool_call(self, text: str) -> Optional[Dict]:
        """Parse tool call - aceita formato inline e multi-linha"""
        # Tentar formato inline: [tool]{...}[/tool]
        pattern_inline = r'\[tool\]\s*(\{.*?\})\s*\[/tool\]'
        match = re.search(pattern_inline, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Tentar formato multi-linha
        pattern_multiline = r'\[tool\]\s*\n(.*?)\n\s*\[/tool\]'
        match = re.search(pattern_multiline, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Tentar JSON puro
        try:
            data = json.loads(text.strip())
            if "action" in data:
                return data
        except json.JSONDecodeError:
            pass
        
        return None

    def _execute_tool(self, tool_call: Dict) -> str:
        action = tool_call.get("action", "")
        args = tool_call.get("args", {})
        
        if action in self.tools:
            try:
                result = self.tools[action](**args)
                return str(result)
            except Exception as e:
                return "Erro na ferramenta " + action + ": " + str(e)
        else:
            return "Ferramenta desconhecida: " + action

    def run(self, session_id: str, user_message: str, event_callback: Callable = None) -> str:
        if session_id not in self.sessions:
            return "Sessao nao encontrada"
        
        session = self.sessions[session_id]
        if session["status"] != "active":
            return "Sessao nao ativa"
        
        session["messages"].append({"role": "user", "content": user_message})
        
        if event_callback:
            event_callback({"type": "user_message", "content": user_message})
        
        final_response = ""
        tool_calls_count = 0
        
        for iteration in range(self.max_iterations):
            if session["status"] == "cancelled":
                return "Sessao cancelada"
            
            print(f"[Agent] Iteracao {iteration + 1}/{self.max_iterations}", flush=True)
            
            try:
                response = self.llm.generate(
                    messages=session["messages"],
                    max_tokens=2048,
                    temperature=0.1
                )
            except Exception as e:
                error_msg = "Erro ao gerar: " + str(e)
                if event_callback:
                    event_callback({"type": "agent_message", "content": error_msg})
                return error_msg
            
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                tool_calls_count += 1
                action = tool_call.get("action", "unknown")
                args = tool_call.get("args", {})
                print(f"[Agent] Tool call #{tool_calls_count}: {action}", flush=True)
                
                if event_callback:
                    event_callback({"type": "tool_call", "tool": action, "args": args})
                
                # Remover bloco tool da resposta
                clean_response = re.sub(r'\[tool\].*?\[/tool\]', '', response, flags=re.DOTALL).strip()
                if clean_response:
                    session["messages"].append({"role": "assistant", "content": clean_response})
                
                # Executar ferramenta
                result = self._execute_tool(tool_call)
                print(f"[Agent] Result: {result[:200]}", flush=True)
                
                if event_callback:
                    event_callback({"type": "tool_result", "tool": action, "result": result})
                
                # Adicionar resultado ao contexto
                session["messages"].append({
                    "role": "user",
                    "content": f"Resultado de {action}: {result}\n\nContinue ou responda."
                })
            else:
                # Sem tool call = resposta final
                final_response = response.strip()
                session["messages"].append({"role": "assistant", "content": final_response})
                
                if event_callback:
                    event_callback({"type": "agent_message", "content": final_response})
                
                break
        
        if not final_response:
            final_response = f"Limite de iteracoes atingido. Executei {tool_calls_count} ferramentas."
            if event_callback:
                event_callback({"type": "agent_message", "content": final_response})
        
        if event_callback:
            event_callback({"type": "done"})
        
        return final_response

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> List[Dict]:
        return list(self.sessions.values())
