import json
import re
import time
import uuid
from typing import List, Dict, Any, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, um AGENTE AUTONOMO que EXECUTA tarefas de desenvolvimento de software.

FORMATO DE FERRAMENTA (OBRIGATORIO):
[tool]{"action": "nome", "args": {"param": "valor"}}[/tool]

FLUXO OBRIGATORIO - VOCE DEVE COMPLETAR TODAS AS ETAPAS:
1. create_project(name, language)
2. write_file(path, content_COMPLETO)
3. compile_cpp OU compile_java OU terminal("g++ ...")
4. SE DER ERRO NA COMPILACAO: read_file -> corrigir codigo -> write_file -> RECOMPILAR
5. run_executable(path, args="valores_teste")
6. memory_save(key="projeto_X", value="descricao")
7. Responder ao usuario com resumo FINAL

REGRAS ABSOLUTAS:
- NUNCA pare no meio do fluxo. Complete TODAS as 7 etapas.
- Escreva codigo COMPLETO e funcional. Nunca esqueletos.
- Se compilacao falhar, CORRIJA e RECOMPILAR. Repita ate funcionar.
- SEMPRE teste o executavel com valores reais.
- SEMPRE salve na memoria ao concluir.
- Use UMA ferramenta por vez. Aguarde o resultado.

EXEMPLO DE FLUXO COMPLETO:
Usuario: "crie calculadora C++"
Agente:
[tool]{"action": "create_project", "args": {"name": "calc", "language": "cpp"}}[/tool]
[tool]{"action": "write_file", "args": {"path": "Drive/projects/calc/main.cpp", "content": "#include <iostream>\\nint main(){...}"}}[/tool]
[tool]{"action": "compile_cpp", "args": {"source_path": "Drive/projects/calc/main.cpp", "output_path": "Drive/projects/calc/calc"}}[/tool]
[tool]{"action": "run_executable", "args": {"path": "Drive/projects/calc/calc", "args": "10 + 5"}}[/tool]
[tool]{"action": "memory_save", "args": {"key": "projeto_calc", "value": "Calculadora C++ compilada e testada"}}[/tool]
"Calculadora criada, compilada, testada e salva com sucesso!"

FERRAMENTAS DISPONIVEIS:
- terminal: Executa comandos bash. args: {"command": "ls -la"}
- read_file: Le arquivo. args: {"path": "caminho"}
- write_file: Escreve arquivo COMPLETO. args: {"path": "caminho", "content": "conteudo"}
- append_file: Adiciona ao final. args: {"path": "caminho", "content": "texto"}
- list_directory: Lista arquivos. args: {"path": "."}
- file_info: Info do arquivo. args: {"path": "caminho"}
- delete_file: Deleta arquivo/dir. args: {"path": "caminho"}
- memory_save: Salva na memoria. args: {"key": "chave", "value": "valor"}
- memory_load: Carrega da memoria. args: {"key": "chave"}
- memory_list: Lista chaves. args: {}
- memory_delete: Deleta da memoria. args: {"key": "chave"}
- compile_cpp: Compila C/C++. args: {"source_path": "main.cpp", "output_path": "main"}
- compile_java: Compila Java. args: {"source_path": "Main.java"}
- run_executable: Executa binario. args: {"path": "./app", "args": "argumentos", "timeout": 30}
- create_project: Cria projeto. args: {"name": "nome", "language": "cpp|java|python|android"}
- git_status, git_commit, git_log, git_push, git_clone: Git
- hexdump, analyze_binary, find_patterns, extract_strings, compare_files, entropy_analysis, parse_struct, search_signature: Engenharia reversa"""


class Agent:
    def __init__(self, llm_provider, tools: Dict[str, Callable] = None):
        self.llm = llm_provider
        self.tools = tools or {}
        self.sessions: Dict[str, Dict] = {}
        self.max_iterations = 20  # Aumentado de 15 para 20

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
        # Formato inline: [tool]{...}[/tool]
        pattern_inline = r'\[tool\]\s*(\{.*?\})\s*\[/tool\]'
        match = re.search(pattern_inline, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Formato multi-linha
        pattern_multiline = r'\[tool\]\s*\n(.*?)\n\s*\[/tool\]'
        match = re.search(pattern_multiline, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # JSON puro
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
        consecutive_empty = 0
        
        for iteration in range(self.max_iterations):
            if session["status"] == "cancelled":
                return "Sessao cancelada"
            
            print(f"[Agent] Iteracao {iteration + 1}/{self.max_iterations}", flush=True)
            
            try:
                # AUMENTADO: max_tokens de 2048 para 4096
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
                consecutive_empty = 0
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
                
                # GATILHO: Forçar continuidade com instrução explícita
                session["messages"].append({
                    "role": "user",
                    "content": f"Resultado de {action}: {result}\n\nCONTINUE O FLUXO. Proxima etapa obrigatoria."
                })
            else:
                # Verificar se a resposta está vazia ou muito curta
                if len(response.strip()) < 50:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        # Forçar resposta final
                        final_response = "Tarefa concluída. Executei " + str(tool_calls_count) + " ferramentas."
                        break
                else:
                    consecutive_empty = 0
                
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
