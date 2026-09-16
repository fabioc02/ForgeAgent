import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.tools.terminal import terminal
from server.tools.filesystem import (
    read_file, write_file, append_file, list_directory, file_info, delete_file
)
from server.tools.memory import memory_save, memory_load, memory_list, memory_delete
from server.tools.code_executor import compile_cpp, compile_java, run_executable, create_project
from server.tools.git import git_status, git_clone, git_commit, git_log, git_push
from server.tools.reverse_engineering import (
    hexdump, analyze_binary, find_patterns, extract_strings,
    compare_files, entropy_analysis, parse_struct, search_signature
)


def get_all_tools() -> dict:
    """Retorna todas as ferramentas disponiveis para o agente."""
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
        "git_status": git_status,
        "git_clone": git_clone,
        "git_commit": git_commit,
        "git_log": git_log,
        "git_push": git_push,
        "hexdump": hexdump,
        "analyze_binary": analyze_binary,
        "find_patterns": find_patterns,
        "extract_strings": extract_strings,
        "compare_files": compare_files,
        "entropy_analysis": entropy_analysis,
        "parse_struct": parse_struct,
        "search_signature": search_signature,
    }


def get_tools_info() -> list:
    """Retorna lista de ferramentas com descricao para o system prompt."""
    return [
        {"name": "terminal", "description": "Executa comandos no terminal", "args": "command, cwd, timeout"},
        {"name": "read_file", "description": "Le conteudo de arquivo", "args": "path"},
        {"name": "write_file", "description": "Escreve em arquivo", "args": "path, content"},
        {"name": "append_file", "description": "Adiciona ao final de arquivo", "args": "path, content"},
        {"name": "list_directory", "description": "Lista arquivos/dirs", "args": "path"},
        {"name": "file_info", "description": "Info sobre arquivo", "args": "path"},
        {"name": "delete_file", "description": "Deleta arquivo/dir", "args": "path"},
        {"name": "memory_save", "description": "Salva na memoria persistente", "args": "key, value"},
        {"name": "memory_load", "description": "Carrega da memoria", "args": "key"},
        {"name": "memory_list", "description": "Lista chaves da memoria", "args": ""},
        {"name": "memory_delete", "description": "Deleta da memoria", "args": "key"},
        {"name": "compile_cpp", "description": "Compila C/C++", "args": "source_path, output_path, flags"},
        {"name": "compile_java", "description": "Compila Java", "args": "source_path, output_dir"},
        {"name": "run_executable", "description": "Executa binario", "args": "path, args, timeout"},
        {"name": "create_project", "description": "Cria projeto (cpp/java/python/android)", "args": "name, language, base_dir"},
        {"name": "git_clone", "description": "Clona repositorio GitHub", "args": "url, dest_path"},
        {"name": "git_status", "description": "Status git", "args": "repo_path"},
        {"name": "git_commit", "description": "Commit git", "args": "repo_path, message"},
        {"name": "git_log", "description": "Log git", "args": "repo_path, n"},
        {"name": "git_push", "description": "Push git", "args": "repo_path, remote, branch"},
        {"name": "hexdump", "description": "Dump hexadecimal de arquivo", "args": "path, offset, length"},
        {"name": "analyze_binary", "description": "Analisa estrutura binaria (magic bytes, formato)", "args": "path"},
        {"name": "find_patterns", "description": "Busca padrao hex em arquivo", "args": "path, pattern_hex, max_results"},
        {"name": "extract_strings", "description": "Extrai strings ASCII de binario", "args": "path, min_length, max_results"},
        {"name": "compare_files", "description": "Compara dois arquivos byte-a-byte", "args": "path1, path2, max_diffs"},
        {"name": "entropy_analysis", "description": "Analise de entropia (detecta compressao/criptografia)", "args": "path, block_size"},
        {"name": "parse_struct", "description": "Parseia estrutura C em binario (format tipo '<IHH')", "args": "path, offset, format_str"},
        {"name": "search_signature", "description": "Busca assinatura ASCII (CASM, CTB, NTT, etc)", "args": "path, signature"},
    ]
