import os
import json
import re
from bs4 import BeautifulSoup
from groq import Groq

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))  # pastikan variabel ini benar
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = "llama-3.3-70b-versatile"

os.makedirs(OUT_DIR, exist_ok=True)

# --- UTILITAS ---
def clean_text(html_content):
    """Hapus tag HTML dan ambil teks bersih."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(filename, data, subfolder=""):
    """Simpan hasil parsing dalam file JSON."""
    folder = os.path.join(OUT_DIR, subfolder) if subfolder else OUT_DIR
    os.makedirs(folder, exist_ok=True)
    out_path = os.path.join(folder, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def extract_json(text):
    """Ambil blok JSON valid dari teks Groq."""
    try:
        # ambil hanya isi JSON terakhir (Groq kadang kirim teks sebelum/ sesudah)
        json_part = re.search(r'\{[\s\S]*\}', text)
        if json_part:
            return json.loads(json_part.group(0))
    except Exception:
        pass
    return {}

def parse_with_groq(raw_text):
    """Panggil Groq dan parsing hasilnya menjadi struktur JSON standar."""
    prompt = f"""
Kamu sistem ekstraktor musik.
Ambil informasi dari teks berikut dan ubah menjadi JSON valid.
Jika tidak ada data, kosongkan saja.

Struktur JSON yang wajib dikirim:
{{
  "Bio / Profil": {{
    "nama": "",
    "asal": "",
    "genre": "",
    "tahun_aktif": "",
    "deskripsi": ""
  }},
  "Diskografi": [],
  "Lirik": []
}}

Teks:
\"\"\"{raw_text}\"\"\"
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        raw_response = completion.choices[0].message.content
        data = extract_json(raw_response)

        # pastikan struktur aman
        result = {
            "Bio / Profil": data.get("Bio / Profil", {}),
            "Diskografi": data.get("Diskografi", []),
            "Lirik": data.get("Lirik", [])
        }

        return {
            "raw_text": raw_text[:5000],  # batasi agar tidak terlalu panjang
            "parsed_info": result,
            "groq_status": "success",
            "groq_error": [],
            "raw_response": raw_response
        }

    except Exception as e:
        return {
            "raw_text": raw_text[:5000],
            "parsed_info": {"Bio / Profil": {}, "Diskografi": [], "Lirik": []},
            "groq_status": "failed",
            "groq_error": [str(e)],
            "raw_response": ""
        }

# --- PROSES SEMUA FILE ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue

    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    result = parse_with_groq(text)

    folder = "unknown" if result["groq_status"] == "failed" else ""
    save_json(file.replace(".html", ".json"), result, subfolder=folder)