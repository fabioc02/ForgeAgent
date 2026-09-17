import os
import json

MEMORY_DIR = "/content/ForgeAgent/Drive/memory"

def memory_save(key, value):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    file_path = os.path.join(MEMORY_DIR, f"{key}.json")
    try:
        data = {"key": key, "value": value}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return f"OK: salvo '{key}' em {file_path}"
    except Exception as e:
        return f"Erro ao salvar: {str(e)}"

def memory_load(key):
    file_path = os.path.join(MEMORY_DIR, f"{key}.json")
    if not os.path.exists(file_path):
        return f"Erro: chave '{key}' nao encontrada"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("value", "")
    except Exception as e:
        return f"Erro ao carregar: {str(e)}"

def memory_list():
    os.makedirs(MEMORY_DIR, exist_ok=True)
    try:
        keys = []
        for f in os.listdir(MEMORY_DIR):
            if f.endswith('.json'):
                keys.append(f[:-5])
        if keys:
            return "Chaves salvas:\n" + "\n".join(f"  - {k}" for k in sorted(keys))
        else:
            return "Memoria vazia"
    except Exception as e:
        return f"Erro: {str(e)}"
