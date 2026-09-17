import os
from typing import List, Dict


def create_project(name: str, language: str = "cpp") -> str:
    """Cria estrutura de projeto"""
    projects_dir = os.path.abspath("Drive/projects")
    project_dir = os.path.join(projects_dir, name)
    
    if os.path.exists(project_dir):
        return f"Erro: projeto ja existe: {project_dir}"
    
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
    
    return f"OK: projeto '{name}' criado em {project_dir} ({language})"


def list_projects() -> str:
    """Lista todos os projetos"""
    projects_dir = os.path.abspath("Drive/projects")
    
    if not os.path.exists(projects_dir):
        return "Nenhum projeto encontrado"
    
    projects = []
    for name in os.listdir(projects_dir):
        project_dir = os.path.join(projects_dir, name)
        if os.path.isdir(project_dir):
            projects.append(name)
    
    if projects:
        return "Projetos: " + ", ".join(projects)
    else:
        return "Nenhum projeto encontrado"


def create_and_write(name: str, language: str, filename: str, content: str) -> str:
    """Cria projeto E escreve arquivo principal em UMA chamada.
    Use esta ferramenta em vez de create_project + write_file separados."""
    projects_dir = os.path.abspath("Drive/projects")
    project_dir = os.path.join(projects_dir, name)
    
    # Criar projeto (se não existir)
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
    
    # Determinar caminho do arquivo
    if "/" in filename:
        file_path = os.path.join(projects_dir, filename)
    else:
        file_path = os.path.join(project_dir, "src", filename)
    
    # Criar diretórios pais se necessário
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Limpar markdown fences do conteúdo
    import re
    content = re.sub(r'^```[a-zA-Z]*\n', '', content)
    content = re.sub(r'\n```$', '', content)
    content = content.replace('```', '')
    
    # Escrever arquivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    file_size = os.path.getsize(file_path)
    return f"OK: projeto '{name}' criado e arquivo '{filename}' escrito ({file_size} bytes) em {file_path}"


def list_project_files(project_name: str) -> str:
    """Lista arquivos de um projeto específico"""
    projects_dir = os.path.abspath("Drive/projects")
    project_dir = os.path.join(projects_dir, project_name)
    
    if not os.path.exists(project_dir):
        return f"Erro: projeto '{project_name}' nao existe"
    
    files = []
    for root, dirs, filenames in os.walk(project_dir):
        for f in filenames:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, projects_dir)
            files.append(rel_path)
    
    if files:
        return f"Arquivos de '{project_name}':\n" + "\n".join(files)
    else:
        return f"Projeto '{project_name}' esta vazio"
