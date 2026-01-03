import re
from typing import List, Dict, Optional, Tuple

def normalize_text(text: str) -> str:
    t = text.lower()

    # satukan kcal/kkal/kal
    t = re.sub(r"\bkcal\b", "kkal", t)
    t = re.sub(r"\bkkai\b", "kkal", t)
    t = re.sub(r"\bkal\b", "kkal", t)

    # typo energi
    t = t.replace("energl", "energi").replace("energ!", "energi").replace("energ1", "energi")

    # typo takaran/sajian
    t = t.replace("sajl", "saji").replace("sajlan", "sajian")

    # mg typo
    t = t.replace("mq", "mg")

    # NORMALISASI KRUSIAL (foto 3)
    # "lemakjenuh", "lemakjjenuh", "lemakjJenuh" -> "lemak jenuh"
    t = re.sub(r"lemak\s*j+enuh", "lemak jenuh", t)

    # "seratpangan" -> "serat pangan"
    t = re.sub(r"serat\s*pangan|seratpangan", "serat pangan", t)

    t = re.sub(r"\blg\b", "1g", t)

    # rapikan karakter
    t = re.sub(r"[^a-z0-9.,%/ ]", " ", t)
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


def extract_serving_size(lines: List[str]) -> Tuple[Optional[float], Optional[str]]:
    candidates: List[Tuple[float, str, int]] = []  # (val, unit, idx)

    patterns = [
        r"(takaran\s*saji|serving\s*size)[^\d]{0,30}(\d+(?:[.,]\d+)?)\s*(g|gr|ml)\b",
        r"(takaran|serving)[^\d]{0,30}(\d+(?:[.,]\d+)?)\s*(g|gr|ml)\b",
    ]

    for idx, ln in enumerate(lines):
        for pat in patterns:
            m = re.search(pat, ln)
            if m:
                val = to_float(m.group(2))
                unit = m.group(3)
                if unit == "gr":
                    unit = "g"
                if val is not None:
                    candidates.append((val, unit, idx))

    if not candidates:
        return None, None

    # prioritaskan kandidat "g" yang paling atas
    g_candidates = [(v, u, i) for (v, u, i) in candidates if u == "g"]
    if g_candidates:
        g_candidates.sort(key=lambda x: x[2])  # idx kecil = lebih atas
        top_val, top_unit, top_idx = g_candidates[0]

        # heuristik: kalau <=5g, coba cari kandidat >=10g yang masih dekat bagian atas
        if top_val <= 5:
            for v, u, i in g_candidates:
                if v >= 10 and i <= top_idx + 3:
                    return v, u

        return top_val, top_unit

    # fallback non-g (ml) paling atas
    candidates.sort(key=lambda x: x[2])
    return candidates[0][0], candidates[0][1]

def extract_carbs_context(lines: List[str]) -> Optional[float]:
    """
    Fallback kalau keyword 'karbohidrat/total carbohydrate' hilang dari OCR.
    Ambil angka 'Xg Y%' yang posisinya biasanya:
      setelah protein, sebelum gula total.
    """
    # cari index protein dan gula
    idx_protein = next((i for i, ln in enumerate(lines) if "protein" in ln), None)
    idx_sugar   = next((i for i, ln in enumerate(lines) if "gula total" in ln or "sugar" in ln), None)

    # rentang pencarian
    start = (idx_protein + 1) if idx_protein is not None else 0
    end   = idx_sugar if idx_sugar is not None else len(lines)

    # cari pola "10g 3%" (atau "10 g 3%")
    best = None
    for i in range(start, end):
        ln = lines[i]
        m = re.search(r"\b(\d+(?:[.,]\d+)?)\s*g\b[^0-9]{0,10}(\d+)\s*%\b", ln)
        if not m:
            continue
        grams = to_float(m.group(1))
        if grams is None:
            continue

        # filter nilai masuk akal untuk karbohidrat (0g biasanya noise)
        if grams <= 0:
            continue

        # ambil kandidat pertama di rentang itu (biasanya memang karbohidrat)
        best = grams
        break

    return best

# ---------------------------------------
# ENERGI: lebih robust
# ---------------------------------------
def extract_energy_kkal(lines: List[str]) -> Optional[float]:
    """
    Strategi:
    1) Cari baris yang mengandung keyword energi + ada angka + kkal
       (tahan untuk "130kkal/kkal")
    2) Kalau tidak ketemu, cari angka+kkal di sekitar baris energi (±2 baris)
    3) Fallback: cari angka+kkal pertama yang masuk akal
    """

    energy_kw = ("energi total", "total energy", "energi")

    def find_num_kkal(s: str) -> Optional[float]:
        # tangkap "130kkal", "130 kkal", "130kkal/kkal"
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*kkal\b", s)
        return to_float(m.group(1)) if m else None

    # 1) langsung di baris energi
    for ln in lines:
        if any(k in ln for k in energy_kw):
            v = find_num_kkal(ln)
            if v is not None:
                return v

    # 2) cari di sekitar baris energi (±2 baris)
    idxs = [i for i, ln in enumerate(lines) if any(k in ln for k in energy_kw)]
    for i in idxs:
        for j in range(max(0, i-2), min(len(lines), i+3)):
            v = find_num_kkal(lines[j])
            if v is not None:
                return v

    # 3) fallback: angka+kkal pertama yang reasonable (hindari 2150 kkal AKG kalau bisa)
    candidates = []
    for ln in lines:
        v = find_num_kkal(ln)
        if v is not None:
            candidates.append(v)

    # prefer yang kecil (energi per sajian biasanya jauh < 2150)
    for v in sorted(candidates):
        if 5 <= v <= 1000:
            return v

    return None


