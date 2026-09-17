import os
import sys
from typing import List, Dict


class LLMProvider:
    def __init__(self, model_name: str = None, backend: str = "auto"):
        self.model_name = model_name
        self.backend = backend
        self.llm = None
        self.mode = "uninitialized"
        self.device = None

    def initialize(self, model_name: str = None, backend: str = None):
        if model_name:
            self.model_name = model_name
        if backend:
            self.backend = backend
        print("[LLM] Iniciando via lama-cpp-python...", flush=True)
        try:
            self._init_llama_cpp()
            print("[LLM] OK - Modo: " + self.mode, flush=True)
        except Exception as e:
            print("[LLM] ERRO: " + str(e), flush=True)
            self.mode = "error"
            raise

    def _init_llama_cpp(self):
        from llama_cpp import Llama
        from huggingface_hub import hf_hub_download
        import torch
        
        print("[LLM] Baixando modelo GGUF do HuggingFace...", flush=True)
        model_path = hf_hub_download(
            repo_id="bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
            filename="DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"
        )
        print("[LLM] Modelo baixado: " + model_path, flush=True)
        
        n_gpu_layers = -1 if torch.cuda.is_available() else 0
        
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=4096,
            n_batch=512,
            verbose=False
        )
        
        self.mode = "gpu" if torch.cuda.is_available() else "cpu"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("[LLM] Carregado em " + self.mode, flush=True)

    def _build_prompt(self, messages: List[Dict]) -> str:
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += "<|im_start|>" + role + "\n" + content + "<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        return prompt

    def generate(self, messages: List[Dict], max_tokens: int = 1024, temperature: float = 0.1) -> str:
        if self.mode == "error":
            raise RuntimeError("LLM em estado de erro")
        prompt = self._build_prompt(messages)
        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            stop=["<|im_end|>"]
        )
        return output["choices"][0]["text"].strip()

    def get_status(self) -> Dict:
        return {
            "mode": self.mode,
            "model": self.model_name,
            "backend": "llama-cpp",
            "device": self.device
        }
