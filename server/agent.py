import json
import re
import time
import uuid
from typing import List, Dict, Any, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, AGENTE AUTONOMO de desenvolvimento.

FORMATO DE FERRAMENTA (OBRIGATORIO):
[tool]{"action": "nome", "args": {"param": "valor"}}[/tool]

REGRAS CRITICAS:
1. NUNCA use ```cpp ou ``` no content do write_file. Escreva APENAS o código puro.
2. Escreva código COMPLETO e funcional, nunca esqueletos.
3. Complete TODAS as etapas: criar -> escrever -> compilar -> testar -> salvar.
4. Use os nomes EXATOS dos parâmetros das ferramentas (veja abaixo).
5. Se compilacao falhar, leia o erro, corrija o codigo, recompile.

NOMES EXATOS DE PARAMETROS:
- write_file: {"path": "caminho", "content": "codigo_puro_sem_markdown"}
- compile_cpp: {"source_path": "main.cpp", "output_path": "app"}
- compile_java: {"source_path": "Main.java"}
- run_executable: {"path": "./app", "args": "argumentos", "timeout": 30}
- terminal: {"command": "ls -la"}
- read_file: {"path": "caminho"}
- memory_save: {"key": "chave", "value": "valor"}
- create_project: {"name": "nome", "language": "cpp"}

EXEMPLO CORRETO:
[tool]{"action": "write_file", "args": {"path": "main.cpp", "content": "#include <iostream>\nint main(){ std::cout << \"Hello\"; return 0; }"}}[/tool]

EXEMPLO ERRADO (NUNCA FAÇA):
[tool]{"action": "write_file", "args": {"path": "main.cpp", "content": "```cpp\n#include <iostream>\n```"}}[/tool]

FLUXO OBRIGATORIO:
1. create_project(name, language)
2. write_file(path, content_puro)
3. compile_cpp(source_path, output_path)
4. SE ERRO: read_file -> corrigir -> write_file -> compile_cpp (repita)
5. run_executable(path, args)
6. memory_save(key, value)
7. Resposta final

FERRAMENTAS DISPONIVEIS:
terminal, read_file, write_file, append_file, list_directory, file_info, delete_file
memory_save, memory_load, memory_list, memory_delete
compile_cpp, compile_java, run_executable, create_project
git_status, git_commit, git_log, git_push, git_clone
hexdump, analyze_binary, find_patterns, extract_strings, compare_files, entropy_analysis, parse_struct, search_signature"""


class Agent:
    def __init__(self, llm_provider, tools: Dict[str, Callable] = None):
        self.llm = llm_provider
        self.tools = tools or {}
        self.sessions: Dict[str, Dict] = {}
        self.max_iterations = 25

    def create_session(self, project_id: str = None) -> str:
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = {
            "id": session_id,
            "project_id": project_id,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "status": "active",
            "created_at": time.time(),
            "last_tool": None,
            "error_count": 0
        }
        print("[Agent] Sessao criada: " + session_id, flush=True)
        return session_id

    def cancel_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "cancelled"

    def _parse_tool_call(self, text: str) -> Optional[Dict]:
        pattern_inline = r'\[tool\]\s*(\{.*?\})\s*\[/tool\]'
        match = re.search(pattern_inline, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        pattern_multiline = r'\[tool\]\s*\n(.*?)\n\s*\[/tool\]'
        match = re.search(pattern_multiline, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        return None

    def _clean_markdown_fences(self, content: str) -> str:
        content = re.sub(r'^```[a-zA-Z]*\n', '', content)
        content = re.sub(r'\n```$', '', content)
        content = content.replace('```', '')
        return content.strip()

    def _execute_tool(self, tool_call: Dict) -> str:
        action = tool_call.get("action", "")
        args = tool_call.get("args", {})
        
        if action == "write_file" and "content" in args:
            args["content"] = self._clean_markdown_fences(args["content"])
        
        if action == "compile_cpp":
            if "path" in args and "source_path" not in args:
                args["source_path"] = args.pop("path")
        
        if action in self.tools:
            try:
                result = self.tools[action](**args)
                return str(result)
            except TypeError as e:
                return f"Erro de parâmetro: {str(e)}. Parametros: {list(self.tools[action].__code__.co_varnames)}"
            except Exception as e:
                return "Erro: " + str(e)
        else:
            return f"Ferramenta desconhecida: {action}. Disponíveis: {list(self.tools.keys())}"

    def _get_next_required_tool(self, last_tool: str) -> str:
        workflow = {
            "create_project": "write_file",
            "write_file": "compile_cpp",
            "compile_cpp": "run_executable",
            "compile_java": "run_executable",
            "terminal": "run_executable",
            "run_executable": "memory_save",
            "memory_save": "DONE"
        }
        return workflow.get(last_tool, "DONE")

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
                    max_tokens=4096,
                    temperature=0.2
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
                session["last_tool"] = action
                print(f"[Agent] Tool #{tool_calls_count}: {action}", flush=True)
                
                if event_callback:
                    event_callback({"type": "tool_call", "tool": action, "args": args})
                
                clean_response = re.sub(r'\[tool\].*?\[/tool\]', '', response, flags=re.DOTALL).strip()
                if clean_response:
                    session["messages"].append({"role": "assistant", "content": clean_response})
                
                result = self._execute_tool(tool_call)
                print(f"[Agent] Result: {result[:200]}", flush=True)
                
                if event_callback:
                    event_callback({"type": "tool_result", "tool": action, "result": result})
                
                if "Erro" in result or "erro" in result.lower():
                    session["error_count"] = session.get("error_count", 0) + 1
                    if session["error_count"] > 5:
                        final_response = f"Muitos erros ({session['error_count']}). Último: {result}"
                        break
                    
                    session["messages"].append({
                        "role": "user",
                        "content": f"ERRO: {result}\n\nUse read_file para ver o código, corrija com write_file (SEM markdown fences), e recompile."
                    })
                else:
                    session["error_count"] = 0
                    next_tool = self._get_next_required_tool(action)
                    if next_tool != "DONE":
                        session["messages"].append({
                            "role": "user",
                            "content": f"Resultado: {result}\n\nPROXIMA ETAPA: {next_tool}. Execute agora."
                        })
                    else:
                        session["messages"].append({
                            "role": "user",
                            "content": f"Resultado: {result}\n\nFluxo completo. Responda ao usuario."
                        })
            else:
                last_tool = session.get("last_tool")
                next_required = self._get_next_required_tool(last_tool) if last_tool else "write_file"
                
                if next_required == "DONE":
                    final_response = response.strip()
                else:
                    force_msg = f"PAROU PREMATURAMENTE. Proxima etapa: {next_required}\nExecute [tool]{{\"action\": \"{next_required}\", ...}}[/tool] AGORA.\nLembre: NUNCA use ``` no content do write_file."
                    session["messages"].append({"role": "user", "content": force_msg})
                    print(f"[Agent] Forçando: {next_required}", flush=True)
                    continue
                
                session["messages"].append({"role": "assistant", "content": final_response})
                if event_callback:
                    event_callback({"type": "agent_message", "content": final_response})
                break
        
        if not final_response:
            final_response = f"Concluído. {tool_calls_count} ferramentas executadas."
            if event_callback:
                event_callback({"type": "agent_message", "content": final_response})
        
        if event_callback:
            event_callback({"type": "done"})
        
        return final_response

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> List[Dict]:
        return list(self.sessions.values())
