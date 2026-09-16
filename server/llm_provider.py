import torch
from typing import List, Dict


class LLMProvider:
    def __init__(self, model_name: str = None, backend: str = "auto"):
        self.model_name = model_name
        self.backend = backend
        self.llm = None
        self.tokenizer = None
        self.mode = "uninitialized"
        self.device = None

    def initialize(self, model_name: str = None, backend: str = None):
        if model_name:
            self.model_name = model_name
        if backend:
            self.backend = backend
        if not self.model_name:
            raise ValueError("model_name nao especificado")
        print("[LLM] Iniciando " + self.model_name + " via " + self.backend)
        try:
            if self.backend == "vllm" and torch.cuda.is_available():
                self._init_vllm()
            elif self.backend == "transformers":
                self._init_transformers()
            else:
                raise ValueError("Backend invalido: " + self.backend)
            print("[LLM] OK - Modo: " + self.mode)
        except Exception as e:
            print("[LLM] ERRO: " + str(e))
            self.mode = "error"
            raise

    def _init_vllm(self):
        from vllm import LLM
        self.llm = LLM(
            model=self.model_name,
            quantization="awq" if "7B" in self.model_name else None,
            trust_remote_code=True,
            gpu_memory_utilization=0.85,
            max_model_len=4096,
            dtype="float16"
        )
        self.mode = "gpu"
        self.device = "cuda"

    def _init_transformers(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        self.llm = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map=device if device == "cuda" else {"": device},
            torch_dtype=dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        self.mode = "gpu" if device == "cuda" else "cpu"
        self.device = device

    def _build_prompt(self, messages: List[Dict]) -> str:
        if self.tokenizer and hasattr(self.tokenizer, "apply_chat_template"):
            try:
                return self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception as e:
                print("[LLM] Erro chat template: " + str(e))
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
        
        if self.mode == "gpu" and self.backend == "vllm":
            from vllm import SamplingParams
            params = SamplingParams(
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )
            outputs = self.llm.generate([prompt], params, use_tqdm=False)
            return outputs[0].outputs[0].text.strip()
        
        elif self.backend == "transformers":
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.llm.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.9,
                    do_sample=temperature > 0
                )
            response = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            return response.strip()
        
        else:
            raise RuntimeError("Modo nao suportado: " + self.mode)

    def get_status(self) -> Dict:
        return {
            "mode": self.mode,
            "model": self.model_name,
            "backend": self.backend,
            "device": self.device
        }
