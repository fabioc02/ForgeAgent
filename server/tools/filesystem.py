import os
import json
from typing import Optional


def read_file(path: str) -> str:
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return "Erro: arquivo nao existe: " + path
        if not os.path.isfile(path):
            return "Erro: nao e um arquivo: " + path
        
        size = os.path.getsize(path)
        if size > 100000:
            with open(path, "r", errors="ignore") as f:
                content = f.read(100000)
            return content + "\n\n... [truncado, arquivo tem " + str(size) + " bytes]"
        
        with open(path, "r", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return "Erro ao ler arquivo: " + str(e)


def write_file(path: str, content: str) -> str:
    try:
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return "OK: arquivo escrito (" + str(len(content)) + " bytes): " + path
    except Exception as e:
        return "Erro ao escrever arquivo: " + str(e)


def append_file(path: str, content: str) -> str:
    try:
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(content)
        return "OK: conteudo adicionado a " + path
    except Exception as e:
        return "Erro: " + str(e)


def list_directory(path: str = ".") -> str:
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return "Erro: diretorio nao existe: " + path
        
        items = []
        for item in sorted(os.listdir(path)):
            full = os.path.join(path, item)
            if os.path.isdir(full):
                items.append("[DIR]  " + item)
            else:
                size = os.path.getsize(full)
                items.append("[FILE] " + item + " (" + str(size) + " bytes)")
        
        if not items:
            return "Diretorio vazio: " + path
        
        return "Conteudo de " + path + ":\n" + "\n".join(items)
    except Exception as e:
        return "Erro: " + str(e)


def file_info(path: str) -> str:
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return "Erro: nao existe: " + path
        
        stat = os.stat(path)
        info = {
            "path": path,
            "type": "directory" if os.path.isdir(path) else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "permissions": oct(stat.st_mode)[-3:]
        }
        return json.dumps(info, indent=2)
    except Exception as e:
        return "Erro: " + str(e)


def delete_file(path: str) -> str:
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return "Erro: nao existe: " + path
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
            return "OK: diretorio deletado: " + path
        else:
            os.remove(path)
            return "OK: arquivo deletado: " + path
    except Exception as e:
        return "Erro: " + str(e)
