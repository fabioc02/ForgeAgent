import os
import sys
import torch
from typing import List, Dict

# Workaround: bloquear torchaudio antes de importar transformers
import types
if 'torchaudio' not in sys.modules:
    fake_ta = types.ModuleType('torchaudio')
    fake_ta.__version__ = '0.0.0'
    sys.modules['torchaudio'] = fake_ta

os.environ['TRANSFORMERS_NO_AUDIO'] = '1'


class LLMProvider:
    def __init__(self, model_name: str = None, backend: str = 'auto'):
        self.model_name = model_name
        self.backend = backend
        self.llm = None
        self.tokenizer = None
        self.mode = 'uninitialized'
        self.device = None

    def initialize(self, model_name: str = None, backend: str = None):
        if model_name:
            self.model_name = model_name
        if backend:
            self.backend = backend
        if not self.model_name:
            raise ValueError('model_name nao especificado')
        print('[LLM] Iniciando ' + self.model_name + ' via ' + self.backend, flush=True)
        try:
            if self.backend == 'transformers':
                self._init_transformers()
            else:
                raise ValueError('Backend invalido: ' + self.backend)
            print('[LLM] OK - Modo: ' + self.mode, flush=True)
        except Exception as e:
            print('[LLM] ERRO: ' + str(e), flush=True)
            self.mode = 'error'
            raise

    def _init_transformers(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        print('[LLM] Carregando tokenizer...', flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        dtype = torch.float16 if device == 'cuda' else torch.float32
        print('[LLM] Carregando modelo em ' + device, flush=True)
        self.llm = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map=device if device == 'cuda' else {'': device},
            torch_dtype=dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        self.mode = 'gpu' if device == 'cuda' else 'cpu'
        self.device = device
        print('[LLM] Modelo carregado em ' + self.mode, flush=True)

    def _build_prompt(self, messages: List[Dict]) -> str:
        if self.tokenizer and hasattr(self.tokenizer, 'apply_chat_template'):
            try:
                return self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception as e:
                print('[LLM] Erro chat template: ' + str(e), flush=True)
        prompt = ''
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            prompt += '<|im_start|>' + role + '\n' + content + '<|im_end|>\n'
        prompt += '<|im_start|>assistant\n'
        return prompt

    def generate(self, messages: List[Dict], max_tokens: int = 1024, temperature: float = 0.1) -> str:
        if self.mode == 'error':
            raise RuntimeError('LLM em estado de erro')
        prompt = self._build_prompt(messages)
        inputs = self.tokenizer(prompt, return_tensors='pt').to(self.device)
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

    def get_status(self) -> Dict:
        return {
            'mode': self.mode,
            'model': self.model_name,
            'backend': self.backend,
            'device': self.device
        }
