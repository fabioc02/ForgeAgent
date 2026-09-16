import os
import struct
import json
import math
from typing import Dict, List, Optional, Tuple
from collections import Counter


def hexdump(path: str, offset: int = 0, length: int = 512) -> str:
    """Exibe dump hexadecimal de um arquivo."""
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return "Erro: arquivo nao existe"
        
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(length)
        
        if not data:
            return "Sem dados neste offset"
        
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = " ".join("{:02x}".format(b) for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append("{:08x}  {:<48}  |{}|".format(offset + i, hex_part, ascii_part))
        
        return "\n".join(lines)
    except Exception as e:
        return "Erro: " + str(e)


def analyze_binary(path: str) -> str:
    """Analisa estrutura binaria de um arquivo (magic bytes, headers)."""
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return "Erro: arquivo nao existe"
        
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            header = f.read(512)
        
        info = {
            "path": path,
            "size": size,
            "size_human": _human_size(size),
            "magic_hex": " ".join("{:02x}".format(b) for b in header[:16]),
            "magic_ascii": "".join(chr(b) if 32 <= b < 127 else "." for b in header[:16]),
        }
        
        magic = header[:4]
        format_detected = "desconhecido"
        if magic == b"\x7fELF":
            format_detected = "ELF (Linux executable)"
        elif magic[:2] == b"MZ":
            format_detected = "PE (Windows executable)"
        elif magic == b"PK\x03\x04":
            format_detected = "ZIP/JAR/APK/DOCX"
        elif magic[:4] == b"\xca\xfe\xba\xbe":
            format_detected = "Java class file"
        elif magic[:3] == b"ID3":
            format_detected = "MP3 (ID3 tag)"
        elif magic[:4] == b"RIFF":
            format_detected = "RIFF (WAV/AVI)"
        elif magic[:8] == b"\x89PNG\r\n\x1a\n":
            format_detected = "PNG image"
        elif magic[:3] == b"\xff\xd8\xff":
            format_detected = "JPEG image"
        elif magic[:4] == b"OggS":
            format_detected = "OGG audio"
        elif magic[:4] == b"FORM":
            format_detected = "IFF (Amiga/EA)"
        elif header[:4] == b"YMH0" or header[:4] == b"YMH1":
            format_detected = "Yamaha Voice/Style"
        elif b"CAS" in header[:16]:
            format_detected = "Possivel CASM (Yamaha)"
        elif b"CTB" in header[:16]:
            format_detected = "Possivel CTB (Yamaha)"
        
        info["format_detected"] = format_detected
        
        byte_freq = Counter(header)
        info["unique_bytes_in_header"] = len(byte_freq)
        info["most_common_byte"] = "{:02x}".format(byte_freq.most_common(1)[0][0])
        
        printable = sum(1 for b in header if 32 <= b < 127)
        info["printable_ratio"] = round(printable / len(header), 3)
        
        return json.dumps(info, indent=2)
    except Exception as e:
        return "Erro: " + str(e)


def find_patterns(path: str, pattern_hex: str, max_results: int = 20) -> str:
    """Busca padrao de bytes (hex) em arquivo. Ex: '4D5A' para MZ."""
    try:
        path = os.path.abspath(path)
        pattern_hex = pattern_hex.replace(" ", "").replace("0x", "")
        if len(pattern_hex) % 2 != 0:
            return "Erro: pattern deve ter numero par de digitos hex"
        
        pattern = bytes.fromhex(pattern_hex)
        
        with open(path, "rb") as f:
            data = f.read()
        
        positions = []
        start = 0
        while True:
            idx = data.find(pattern, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1
            if len(positions) >= max_results:
                break
        
        if not positions:
            return "Padrao nao encontrado: " + pattern_hex
        
        result = "Padrao {} encontrado {} vezes:\n".format(pattern_hex, len(positions))
        for pos in positions[:max_results]:
            context = data[max(0, pos-8):pos+len(pattern)+8]
            ctx_hex = " ".join("{:02x}".format(b) for b in context)
            result += "  offset {:08x}: {}\n".format(pos, ctx_hex)
        
        return result
    except Exception as e:
        return "Erro: " + str(e)


def extract_strings(path: str, min_length: int = 4, max_results: int = 100) -> str:
    """Extrai strings ASCII de um arquivo binario."""
    try:
        path = os.path.abspath(path)
        with open(path, "rb") as f:
            data = f.read()
        
        strings = []
        current = []
        current_offset = 0
        
        for i, b in enumerate(data):
            if 32 <= b < 127:
                if not current:
                    current_offset = i
                current.append(chr(b))
            else:
                if len(current) >= min_length:
                    strings.append((current_offset, "".join(current)))
                current = []
        
        if len(current) >= min_length:
            strings.append((current_offset, "".join(current)))
        
        if not strings:
            return "Nenhuma string encontrada"
        
        result = "Strings encontradas (min {} chars): {}\n\n".format(min_length, len(strings))
        for offset, s in strings[:max_results]:
            preview = s[:80] + ("..." if len(s) > 80 else "")
            result += "{:08x}: {}\n".format(offset, preview)
        
        if len(strings) > max_results:
            result += "\n... e mais {} strings".format(len(strings) - max_results)
        
        return result
    except Exception as e:
        return "Erro: " + str(e)


def compare_files(path1: str, path2: str, max_diffs: int = 50) -> str:
    """Compara dois arquivos binarios byte-a-byte."""
    try:
        path1 = os.path.abspath(path1)
        path2 = os.path.abspath(path2)
        
        with open(path1, "rb") as f:
            data1 = f.read()
        with open(path2, "rb") as f:
            data2 = f.read()
        
        info = {
            "file1": path1,
            "file2": path2,
            "size1": len(data1),
            "size2": len(data2),
            "size_equal": len(data1) == len(data2)
        }
        
        diffs = []
        min_len = min(len(data1), len(data2))
        for i in range(min_len):
            if data1[i] != data2[i]:
                diffs.append({
                    "offset": i,
                    "offset_hex": "{:08x}".format(i),
                    "byte1": "{:02x}".format(data1[i]),
                    "byte2": "{:02x}".format(data2[i])
                })
                if len(diffs) >= max_diffs:
                    break
        
        info["total_diffs"] = len(diffs)
        info["diffs_truncated"] = len(diffs) >= max_diffs
        info["first_diffs"] = diffs[:20]
        
        identical_bytes = sum(1 for i in range(min_len) if data1[i] == data2[i])
        info["similarity"] = round(identical_bytes / max(len(data1), len(data2)), 4)
        
        return json.dumps(info, indent=2)
    except Exception as e:
        return "Erro: " + str(e)


def entropy_analysis(path: str, block_size: int = 1024) -> str:
    """Analisa entropia de um arquivo (detecta compressao/criptografia)."""
    try:
        path = os.path.abspath(path)
        with open(path, "rb") as f:
            data = f.read()
        
        def entropy(d):
            if not d:
                return 0.0
            freq = Counter(d)
            length = len(d)
            e = -sum((c/length) * math.log2(c/length) for c in freq.values())
            return e
        
        total_entropy = entropy(data)
        
        blocks = []
        for i in range(0, len(data), block_size):
            block = data[i:i+block_size]
            if len(block) < block_size // 2:
                break
            e = entropy(block)
            blocks.append({
                "offset": i,
                "offset_hex": "{:08x}".format(i),
                "entropy": round(e, 4),
                "classification": _classify_entropy(e)
            })
        
        result = "=== Analise de Entropia ===\n"
        result += "Arquivo: {}\n".format(path)
        result += "Tamanho: {} bytes\n".format(len(data))
        result += "Entropia total: {:.4f} bits/byte ({})\n\n".format(
            total_entropy, _classify_entropy(total_entropy)
        )
        result += "Blocos de {} bytes:\n".format(block_size)
        for b in blocks[:30]:
            result += "  {:08x}: {:.4f} ({})\n".format(
                b["offset"], b["entropy"], b["classification"]
            )
        
        return result
    except Exception as e:
        return "Erro: " + str(e)


def parse_struct(path: str, offset: int, format_str: str) -> str:
    """Parseia estrutura C em dados binarios. Format: '<IHH' (little-endian: uint32, uint16, uint16)."""
    try:
        path = os.path.abspath(path)
        with open(path, "rb") as f:
            f.seek(offset)
            size = struct.calcsize(format_str)
            data = f.read(size)
        
        if len(data) < size:
            return "Erro: dados insuficientes (precisa {} bytes, tem {})".format(size, len(data))
        
        values = struct.unpack(format_str, data)
        
        type_names = {
            "b": "int8", "B": "uint8",
            "h": "int16", "H": "uint16",
            "i": "int32", "I": "uint32",
            "q": "int64", "Q": "uint64",
            "f": "float32", "d": "float64"
        }
        
        result = "Struct parseada em offset {:08x}:\n".format(offset)
        result += "Format: {}\n\n".format(format_str)
        
        clean_fmt = format_str.lstrip("<>=!@")
        for i, (ch, val) in enumerate(zip(clean_fmt, values)):
            tname = type_names.get(ch, ch)
            result += "field[{}]: {} = {} (0x{:x})\n".format(
                i, tname, val, val if isinstance(val, int) else 0
            )
        
        result += "\nRaw hex: " + " ".join("{:02x}".format(b) for b in data)
        return result
    except Exception as e:
        return "Erro: " + str(e)


def search_signature(path: str, signature: str) -> str:
    """Busca assinatura conhecida (ex: 'CASM', 'CTB', 'NTT')."""
    try:
        path = os.path.abspath(path)
        with open(path, "rb") as f:
            data = f.read()
        
        sig_bytes = signature.encode("ascii", errors="ignore")
        positions = []
        start = 0
        while True:
            idx = data.find(sig_bytes, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1
        
        if not positions:
            return "Assinatura '{}' nao encontrada".format(signature)
        
        result = "Assinatura '{}' encontrada {} vezes:\n\n".format(signature, len(positions))
        for pos in positions[:20]:
            context = data[pos:pos+64]
            hex_part = " ".join("{:02x}".format(b) for b in context[:32])
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in context[:32])
            result += "offset {:08x}:\n".format(pos)
            result += "  hex:   {}\n".format(hex_part)
            result += "  ascii: {}\n\n".format(ascii_part)
        
        return result
    except Exception as e:
        return "Erro: " + str(e)


def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return "{:.2f} {}".format(size, unit)
        size /= 1024
    return "{:.2f} TB".format(size)


def _classify_entropy(e: float) -> str:
    if e < 1.0:
        return "muito baixa (dados repetitivos/zerados)"
    elif e < 3.0:
        return "baixa (texto/estruturado)"
    elif e < 5.0:
        return "media (dados mistos)"
    elif e < 7.0:
        return "alta (possivelmente comprimido)"
    else:
        return "muito alta (criptografado/comprimido forte)"
