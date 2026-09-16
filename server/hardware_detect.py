import torch
from typing import Dict, Any


def detect_hardware() -> Dict[str, Any]:
    result = {
        "gpu_available": False,
        "gpu_name": None,
        "gpu_memory_gb": 0.0,
        "cuda_version": None,
        "mode": "cpu",
        "recommended_model": "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    }
    try:
        if torch.cuda.is_available():
            result["gpu_available"] = True
            result["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            result["gpu_memory_gb"] = round(props.total_memory / 1e9, 2)
            result["cuda_version"] = torch.version.cuda
            vram_gb = result["gpu_memory_gb"]
            if vram_gb >= 14:
                result["recommended_model"] = "Qwen/Qwen2.5-Coder-7B-Instruct"
                result["mode"] = "gpu"
            elif vram_gb >= 8:
                result["recommended_model"] = "Qwen/Qwen2.5-Coder-3B-Instruct"
                result["mode"] = "gpu"
    except Exception as e:
        print("[HardwareDetect] Erro: " + str(e))
    return result


def get_model_for_mode(mode: str = "auto") -> Dict[str, str]:
    hw = detect_hardware()
    if mode == "auto":
        mode = hw["mode"]
    if mode == "gpu" and hw["gpu_available"]:
        return {
            "model": hw["recommended_model"],
            "backend": "vllm" if hw["gpu_memory_gb"] >= 14 else "transformers",
            "device": "cuda",
            "mode": "gpu"
        }
    else:
        return {
            "model": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
            "backend": "transformers",
            "device": "cpu",
            "mode": "cpu"
        }
