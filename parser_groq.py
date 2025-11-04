import os
import json
from groq import Groq
from bs4 import BeautifulSoup
import re

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
UNKNOWN_DIR = os.path.join(OUT_DIR, "unknown")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")

# --- UTILITAS ---
def clean_text(html_content):
    """Hapus HTML dan ambil teks mentah."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def extract_chords(line):
    """Ekstrak chord dari satu baris lirik."""
    chords = re.findall(r'\b[A-G][#b]?m?(maj7|sus4|dim|aug)?\b', line)
    return " ".join(chords) if chords else ""

def save_json_safe(folder, filename, data):
    """Simpan JSON, buat folder jika belum ada."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {path}")

def parse_with_groq(raw_text):
    """Kirim ke Groq untuk parsing JSON. Lebih fleksibel."""
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON.
Hanya keluarkan JSON valid.
Jika tidak ada data, biarkan field kosong.
Format fleksibel:
{{
  "Bio / Profil": {{}},
  "Diskografi": [],
  "Lirik": [],
  "Chord": []
}}
Teks mentah:
\"\"\"{raw_text}\"\"\"
"""
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return completion.choices[0].message.content

def merge_data(old, new):
    """Merge data baru ke data lama tanpa menimpa data lama."""
    merged = old.copy()
    for key in new:
        if key not in merged or not merged[key]:
            merged[key] = new[key]
        elif isinstance(merged[key], list) and isinstance(new[key], list):
            merged[key].extend([item for item in new[key] if item not in merged[key]])
        elif isinstance(merged[key], dict) and isinstance(new[key], dict):
            merged[key] = merge_data(merged[key], new[key])
    return merged

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue
    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    groq_status = "failed"
    try:
        json_text = parse_with_groq(text)
        data = json.loads(json_text)
        groq_status = "success"

        # Ekstrak lirik & chord dari raw_text jika Groq tidak memberikan
        if "Lirik" not in data or not data["Lirik"]:
            lines = text.split("\n")
            lirik_list = []
            for line in lines:
                if line.strip():
                    lirik_list.append({
                        "line": line.strip(),
                        "chord": extract_chords(line)
                    })
            data["Lirik"] = lirik_list

        artist = data.get("Bio / Profil", {}).get("Nama lengkap & nama panggung", "Unknown").strip().replace(" ", "_")
        album = "Unknown_Album"
        if "Diskografi" in data and data["Diskografi"]:
            album_name = data["Diskografi"][0].get("Nama album/single")
            if album_name:
                album = album_name.strip().replace(" ", "_")

        # Tambahkan status Groq
        data["groq_status"] = groq_status

        # Jika file lama sudah ada, merge
        out_folder = os.path.join(OUT_DIR, artist)
        out_path = f"{album}.json"
        if os.path.exists(os.path.join(out_folder, out_path)):
            with open(os.path.join(out_folder, out_path), "r", encoding="utf-8") as f:
                old_data = json.load(f)
            data = merge_data(old_data, data)
            data["groq_status"] = groq_status  # pastikan tetap update status

        save_json_safe(out_folder, out_path, data)

    except Exception as e:
        print(f"⚠️ Gagal memproses {file}: {e}")
        # Simpan raw_text di folder unknown
        save_json_safe(UNKNOWN_DIR, file.replace(".html", ".json"), {
            "raw_text": text,
            "parsed_info": {"Bio / Profil": {}, "Diskografi": []},
            "groq_status": groq_status
        })