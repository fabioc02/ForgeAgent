import json
import re
import time
import uuid
from typing import List, Dict, Any, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, um assistente de IA especializado em desenvolvimento de software multi-plataforma.

Voce pode programar em:
- C/C++ (GCC, Clang, CMake, Makefiles)
- Java (Maven, Gradle, aplicacoes desktop)
- Android (Gradle, Android SDK, Kotlin, Java)
- Linux (Bash, Make, systemd, daemons)
- Windows (PowerShell, batch, aplicacoes nativas)
- Python, Node.js, e mais

Voce tem acesso a ferramentas. Para usar uma ferramenta, responda com um bloco JSON:

[tool]
{
  "action": "nome_da_ferramenta",
  "args": { "parametro": "valor" }
}
[/tool]

Ferramentas disponiveis:
- terminal: Executa comandos no terminal. args: {"command": "ls -la"}
- read_file: Le um arquivo. args: {"path": "caminho/do/arquivo"}
- write_file: Escreve um arquivo. args: {"path": "caminho", "content": "conteudo"}
- list_directory: Lista arquivos. args: {"path": "."}
- create_project: Cria um novo projeto. args: {"name": "nome", "language": "cpp"}
- memory_save: Salva na memoria. args: {"key": "chave", "value": "valor"}
- memory_load: Carrega da memoria. args: {"key": "chave"}

Quando terminar, responda normalmente sem bloco tool.

Regras:
1. Pense passo a passo antes de agir
2. Use uma ferramenta por vez
3. Verifique o resultado antes de prosseguir
4. Seja conciso e direto
5. Sempre use a ferramenta terminal para compilar e testar codigo"""


class Agent:
    def __init__(self, llm_provider, tools: Dict[str, Callable] = None):
        self.llm = llm_provider
        self.tools = tools or {}
        self.sessions: Dict[str, Dict] = {}
        self.max_iterations = 10

    def create_session(self, project_id: str = None) -> str:
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = {
            "id": session_id,
            "project_id": project_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT}
            ],
            "status": "active",
            "created_at": time.time()
        }
        print("[Agent] Sessao criada: " + session_id)
        return session_id

    def cancel_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "cancelled"
            print("[Agent] Sessao cancelada: " + session_id)

    def _parse_tool_call(self, text: str) -> Optional[Dict]:
        pattern = r'\[tool\]\s*
(.*?)
\[/tool\]'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
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
            return "Sessao nao encontrada: " + session_id
        
        session = self.sessions[session_id]
        if session["status"] != "active":
            return "Sessao nao esta ativa"
        
        session["messages"].append({
            "role": "user",
            "content": user_message
        })
        
        if event_callback:
            event_callback({"type": "user_message", "content": user_message})
        
        final_response = ""
        
        for iteration in range(self.max_iterations):
            if session["status"] == "cancelled":
                return "Sessao cancelada pelo usuario"
            
            print("[Agent] Iteracao " + str(iteration + 1) + "/" + str(self.max_iterations))
            
            try:
                response = self.llm.generate(
                    messages=session["messages"],
                    max_tokens=2048,
                    temperature=0.1
                )
            except Exception as e:
                error_msg = "Erro ao gerar resposta: " + str(e)
                print("[Agent] " + error_msg)
                if event_callback:
                    event_callback({"type": "agent_message", "content": error_msg})
                return error_msg
            
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                action = tool_call.get("action", "unknown")
                args = tool_call.get("args", {})
                print("[Agent] Tool call: " + action + " " + str(args))
                
                if event_callback:
                    event_callback({
                        "type": "tool_call",
                        "tool": action,
                        "args": args
                    })
                
                clean_response = re.sub(r'\[tool\]\s*
.*?
\[/tool\]', '', response, flags=re.DOTALL).strip()
                if clean_response:
                    session["messages"].append({
                        "role": "assistant",
                        "content": clean_response
                    })
                
                result = self._execute_tool(tool_call)
                print("[Agent] Tool result: " + result[:200])
                
                if event_callback:
                    event_callback({
                        "type": "tool_result",
                        "tool": action,
                        "result": result
                    })
                
                session["messages"].append({
                    "role": "user",
                    "content": "Resultado da ferramenta " + action + ":
" + result + "

Continue ou responda ao usuario."
                })
            else:
                final_response = response.strip()
                session["messages"].append({
                    "role": "assistant",
                    "content": final_response
                })
                
                if event_callback:
                    event_callback({
                        "type": "agent_message",
                        "content": final_response
                    })
                
                break
        
        if not final_response:
            final_response = "Limite de iteracoes atingido. Tente simplificar o pedido."
            if event_callback:
                event_callback({
                    "type": "agent_message",
                    "content": final_response
                })
        
        if event_callback:
            event_callback({"type": "done"})
        
        return final_response

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> List[Dict]:
        return list(self.sessions.values())
