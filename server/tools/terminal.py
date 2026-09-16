import subprocess
import os
from typing import Dict, Any


ALLOWED_COMMANDS = [
    "ls", "cat", "head", "tail", "grep", "find", "wc",
    "echo", "pwd", "mkdir", "touch", "cp", "mv", "rm",
    "gcc", "g++", "clang", "clang++", "make", "cmake",
    "javac", "java", "gradle", "mvn",
    "python3", "python", "node", "npm",
    "hexdump", "xxd", "od", "strings", "file",
    "objdump", "readelf", "nm", "ldd",
    "git", "zip", "unzip", "tar",
    "diff", "patch", "sort", "uniq", "cut", "awk", "sed"
]

BLOCKED_PATTERNS = ["&&", "||", "|", ";", "`", "$", "(", ")", ">>", "<"]


def terminal(command: str, cwd: str = ".", timeout: int = 30) -> str:
    """Executa um comando no terminal de forma segura."""
    if not command or not command.strip():
        return "Erro: comando vazio"
    
    cmd_parts = command.strip().split()
    base_cmd = cmd_parts[0]
    
    if base_cmd not in ALLOWED_COMMANDS:
        return "Erro: comando nao permitido: " + base_cmd + ". Permitidos: " + ", ".join(ALLOWED_COMMANDS[:10]) + "..."
    
    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return "Erro: padrao bloqueado no comando: " + pattern
    
    if ".." in command and ("/" in command):
        if "../" in command:
            return "Erro: path traversal nao permitido"
    
    try:
        work_dir = os.path.abspath(cwd)
        if not os.path.exists(work_dir):
            os.makedirs(work_dir, exist_ok=True)
        
        result = subprocess.run(
            command,
            shell=False,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            executable="/bin/bash",
            args=["bash", "-c", command]
        )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "
[STDERR]
" + result.stderr
        
        output += "
[Exit code: " + str(result.returncode) + "]"
        
        if len(output) > 10000:
            output = output[:10000] + "
... [truncado, " + str(len(output) - 10000) + " chars omitidos]"
        
        return output
    except subprocess.TimeoutExpired:
        return "Erro: timeout (" + str(timeout) + "s)"
    except Exception as e:
        return "Erro: " + str(e)


def get_allowed_commands() -> list:
    return ALLOWED_COMMANDS
