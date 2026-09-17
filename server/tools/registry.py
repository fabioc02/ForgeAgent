from server.tools.bash import bash
from server.tools.filesystem import read_file, write_file, list_dir
from server.tools.memory import memory_save, memory_load, memory_list
from server.tools.projects import create_project
from server.tools.python_exec import python_exec

def get_all_tools():
    return {
        "bash": bash,
        "read_file": read_file,
        "write_file": write_file,
        "list_dir": list_dir,
        "memory_save": memory_save,
        "memory_load": memory_load,
        "memory_list": memory_list,
        "create_project": create_project,
        "python_exec": python_exec,
    }

def get_tools_info():
    return [
        {"name": "bash", "description": "Executa comando bash", "args": '{"command": "ls -la"}'},
        {"name": "read_file", "description": "Le arquivo", "args": '{"path": "caminho"}'},
        {"name": "write_file", "description": "Escreve arquivo", "args": '{"path": "caminho", "content": "texto"}'},
        {"name": "list_dir", "description": "Lista diretorio", "args": '{"path": "."}'},
        {"name": "memory_save", "description": "Salva na memoria", "args": '{"key": "chave", "value": "valor"}'},
        {"name": "memory_load", "description": "Carrega da memoria", "args": '{"key": "chave"}'},
        {"name": "memory_list", "description": "Lista chaves", "args": "{}"},
        {"name": "create_project", "description": "Cria projeto", "args": '{"name": "nome", "language": "cpp"}'},
        {"name": "python_exec", "description": "Executa Python", "args": '{"code": "print(1)"}'},
    ]
