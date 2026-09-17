import json
import re
import time
import uuid
from typing import List, Dict, Any, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, AGENTE AUTONOMO de desenvolvimento.

REGRA DE OURO: USE create_and_write PARA CRIAR PROJETO + ARQUIVO EM UMA CHAMADA!
Nao use create_project seguido de write_file. Use create_and_write.

FORMATO DE FERRAMENTA (OBRIGATORIO):
[tool]{"action": "nome", "args": {"param": "valor"}}[/tool]

FLUXO CORRETO (4 ETAPAS):
1. create_and_write(name, language, filename, content) - cria projeto E arquivo
2. compile_cpp(source_path, output_path) - compila
3. run_executable(path, args) - testa
4. memory_save(key, value) - salva

EXEMPLO COMPLETO:
Usuario: "crie calculadora C++"
Agente:
[tool]{"action": "create_and_write", "args": {"name": "calc", "language": "cpp", "filename": "main.cpp", "content": "#include <iostream>\nint main(){ double a,b; char op; std::cin>>a>>op>>b; if(op=='+') std::cout<<a+b; return 0; }"}}[/tool]
[tool]{"action": "compile_cpp", "args": {"source_path": "Drive/projects/calc/src/main.cpp", "output_path": "Drive/projects/calc/calc"}}[/tool]
[tool]{"action": "run_executable", "args": {"path": "Drive/projects/calc/calc", "args": "", "timeout": 10}}[/tool]
[tool]{"action": "memory_save", "args": {"key": "projeto_calc", "value": "Calculadora C++ compilada"}}[/tool]

SE COMPILACAO FALHAR:
- Leia o erro
- Use write_file para corrigir o codigo (path correto: Drive/projects/NOME/src/main.cpp)
- Recompile com compile_cpp

