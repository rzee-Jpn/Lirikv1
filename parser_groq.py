import os
import json
import time
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = "llama-3.3-70b-versatile"
API_KEYS = [
    os.getenv("GROQ_API_KEY1"),
    os.getenv("GROQ_API_KEY2"),
    os.getenv("GROQ_API_KEY3")
]

# --- UTILITAS ---
def clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(artist, album, data):
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            # Gabungkan data baru dengan lama (update fleksibel)
            for album_new in data.get("parsed_info", {}).get("Diskografi", []):
                existing["parsed_info"]["Diskografi"].append(album_new)
            data = existing
        except Exception:
            pass

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def save_raw(file, text):
    raw_folder = os.path.join(OUT_DIR, "failed_raw")
    os.makedirs(raw_folder, exist_ok=True)
    out_path = os.path.join(raw_folder, f"{file}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"⚠️ Disimpan raw sementara: {out_path}")

# --- PARSING DENGAN GROW ---
def parse_with_groq(raw_text):
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON fleksibel. 
Isi field yang ada, kosongkan yang tidak ada. Jangan timpa data lama, tambahkan jika baru. 
Keluarkan hanya JSON valid.

Teks mentah:
\"\"\"{raw_text}\"\"\"
"""
    for key in API_KEYS:
        client = Groq(api_key=key)
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            msg = str(e)
            if "rate_limit" in msg.lower():
                print(f"⚠️ Rate limit pada API key, pindah ke key berikutnya...")
                continue
            else:
                raise e
    raise RuntimeError("Semua API key gagal atau limit habis.")

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue
    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    try:
        json_text = parse_with_groq(text)
        data = json.loads(json_text)

        # Tentukan artist & album
        artist = data.get("parsed_info", {}).get("Bio / Profil", {}).get(
            "Nama lengkap & nama panggung", "Unknown"
        ) or "Unknown"
        albums = data.get("parsed_info", {}).get("Diskografi", [])
        if not albums:
            album_name = os.path.splitext(file)[0]
            save_json(artist.strip().replace(" ", "_"), album_name.strip().replace(" ", "_"), data)
        else:
            for album_data in albums:
                album_name = album_data.get("Nama album/single") or os.path.splitext(file)[0]
                save_json(artist.strip().replace(" ", "_"), album_name.strip().replace(" ", "_"), data)
    except Exception as e:
        print(f"⚠️ JSON tidak valid untuk {file}, menyimpan teks mentah.")
        save_raw(os.path.splitext(file)[0], text)
        print(f"⚠️ Gagal memproses {file}: {e}")