# ---------------------------------------
# EXTRACTOR UTAMA
# ---------------------------------------
def extract_value_from_line(line: str, keywords: List[str], unit: str) -> Optional[float]:
    for kw in keywords:
        if kw not in line:
            continue

        # izinkan teks non-angka di antara keyword dan angka
        m = re.search(
            rf"{re.escape(kw)}[^0-9%]{{0,50}}(\d+(?:[.,]\d+)?)\s*{unit}\b",
            line
        )
        if m:
            return to_float(m.group(1))
    return None

def extract_sugar_fields(lines: List[str]) -> Dict[str, Optional[float]]:
    """
    Ekstrak:
    - gula_total_g: "gula", "gula total", "sugar"
    - sukrosa_g: "sukrosa", "sucrose" (kadang ditulis gula (sukrosa))
    - laktosa_g: "laktosa", "lactose"
    """
    out = {"gula_total_g": None, "sukrosa_g": None, "laktosa_g": None}

    def find_any(keys: List[str]) -> Optional[float]:
        for ln in lines:
            for kw in keys:
                if kw in ln:
                    # cari angka g setelah keyword (toleran "lg" -> "1g" kadang)
                    m = re.search(rf"{re.escape(kw)}[^0-9]{{0,50}}(\d+(?:[.,]\d+)?)\s*g\b", ln)
                    if m:
                        return to_float(m.group(1))
        return None

    # gula total (prioritas: "gula total" dulu biar ga ketukar sama "gula (sukrosa)")
    out["gula_total_g"] = find_any(["gula total", "total sugar"])
    if out["gula_total_g"] is None:
        # fallback: "gula" atau "sugar" (tapi hindari baris sukrosa/laktosa)
        for ln in lines:
            if ("sukrosa" in ln) or ("sucrose" in ln) or ("laktosa" in ln) or ("lactose" in ln):
                continue
            if ("gula" in ln) or ("sugar" in ln):
                m = re.search(r"\b(\d+(?:[.,]\d+)?)\s*g\b", ln)
                if m:
                    out["gula_total_g"] = to_float(m.group(1))
                    break

    # sukrosa
    out["sukrosa_g"] = find_any(["sukrosa", "sucrose", "gula sukrosa"])

    # laktosa
    out["laktosa_g"] = find_any(["laktosa", "lactose"])

    return out

def extract_nutrition(texts: List[str], return_debug: bool=False):
    lines = [normalize_text(t) for t in texts if t and t.strip()]

    result = {
    "takaran_saji": None,
    "takaran_saji_unit": None,
    "energi_kkal": None,
    "lemak_total_g": None,
    "lemak_jenuh_g": None,
    "protein_g": None,
    "karbohidrat_g": None,
    "gula_total_g": None,   # <---
    "sukrosa_g": None,      # <---
    "laktosa_g": None,      # <---
    "garam_mg": None
}

    def find_line_first(keys, unit):
        for ln in lines:
            v = extract_value_from_line(ln, keys, unit)
            if v is not None:
                return v
        return None

    # TAKARAN SAJI (g / ml)
    ss_val, ss_unit = extract_serving_size(lines)
    result["takaran_saji"] = ss_val
    result["takaran_saji_unit"] = ss_unit

    # ENERGI (kkal)
    result["energi_kkal"] = extract_energy_kkal(lines)

    # Makro lain (seperti punyamu)
    result["lemak_total_g"] = find_line_first(["lemak total", "total fat", "total lemak"], "g")
    result["lemak_jenuh_g"] = find_line_first(["lemak jenuh", "saturated fat"], "g")
    result["protein_g"] = find_line_first(["protein"], "g")
    result["karbohidrat_g"] = find_line_first(["karbohidrat", "total carbohydrate"], "g")
    if result["karbohidrat_g"] is None:
        result["karbohidrat_g"] = extract_carbs_context(lines)
    sugar = extract_sugar_fields(lines)
    result["gula_total_g"] = sugar["gula_total_g"]
    result["sukrosa_g"] = sugar["sukrosa_g"]
    result["laktosa_g"] = sugar["laktosa_g"]
    result["garam_mg"] = find_line_first(["garam", "natrium", "sodium"], "mg")

    debug = {"lines": lines}
    return (result, debug) if return_debug else result