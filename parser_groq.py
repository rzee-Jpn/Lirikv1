import os
import json
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY1"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = "llama-3.3-70b-versatile"

# --- UTILITAS ---
def clean_text(html_content):
    """Bersihkan HTML menjadi plain text"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(filename, data, subfolder=""):
    """Simpan JSON ke folder tertentu"""
    folder = os.path.join(OUT_DIR, subfolder) if subfolder else OUT_DIR
    os.makedirs(folder, exist_ok=True)
    out_path = os.path.join(folder, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

# --- PARSING DENGAN GROQ ---
def parse_with_groq(raw_text, title_hint=""):
    """
    Memanggil Groq untuk memproses teks menjadi JSON.
    Menambahkan logging chunk jika gagal parsing.
    """
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON fleksibel.
Pisahkan data menjadi:
- Bio / Profil artis
- Diskografi (judul lagu, rilis, durasi, album)
- Lirik per lagu, termasuk Kanji, Romaji, Terjemahan, dan Chord (jika ada)

Jika tidak ada data, biarkan kosong.
Jangan mengubah teks asli.
Keluarkan **hanya JSON valid**.

Teks mentah:
\"\"\"{raw_text}\"\"\"
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        groq_text = completion.choices[0].message.content

        # Coba parsing JSON
        try:
            parsed_json = json.loads(groq_text)
            parsed_json["raw_text"] = raw_text
            parsed_json["groq_status"] = "success"
            return parsed_json

        except json.JSONDecodeError:
            return {
                "raw_text": raw_text,
                "parsed_info": {"Bio / Profil": {}, "Diskografi": [], "Lirik": []},
                "groq_status": "failed",
                "groq_error": ["JSONDecodeError"],
                "raw_response": groq_text
            }

    except Exception as e:
        return {
            "raw_text": raw_text,
            "parsed_info": {"Bio / Profil": {}, "Diskografi": [], "Lirik": []},
            "groq_status": "failed",
            "groq_error": str(e)
        }

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue

    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    result = parse_with_groq(text)

    # Tentukan folder: unknown jika gagal
    folder = "unknown" if result.get("groq_status") == "failed" else ""
    save_json(file.replace(".html", ".json"), result, subfolder=folder)