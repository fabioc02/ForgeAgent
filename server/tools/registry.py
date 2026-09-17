from server.tools.terminal import terminal
from server.tools.filesystem import read_file, write_file, append_file, list_directory, file_info, delete_file
from server.tools.memory import memory_save, memory_load, memory_list, memory_delete
from server.tools.compile import compile_cpp, compile_java, run_executable
from server.tools.projects import create_project, list_projects, create_and_write, list_project_files
from server.tools.git import git_status, git_commit, git_log, git_push, git_clone
from server.tools.reverse_engineering import hexdump, analyze_binary, find_patterns, extract_strings, compare_files, entropy_analysis, parse_struct, search_signature


def get_all_tools():
    return {
        "terminal": terminal,
        "read_file": read_file,
        "write_file": write_file,
        "append_file": append_file,
        "list_directory": list_directory,
        "file_info": file_info,
        "delete_file": delete_file,
        "memory_save": memory_save,
        "memory_load": memory_load,
        "memory_list": memory_list,
        "memory_delete": memory_delete,
        "compile_cpp": compile_cpp,
        "compile_java": compile_java,
        "run_executable": run_executable,
        "create_project": create_project,
        "list_projects": list_projects,
        "create_and_write": create_and_write,
        "list_project_files": list_project_files,
        "git_status": git_status,
        "git_commit": git_commit,
        "git_log": git_log,
        "git_push": git_push,
        "git_clone": git_clone,
        "hexdump": hexdump,
        "analyze_binary": analyze_binary,
        "find_patterns": find_patterns,
        "extract_strings": extract_strings,
        "compare_files": compare_files,
        "entropy_analysis": entropy_analysis,
        "parse_struct": parse_struct,
        "search_signature": search_signature,
    }


def get_tools_info():
    return [
        {"name": "terminal", "description": "Executa comando bash", "args": '{"command": "ls -la"}'},
        {"name": "read_file", "description": "Le arquivo", "args": '{"path": "caminho"}'},
        {"name": "write_file", "description": "Escreve arquivo", "args": '{"path": "caminho", "content": "texto"}'},
        {"name": "append_file", "description": "Adiciona ao final", "args": '{"path": "caminho", "content": "texto"}'},
        {"name": "list_directory", "description": "Lista arquivos", "args": '{"path": "."}'},
        {"name": "file_info", "description": "Info do arquivo", "args": '{"path": "caminho"}'},
        {"name": "delete_file", "description": "Deleta arquivo", "args": '{"path": "caminho"}'},
        {"name": "memory_save", "description": "Salva na memoria", "args": '{"key": "chave", "value": "valor"}'},
        {"name": "memory_load", "description": "Carrega da memoria", "args": '{"key": "chave"}'},
        {"name": "memory_list", "description": "Lista chaves", "args": "{}"},
        {"name": "memory_delete", "description": "Deleta da memoria", "args": '{"key": "chave"}'},
        {"name": "compile_cpp", "description": "Compila C/C++", "args": '{"source_path": "main.cpp", "output_path": "app"}'},
        {"name": "compile_java", "description": "Compila Java", "args": '{"source_path": "Main.java"}'},
        {"name": "run_executable", "description": "Executa binario", "args": '{"path": "./app", "args": "", "timeout": 30}'},
        {"name": "create_project", "description": "Cria projeto vazio", "args": '{"name": "nome", "language": "cpp"}'},
        {"name": "list_projects", "description": "Lista projetos", "args": "{}"},
        {"name": "create_and_write", "description": "Cria projeto E escreve arquivo principal (USE ESTA!)", "args": '{"name": "nome", "language": "cpp", "filename": "main.cpp", "content": "codigo"}'},
        {"name": "list_project_files", "description": "Lista arquivos de projeto", "args": '{"project_name": "nome"}'},
        {"name": "git_status", "description": "Status git", "args": '{"path": "."}'},
        {"name": "git_commit", "description": "Git commit", "args": '{"message": "msg", "path": "."}'},
        {"name": "git_log", "description": "Git log", "args": '{"path": "."}'},
        {"name": "git_push", "description": "Git push", "args": '{"path": "."}'},
        {"name": "git_clone", "description": "Clona repositorio", "args": '{"url": "https://...", "dest_path": "."}'},
        {"name": "hexdump", "description": "Dump hexadecimal", "args": '{"path": "arquivo", "offset": 0, "length": 512}'},
        {"name": "analyze_binary", "description": "Analisa binario", "args": '{"path": "arquivo"}'},
        {"name": "find_patterns", "description": "Busca padrao hex", "args": '{"path": "arquivo", "pattern_hex": "4D5A"}'},
        {"name": "extract_strings", "description": "Extrai strings", "args": '{"path": "arquivo", "min_length": 4}'},
        {"name": "compare_files", "description": "Compara arquivos", "args": '{"path1": "a", "path2": "b"}'},
        {"name": "entropy_analysis", "description": "Analise de entropia", "args": '{"path": "arquivo"}'},
        {"name": "parse_struct", "description": "Parseia struct C", "args": '{"path": "arquivo", "offset": 0, "format_str": "<IHH"}'},
        {"name": "search_signature", "description": "Busca assinatura", "args": '{"path": "arquivo", "signature": "CASM"}'},
    ]
