import subprocess
import os


def git_status(repo_path: str = ".") -> str:
    try:
        repo_path = os.path.abspath(repo_path)
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return "Erro: " + result.stderr
        return result.stdout or "Repositorio limpo"
    except Exception as e:
        return "Erro: " + str(e)


def git_commit(repo_path: str = ".", message: str = "update") -> str:
    try:
        repo_path = os.path.abspath(repo_path)
        subprocess.run(["git", "add", "-A"], cwd=repo_path, capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path, capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return "Erro: " + str(e)


def git_log(repo_path: str = ".", n: int = 10) -> str:
    try:
        repo_path = os.path.abspath(repo_path)
        result = subprocess.run(
            ["git", "log", "--oneline", "-n", str(n)],
            cwd=repo_path, capture_output=True, text=True, timeout=10
        )
        return result.stdout or "Sem commits"
    except Exception as e:
        return "Erro: " + str(e)


def git_push(repo_path: str = ".", remote: str = "origin", branch: str = "main") -> str:
    try:
        repo_path = os.path.abspath(repo_path)
        result = subprocess.run(
            ["git", "push", remote, branch],
            cwd=repo_path, capture_output=True, text=True, timeout=60
        )
        return result.stdout + result.stderr
    except Exception as e:
        return "Erro: " + str(e)
