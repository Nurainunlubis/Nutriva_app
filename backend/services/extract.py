import re
from typing import List, Dict, Optional, Tuple

def normalize_text(text: str) -> str:
    t = text.lower()
    t = t.replace("kcal", "kkal").replace("kkai", "kkal")
    t = t.replace("mq", "mg") 
    t = re.sub(r"[^a-z0-9.,% ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def to_float(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return None

def extract_value_from_line(line: str, keywords: List[str], unit: str) -> Optional[float]:
    """
    Ambil nilai dari 1 baris:
    - keyword harus ada
    - unit harus ada (g / mg / kkal)
    - skip kalau angka itu % (AKG)
    """
    for kw in keywords:
        if kw not in line:
            continue

        # contoh: "protein 2 g" / "protein 2g" / "protein: 2 g"
        m = re.search(rf"{re.escape(kw)}\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*{unit}\b", line)
        if m:
            return to_float(m.group(1))

        # fallback: angka setelah keyword tapi pastikan bukan persen
        m2 = re.search(rf"{re.escape(kw)}\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\b(?!\s*%)", line)
        if m2:
            # kalau unit wajib tapi tidak ada, jangan ambil
            return None

    return None

def extract_nutrition(texts: List[str], return_debug: bool=False):
    lines = [normalize_text(t) for t in texts if t and t.strip()]
    result = {
        "takaran_saji_ml": None,
        "energi_kkal": None,
        "lemak_total_g": None,
        "lemak_jenuh_g": None,
        "protein_g": None,
        "karbohidrat_g": None,
        "garam_mg": None
    }

    # helper untuk cari dari baris dulu, baru fallback full_text
    def find_line_first(keys, unit):
        for ln in lines:
            v = extract_value_from_line(ln, keys, unit)
            if v is not None:
                return v
        return None

    # TAKARAN SAJI (ml)
    # ambil yg ada "ml" biar ga ketukar sama angka lain
    for ln in lines:
        m = re.search(r"(takaran saji|sajian|per sajian)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*ml\b", ln)
        if m:
            result["takaran_saji_ml"] = to_float(m.group(2))
            break

    # ENERGI (kkal)
    result["energi_kkal"] = find_line_first(["energi total", "energi"], "kkal")

    # LEMAK TOTAL (g)
    result["lemak_total_g"] = find_line_first(["lemak total", "total lemak"], "g")

    # LEMAK JENUH (g)
    result["lemak_jenuh_g"] = find_line_first(["lemak jenuh"], "g")

    # PROTEIN (g)
    result["protein_g"] = find_line_first(["protein"], "g")

    # KARBOHIDRAT (g)
    result["karbohidrat_g"] = find_line_first(["karbohidrat", "karbohidrat total", "karbo"], "g")

    # GARAM / NATRIUM (mg)
    result["garam_mg"] = find_line_first(["garam", "natrium"], "mg")

    debug = {"lines": lines}
    return (result, debug) if return_debug else result