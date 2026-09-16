# ForgeAgent - AI Software Forge

Agente de IA especializado em desenvolvimento multi-plataforma.

## Capacidades

- C/C++: GCC, Clang, CMake, Makefiles
- Java: Maven, Gradle, aplicacoes desktop
- Android: Apps nativos com Gradle e Android SDK
- Linux: Bash, daemons, scripts, systemd
- Windows: PowerShell, batch, aplicacoes nativas
- Python/Node.js: Scripts e aplicacoes web

## Arquitetura

    Frontend (React + Vite + Tailwind)
             |
    Backend (FastAPI + WebSocket)
             |
    Agente (Qwen + ReAct Loop)
             |
    Tools (terminal, filesystem, code_executor, memory, git)
             |
    Persistencia (Google Drive)

## Modelos

- GPU (T4 Tesla): Qwen2.5-Coder-7B-Instruct (7B params, AWQ)
- CPU (fallback): Qwen2.5-Coder-1.5B-Instruct (1.5B params)

## Uso no Colab

1. Abra o Colab_ForgeAgent.ipynb
2. Preencha NGROK_TOKEN
3. Execute a unica celula
4. Acesse o link gerado
