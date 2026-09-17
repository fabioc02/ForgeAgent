import os
import subprocess
from typing import Optional


def compile_cpp(source_path: str, output_path: Optional[str] = None, flags: str = "-O2") -> str:
    """Compila arquivo C/C++"""
    if not os.path.exists(source_path):
        return f"Erro: arquivo nao existe: {source_path}"
    
    if output_path is None:
        output_path = source_path.rsplit('.', 1)[0]
    
    cmd = f"g++ {flags} {source_path} -o {output_path}"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return f"OK: compilado com sucesso em {output_path}"
        else:
            return f"Erro de compilacao:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Erro: timeout na compilacao (60s)"
    except Exception as e:
        return f"Erro: {str(e)}"


def compile_java(source_path: str, output_dir: Optional[str] = None) -> str:
    """Compila arquivo Java"""
    if not os.path.exists(source_path):
        return f"Erro: arquivo nao existe: {source_path}"
    
    if output_dir is None:
        output_dir = os.path.dirname(source_path)
    
    cmd = f"javac -d {output_dir} {source_path}"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return f"OK: compilado com sucesso em {output_dir}"
        else:
            return f"Erro de compilacao:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Erro: timeout na compilacao (60s)"
    except Exception as e:
        return f"Erro: {str(e)}"


def run_executable(path: str, args: str = "", timeout: int = 30) -> str:
    """Executa binario compilado"""
    if not os.path.exists(path):
        return f"Erro: executavel nao existe: {path}"
    
    cmd = f"{path} {args}"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]: " + result.stderr
        
        if result.returncode == 0:
            return f"OK: executado com sucesso\n{output}"
        else:
            return f"Erro na execucao (codigo {result.returncode}):\n{output}"
    except subprocess.TimeoutExpired:
        return f"Erro: timeout na execucao ({timeout}s)"
    except Exception as e:
        return f"Erro: {str(e)}"
