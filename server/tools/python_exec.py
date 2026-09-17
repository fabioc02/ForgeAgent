import subprocess
import tempfile
import os

def python_exec(code, timeout=30):
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        result = subprocess.run(['python3', temp_path], capture_output=True, text=True, timeout=timeout)
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n[STDERR]: " + result.stderr
        os.unlink(temp_path)
        if result.returncode == 0:
            return output.strip() if output.strip() else "OK (sem output)"
        else:
            return f"Erro (codigo {result.returncode}):\n{output}"
    except subprocess.TimeoutExpired:
        return f"Timeout apos {timeout}s"
    except Exception as e:
        return f"Erro: {str(e)}"
