import os
import json
import re
from bs4 import BeautifulSoup
from groq import Groq

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
LYRIC_DIR = os.path.join(OUT_DIR, "lirik")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")

os.makedirs(LYRIC_DIR, exist_ok=True)

# --- UTILITAS ---
def clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(filename, data, subfolder=""):
    folder = os.path.join(OUT_DIR, subfolder) if subfolder else OUT_DIR
    os.makedirs(folder, exist_ok=True)
    out_path = os.path.join(folder, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

# --- Fungsi parsing Groq ---
def parse_with_groq(raw_text):
    prompt = """
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON fleksibel.
Keluarkan JSON valid, pisahkan info album dan lirik.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        raw_response = completion.choices[0].message.content
        data = json.loads(raw_response)
        return data, raw_response, "success", []
    except Exception as e:
        return {}, "", "failed", [str(e)]

# --- MAIN PROCESS ---
metadata_album = {}

for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue

    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    parsed_data, raw_resp, status, errors = parse_with_groq(text)

    album_name = parsed_data.get("album", "unknown_album")
    album_name_safe = re.sub(r"[^\w\d]+", "_", album_name)

    # Simpan metadata per album
    metadata_album[album_name_safe] = {
        "album": album_name,
        "penyanyi": parsed_data.get("penyanyi", ""),
        "rilis": parsed_data.get("rilis_single", ""),
        "lagu": []
    }

    tracklist = parsed_data.get("tracklist_single", [])
    if not tracklist:
        print(f"⚠️ Tidak ada tracklist untuk album {album_name}")

    # Simpan lirik tiap lagu
    for lagu in tracklist or [{"judul": "unknown", "durasi": ""}]:
        judul = lagu.get("judul", "unknown")
        judul_safe = re.sub(r"[^\w\d]+", "_", judul)
        lyric_file = f"{judul_safe}.json"
        lyric_path = os.path.join("lirik", lyric_file)

        # ambil lirik, jika tidak ada pakai placeholder
        lirik_data = parsed_data.get("terjemahan_lirik", {})
        if not lirik_data:
            lirik_data = {"kanji": "", "romaji": "", "bahasa_indonesia": ""}

        save_json(lyric_file, {
            "judul": judul,
            "penyanyi": parsed_data.get("penyanyi", ""),
            "lirik": lirik_data
        }, subfolder="lirik")

        # tambahkan link file lirik ke metadata album
        metadata_album[album_name_safe]["lagu"].append({
            "judul": judul,
            "durasi": lagu.get("durasi", ""),
            "file_lirik": lyric_path
        })

# --- Simpan metadata album ---
save_json("metadata_album.json", metadata_album)