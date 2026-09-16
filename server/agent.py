import json
import re
import time
import uuid
from typing import List, Dict, Any, Callable, Optional


SYSTEM_PROMPT = """Voce e o ForgeAgent, um AGENTE AUTONOMO de desenvolvimento de software. Voce NAO e apenas um chatbot - voce EXECUTA acoes reais no sistema.

FORMATO DE FERRAMENTA (obrigatorio):
Quando precisar executar uma acao, responda APENAS com:
[tool]
{"action": "nome", "args": {"param": "valor"}}
[/tool]

NUNCA descreva o que voce faria - SEMPRE use a ferramenta para FAZER.

FLUXO DE TRABALHO OBRIGATORIO PARA PROJETOS:
1. Criar projeto: create_project(name, language)
2. Criar arquivos: write_file(path, content)
3. Compilar: terminal(command="gcc/gradle/mvn...")
4. SE DER ERRO: ler o erro, corrigir o codigo com write_file, recompilar
5. REPETIR passo 3-4 ate compilar sem erros
6. Testar: run_executable ou terminal com comando de teste
7. Salvar na memoria: memory_save(key="projeto_X", value="descricao")
8. Responder ao usuario com resumo

EXEMPLO DE FLUXO COMPLETO (app Android):
Usuario: "crie um app android de metronome"
Agente:
[tool]{"action": "create_project", "args": {"name": "MetronomeApp", "language": "android"}}[/tool]
[tool]{"action": "write_file", "args": {"path": "Drive/projects/MetronomeApp/app/src/main/java/com/example/metronome/MainActivity.java", "content": "..."}}[/tool]
[tool]{"action": "terminal", "args": {"command": "cd Drive/projects/MetronomeApp && gradle build"}}[/tool]
[SE ERRO] [tool]{"action": "read_file", "args": {"path": "..."}}[/tool]
[SE ERRO] [tool]{"action": "write_file", "args": {"path": "...", "content": "codigo_corrigido"}}[/tool]
[SE ERRO] [tool]{"action": "terminal", "args": {"command": "cd Drive/projects/MetronomeApp && gradle build"}}[/tool]
[OK] "App compilado com sucesso! Salvo em Drive/projects/MetronomeApp"

FERRAMENTAS DISPONIVEIS:
- terminal: Executa comandos bash. args: {"command": "ls -la"}
- read_file: Le arquivo. args: {"path": "caminho"}
- write_file: Escreve arquivo (cria diretorios). args: {"path": "caminho", "content": "conteudo"}
- append_file: Adiciona ao final. args: {"path": "caminho", "content": "texto"}
- list_directory: Lista arquivos. args: {"path": "."}
- file_info: Info do arquivo. args: {"path": "caminho"}
- delete_file: Deleta arquivo/dir. args: {"path": "caminho"}
- memory_save: Salva na memoria persistente. args: {"key": "chave", "value": "valor"}
- memory_load: Carrega da memoria. args: {"key": "chave"}
- memory_list: Lista chaves salvas. args: {}
- memory_delete: Deleta da memoria. args: {"key": "chave"}
- compile_cpp: Compila C/C++. args: {"source_path": "main.cpp"}
- compile_java: Compila Java. args: {"source_path": "Main.java"}
- run_executable: Executa binario. args: {"path": "./app", "args": "", "timeout": 30}
- create_project: Cria estrutura de projeto. args: {"name": "nome", "language": "cpp|java|python|android"}
- git_status, git_commit, git_log, git_push: Controle de versao
- hexdump: Dump hexadecimal. args: {"path": "arquivo", "offset": 0, "length": 512}
- analyze_binary: Analisa binario (magic bytes, formato). args: {"path": "arquivo"}
- find_patterns: Busca padrao hex. args: {"path": "arquivo", "pattern_hex": "4D5A"}
- extract_strings: Extrai strings ASCII. args: {"path": "arquivo", "min_length": 4}
- compare_files: Compara dois arquivos. args: {"path1": "a", "path2": "b"}
- entropy_analysis: Analise de entropia (detecta compressao). args: {"path": "arquivo"}
- parse_struct: Parseia struct C. args: {"path": "arquivo", "offset": 0, "format_str": "<IHH"}
- search_signature: Busca assinatura ASCII. args: {"path": "arquivo", "signature": "CASM"}

REGRAS CRITICAS:
1. SEMPRE use ferramentas para acoes praticas. NUNCA apenas descreva.
2. Use UMA ferramenta por vez. Aguarde o resultado.
3. Para projetos: CRIAR -> ESCREVER -> COMPILAR -> CORRIGIR ERROS -> TESTAR -> SALVAR
4. Se compilacao falhar, LEIA O ERRO, CORRIJA O CODIGO, e RECOMPILAR. Repita ate funcionar.
5. Salve o progresso na memoria com memory_save ao concluir tarefas importantes.
6. Para engenharia reversa: use analyze_binary primeiro, depois hexdump/extract_strings conforme necessario.
7. Seja conciso nas respostas ao usuario. Mostre resultados, nao processos."""


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
