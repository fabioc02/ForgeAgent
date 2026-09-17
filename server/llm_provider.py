import os
import json
from typing import List, Dict
from google import genai
from google.genai import types


class LLMProvider:
    def __init__(self, model_name=None, backend="gemini"):
        self.model_name = model_name or "gemini-2.5-flash"
        self.backend = backend
        self.client = None
        self.mode = "uninitialized"
        self.device = "cloud"

    def initialize(self, api_key=None, model_name=None):
        if model_name:
            self.model_name = model_name
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY nao configurada")
        print(f"[LLM] Configurando {self.model_name}...", flush=True)
        self.client = genai.Client(api_key=api_key)
        self.mode = "gpu"
        print(f"[LLM] OK - Modelo: {self.model_name}", flush=True)

    def generate(self, messages, max_tokens=8192, temperature=0.2):
        if self.mode == "error":
            raise RuntimeError("LLM em erro")
        
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)]
                ))
            elif role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=content)]
                ))
            elif role == "tool":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"[TOOL_RESULT]\n{content}")]
                ))
        
        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_instruction
        )
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )
        
        return response.text.strip()

    def get_status(self):
        return {
            "mode": self.mode,
            "model": self.model_name,
            "backend": "gemini",
            "device": self.device
        }
