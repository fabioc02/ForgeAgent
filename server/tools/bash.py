import subprocess

def bash(command, cwd="/content/ForgeAgent", timeout=60):
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n[STDERR]: " + result.stderr
        if result.returncode == 0:
            return output.strip() if output.strip() else "OK (sem output)"
        else:
            return f"Erro (codigo {result.returncode}):\n{output}"
    except subprocess.TimeoutExpired:
        return f"Timeout apos {timeout}s"
    except Exception as e:
        return f"Erro: {str(e)}"
