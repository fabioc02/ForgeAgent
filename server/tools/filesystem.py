import os

def read_file(path):
    if not os.path.isabs(path):
        path = os.path.join("/content/ForgeAgent", path)
    if not os.path.exists(path):
        return f"Erro: arquivo nao existe: {path}"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler: {str(e)}"

def write_file(path, content):
    if not os.path.isabs(path):
        path = os.path.join("/content/ForgeAgent", path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        size = os.path.getsize(path)
        return f"OK: arquivo escrito ({size} bytes) em {path}"
    except Exception as e:
        return f"Erro ao escrever: {str(e)}"

def list_dir(path="."):
    if not os.path.isabs(path):
        path = os.path.join("/content/ForgeAgent", path)
    if not os.path.exists(path):
        return f"Erro: diretorio nao existe: {path}"
    try:
        items = []
        for item in sorted(os.listdir(path)):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                items.append(f"[DIR]  {item}")
            else:
                size = os.path.getsize(full_path)
                items.append(f"[FILE] {item} ({size} bytes)")
        if items:
            return f"Conteudo de {path}:\n" + "\n".join(items)
        else:
            return f"Diretorio vazio: {path}"
    except Exception as e:
        return f"Erro: {str(e)}"
