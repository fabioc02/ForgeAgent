import os

PROJECTS_DIR = "/content/ForgeAgent/Drive/projects"

def create_project(name, language="cpp"):
    project_dir = os.path.join(PROJECTS_DIR, name)
    if os.path.exists(project_dir):
        return f"Projeto '{name}' ja existe em {project_dir}"
    try:
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
        readme = f"# {name}\n\nLinguagem: {language}\n"
        with open(os.path.join(project_dir, "README.md"), 'w') as f:
            f.write(readme)
        return f"OK: projeto '{name}' criado em {project_dir}"
    except Exception as e:
        return f"Erro: {str(e)}"
