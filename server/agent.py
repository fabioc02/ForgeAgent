import json
import re
import time
import uuid
from typing import List, Dict, Any, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, um assistente de IA especializado em desenvolvimento de software multi-plataforma e engenharia reversa.

Voce tem acesso a ferramentas. QUANDO PRECISAR USAR UMA FERRAMENTA, responda APENAS com o bloco JSON abaixo, sem nenhum texto adicional:

[tool]
{"action": "nome_da_ferramenta", "args": {"parametro": "valor"}}
[/tool]

EXEMPLOS DE USO:

Para listar arquivos:
[tool]
{"action": "list_directory", "args": {"path": "."}}
[/tool]

Para ler um arquivo:
[tool]
{"action": "read_file", "args": {"path": "exemplo.py"}}
[/tool]

Para escrever um arquivo:
[tool]
{"action": "write_file", "args": {"path": "exemplo.py", "content": "print('ola')"}}
[/tool]

Para executar comando no terminal:
[tool]
{"action": "terminal", "args": {"command": "ls -la"}}
[/tool]

Para criar projeto:
[tool]
{"action": "create_project", "args": {"name": "meu_projeto", "language": "cpp"}}
[/tool]

Para salvar na memoria:
[tool]
{"action": "memory_save", "args": {"key": "chave", "value": "valor"}}
[/tool]

Para analisar binario (engenharia reversa):
[tool]
{"action": "analyze_binary", "args": {"path": "arquivo.bin"}}
[/tool]

Para dump hexadecimal:
[tool]
{"action": "hexdump", "args": {"path": "arquivo.bin", "offset": 0, "length": 512}}
[/tool]

Para extrair strings de binario:
[tool]
{"action": "extract_strings", "args": {"path": "arquivo.bin"}}
[/tool]

Para buscar assinatura em binario:
[tool]
{"action": "search_signature", "args": {"path": "arquivo.bin", "signature": "CASM"}}
[/tool]

REGRAS IMPORTANTISSIMAS:
1. Se a tarefa REQUER criar arquivos, executar comandos, ler arquivos, OU qualquer acao pratica, VOCE DEVE USAR as ferramentas. Nao apenas descreva o que faria - FACAA usando as ferramentas.
2. Use UMA ferramenta por vez. Espere o resultado antes de usar a proxima.
3. Apos receber o resultado da ferramenta, continue o trabalho ou responda ao usuario.
4. Quando terminar todas as acoes, responda normalmente ao usuario (sem bloco tool).
5. Para tarefas de engenharia reversa, use as ferramentas especializadas: hexdump, analyze_binary, find_patterns, extract_strings, compare_files, entropy_analysis, parse_struct, search_signature.

Ferramentas disponiveis:
- terminal, read_file, write_file, append_file, list_directory, file_info, delete_file
- memory_save, memory_load, memory_list, memory_delete
- compile_cpp, compile_java, run_executable, create_project
- git_status, git_commit, git_log, git_push
- hexdump, analyze_binary, find_patterns, extract_strings, compare_files, entropy_analysis, parse_struct, search_signature"""


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
        pattern = r'\[tool\]\s*\n(.*?)\n\[/tool\]'
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
                
                clean_response = re.sub(r'\[tool\]\s*\n.*?\n\[/tool\]', '', response, flags=re.DOTALL).strip()
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
                    "content": "Resultado da ferramenta " + action + ":\n" + result + "\n\nContinue ou responda ao usuario."
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