NUNCA:
- Nao use create_project sozinho (use create_and_write)
- Nao repita a mesma acao mais de 2 vezes
- Nao use ``` no content do write_file
- Nao tente read_file antes de saber que o arquivo existe (use list_project_files primeiro)

FERRAMENTAS DISPONIVEIS:
- create_and_write: CRIA PROJETO + ARQUIVO (USE ESTA!)
- compile_cpp: source_path, output_path
- run_executable: path, args, timeout
- write_file: path, content (para corrigir)
- read_file: path
- list_project_files: project_name (para ver arquivos)
- list_directory: path
- terminal: command
- memory_save: key, value
- memory_load, memory_list, memory_delete
- git_status, git_commit, git_log, git_push, git_clone
- hexdump, analyze_binary, find_patterns, extract_strings, compare_files, entropy_analysis, parse_struct, search_signature"""


class Agent:
    def __init__(self, llm_provider, tools: Dict[str, Callable] = None):
        self.llm = llm_provider
        self.tools = tools or {}
        self.sessions: Dict[str, Dict] = {}
        self.max_iterations = 20

    def create_session(self, project_id: str = None) -> str:
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = {
            "id": session_id,
            "project_id": project_id,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "status": "active",
            "created_at": time.time(),
            "action_history": [],
            "error_count": 0,
            "consecutive_same_action": 0,
            "last_action": None
        }
        print("[Agent] Sessao criada: " + session_id, flush=True)
        return session_id

    def cancel_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "cancelled"

    def _parse_tool_call(self, text: str) -> Optional[Dict]:
        # Formato correto
        pattern1 = r'\[tool\]\s*(\{.*?\})\s*\[/tool\]'
        match = re.search(pattern1, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Formato quebrado (sem [ no fechamento)
        pattern2 = r'\[tool\]\s*(\{.*?\})\s*/tool\]'
        match = re.search(pattern2, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Multi-linha
        pattern3 = r'\[tool\]\s*\n(.*?)\n\s*\[/tool\]'
        match = re.search(pattern3, text, re.DOTALL)
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
                return f"Erro de parâmetro: {str(e)}. Parametros corretos: {list(self.tools[action].__code__.co_varnames)}"
            except Exception as e:
                return "Erro: " + str(e)
        else:
            return f"Ferramenta desconhecida: {action}. Disponiveis: {list(self.tools.keys())}"

    def _detect_loop(self, session: Dict, action: str, args: Dict) -> bool:
        """Detecta se o agente está em loop"""
        action_key = f"{action}:{json.dumps(args, sort_keys=True)}"
        
        # Verifica se é a mesma ação consecutiva
        if session.get("last_action") == action_key:
            session["consecutive_same_action"] = session.get("consecutive_same_action", 0) + 1
        else:
            session["consecutive_same_action"] = 0
            session["last_action"] = action_key
        
        # Se repetiu 2x, é loop
        if session["consecutive_same_action"] >= 2:
            return True
        
        return False

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
                
                # DETECÇÃO DE LOOP
                if self._detect_loop(session, action, args):
                    print(f"[Agent] LOOP DETECTADO em {action}", flush=True)
                    
                    # Forçar mudança de estratégia
                    if action == "create_project":
                        force_msg = "LOOP DETECTADO! Nao use create_project. USE create_and_write com name, language, filename e content."
                    elif action == "read_file":
                        force_msg = "LOOP DETECTADO! Use list_project_files para ver arquivos existentes, ou write_file para criar."
                    else:
                        force_msg = f"LOOP DETECTADO em {action}. Mude de estrategia. Proxima acao esperada: compile_cpp ou run_executable."
                    
                    session["messages"].append({"role": "user", "content": force_msg})
                    session["consecutive_same_action"] = 0
                    continue
                
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
                
                # Detectar erro
                if "Erro" in result or "erro" in result.lower() or "nao existe" in result.lower():
                    session["error_count"] = session.get("error_count", 0) + 1
                    
                    if session["error_count"] > 10:
                        final_response = f"Muitos erros ({session['error_count']}). Último: {result}"
                        break
                    
                    # Estratégia específica por tipo de erro
                    if "ja existe" in result.lower() and action == "create_project":
                        session["messages"].append({
                            "role": "user",
                            "content": f"ERRO: projeto ja existe. NAO repita create_project. USE create_and_write para criar o arquivo dentro do projeto existente, OU use list_project_files para ver o que tem."
                        })
                    elif "nao existe" in result.lower() and action == "read_file":
                        session["messages"].append({
                            "role": "user",
                            "content": f"ERRO: arquivo nao existe. USE write_file para criar o arquivo, ou list_project_files para ver o que existe."
                        })
                    elif "parâmetro" in result.lower():
                        session["messages"].append({
                            "role": "user",
                            "content": f"ERRO DE PARAMETRO: {result}\n\nVerifique os nomes corretos dos parametros."
                        })
                    else:
                        session["messages"].append({
                            "role": "user",
                            "content": f"ERRO: {result}\n\nTente estrategia diferente."
                        })
                else:
                    session["error_count"] = 0
                    
                    # Guiar próximo passo
                    if action == "create_and_write":
                        next_msg = f"Resultado: {result}\n\nPROXIMO: compile_cpp com source_path='Drive/projects/{args.get('name', 'X')}/src/{args.get('filename', 'main.cpp')}' e output_path='Drive/projects/{args.get('name', 'X')}/app'"
                    elif action == "compile_cpp":
                        next_msg = f"Resultado: {result}\n\nPROXIMO: run_executable com path do executavel"
                    elif action == "run_executable":
                        next_msg = f"Resultado: {result}\n\nPROXIMO: memory_save para salvar progresso"
                    elif action == "memory_save":
                        next_msg = f"Resultado: {result}\n\nFluxo completo! Responda ao usuario com resumo."
                    else:
                        next_msg = f"Resultado: {result}\n\nContinue."
                    
                    session["messages"].append({"role": "user", "content": next_msg})
            else:
                # Sem tool call - resposta final
                final_response = response.strip()
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
