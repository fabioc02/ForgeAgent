import os
import json
from typing import Optional


MEMORY_DIR = os.path.abspath("Drive/memory")


def _ensure_dir():
    os.makedirs(MEMORY_DIR, exist_ok=True)


def memory_save(key: str, value: str) -> str:
    try:
        _ensure_dir()
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        path = os.path.join(MEMORY_DIR, safe_key + ".json")
        data = {"key": key, "value": value}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return "OK: salvo '" + key + "' em " + path
    except Exception as e:
        return "Erro: " + str(e)


def memory_load(key: str) -> str:
    try:
        _ensure_dir()
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        path = os.path.join(MEMORY_DIR, safe_key + ".json")
        if not os.path.exists(path):
            return "Erro: chave nao encontrada: " + key
        with open(path, "r") as f:
            data = json.load(f)
        return data.get("value", "")
    except Exception as e:
        return "Erro: " + str(e)


def memory_list() -> str:
    try:
        _ensure_dir()
        keys = []
        for f in os.listdir(MEMORY_DIR):
            if f.endswith(".json"):
                keys.append(f[:-5])
        if not keys:
            return "Memoria vazia"
        return "Chaves na memoria:\n" + "\n".join("- " + k for k in sorted(keys))
    except Exception as e:
        return "Erro: " + str(e)


def memory_delete(key: str) -> str:
    try:
        _ensure_dir()
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        path = os.path.join(MEMORY_DIR, safe_key + ".json")
        if os.path.exists(path):
            os.remove(path)
            return "OK: chave deletada: " + key
        return "Erro: chave nao existe: " + key
    except Exception as e:
        return "Erro: " + str(e)
