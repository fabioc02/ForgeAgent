import subprocess
import os
import tempfile
import shutil
from typing import Dict


def compile_cpp(source_path: str, output_path: str = None, flags: str = "-O2 -std=c++17") -> str:
    try:
        source_path = os.path.abspath(source_path)
        if not os.path.exists(source_path):
            return "Erro: arquivo nao existe: " + source_path
        
        if not output_path:
            output_path = source_path.rsplit(".", 1)[0]
        
        compiler = "g++" if source_path.endswith(".cpp") else "gcc"
        cmd = [compiler] + flags.split() + [source_path, "-o", output_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        output += "\n[Exit: " + str(result.returncode) + "]"
        
        if result.returncode == 0:
            output += "\n[OK] Binario gerado: " + output_path
        return output
    except Exception as e:
        return "Erro: " + str(e)


def compile_java(source_path: str, output_dir: str = ".") -> str:
    try:
        source_path = os.path.abspath(source_path)
        output_dir = os.path.abspath(output_dir)
        if not os.path.exists(source_path):
            return "Erro: arquivo nao existe"
        
        os.makedirs(output_dir, exist_ok=True)
        cmd = ["javac", "-d", output_dir, source_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        output = result.stdout + result.stderr
        if result.returncode == 0:
            output += "\n[OK] Compilado em " + output_dir
        return output
    except Exception as e:
        return "Erro: " + str(e)


def run_executable(path: str, args: str = "", timeout: int = 30) -> str:
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return "Erro: binario nao existe"
        
        cmd = [path] + (args.split() if args else [])
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        output += "\n[Exit: " + str(result.returncode) + "]"
        return output
    except subprocess.TimeoutExpired:
        return "Erro: timeout"
    except Exception as e:
        return "Erro: " + str(e)


def create_project(name: str, language: str = "cpp", base_dir: str = "Drive/projects") -> str:
    try:
        base_dir = os.path.abspath(base_dir)
        project_dir = os.path.join(base_dir, name)
        
        if os.path.exists(project_dir):
            return "Erro: projeto ja existe: " + project_dir
        
        os.makedirs(project_dir, exist_ok=True)
        
        if language == "cpp":
            os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
            os.makedirs(os.path.join(project_dir, "include"), exist_ok=True)
            os.makedirs(os.path.join(project_dir, "build"), exist_ok=True)
            
            main_cpp = "#include <iostream>\n\nint main() {\n    std::cout << \"Hello from " + name + "\" << std::endl;\n    return 0;\n}\n"
            with open(os.path.join(project_dir, "src", "main.cpp"), "w") as f:
                f.write(main_cpp)
            
            cmake = "cmake_minimum_required(VERSION 3.10)\nproject(" + name + ")\nset(CMAKE_CXX_STANDARD 17)\nadd_executable(" + name + " src/main.cpp)\n"
            with open(os.path.join(project_dir, "CMakeLists.txt"), "w") as f:
                f.write(cmake)
        
        elif language == "java":
            pkg = name.lower().replace("-", "_")
            pkg_dir = os.path.join(project_dir, "src", "main", "java", pkg)
            os.makedirs(pkg_dir, exist_ok=True)
            
            main_java = "package " + pkg + ";\n\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello from " + name + "\");\n    }\n}\n"
            with open(os.path.join(pkg_dir, "Main.java"), "w") as f:
                f.write(main_java)
        
        elif language == "python":
            os.makedirs(os.path.join(project_dir, name), exist_ok=True)
            with open(os.path.join(project_dir, name, "__init__.py"), "w") as f:
                f.write("")
            main_py = "def main():\n    print(\"Hello from " + name + "\")\n\nif __name__ == \"__main__\":\n    main()\n"
            with open(os.path.join(project_dir, "main.py"), "w") as f:
                f.write(main_py)
        
        elif language == "android":
            os.makedirs(os.path.join(project_dir, "app", "src", "main", "java"), exist_ok=True)
            os.makedirs(os.path.join(project_dir, "app", "src", "main", "res", "layout"), exist_ok=True)
            
            build_gradle = "plugins {\n    id 'com.android.application'\n}\n\nandroid {\n    namespace 'com.example." + name.lower() + "'\n    compileSdk 34\n    defaultConfig {\n        applicationId \"com.example." + name.lower() + "\"\n        minSdk 24\n        targetSdk 34\n    }\n}\n"
            with open(os.path.join(project_dir, "app", "build.gradle"), "w") as f:
                f.write(build_gradle)
        
        return "OK: projeto '" + name + "' criado em " + project_dir + " (" + language + ")"
    except Exception as e:
        return "Erro: " + str(e)
