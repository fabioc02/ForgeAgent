import os
import json
from typing import List, Dict
import google.generativeai as genai


class LLMProvider:
    def __init__(self, model_name=None, backend="gemini"):
        self.model_name = model_name or "gemini-2.5-pro"
        self.backend = backend
        self.model = None
        self.mode = "uninitialized"
        self.device = "cloud"

    def initialize(self, api_key=None, model_name=None):
        if model_name:
            self.model_name = model_name
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY nao configurada")
        print("[LLM] Configurando Gemini 2.5 Pro...", flush=True)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.mode = "gpu"
        print(f"[LLM] OK - Modelo: {self.model_name}", flush=True)

    def generate(self, messages, max_tokens=8192, temperature=0.2):
        if self.mode == "error":
            raise RuntimeError("LLM em erro")
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"[SYSTEM]\n{content}")
            elif role == "user":
                prompt_parts.append(f"[USER]\n{content}")
            elif role == "assistant":
                prompt_parts.append(f"[ASSISTANT]\n{content}")
            elif role == "tool":
                prompt_parts.append(f"[TOOL_RESULT]\n{content}")
        full_prompt = "\n\n".join(prompt_parts)
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        )
        return response.text.strip()

    def get_status(self):
        return {
            "mode": self.mode,
            "model": self.model_name,
            "backend": "gemini",
            "device": self.device
        }
