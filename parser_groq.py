import os
import json
import time
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
API_KEYS = [
    os.getenv("GROQ_API_KEY1"),
    os.getenv("GROQ_API_KEY2"),
    os.getenv("GROQ_API_KEY3")
]
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
FAILED_RAW_DIR = os.path.join(OUT_DIR, "failed_raw")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
MAX_RETRIES = 3
RETRY_DELAY = 10  # detik

os.makedirs(FAILED_RAW_DIR, exist_ok=True)

# --- UTILITAS ---
def clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(artist, album, data):
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # Merge diskografi lama dan baru
        if "Diskografi" in data.get("parsed_info", {}):
            if "Diskografi" not in existing.get("parsed_info", {}):
                existing.setdefault("parsed_info", {})["Diskografi"] = []
            existing["parsed_info"]["Diskografi"].extend(data["parsed_info"]["Diskografi"])
        # Merge field lain fleksibel
        for k, v in data.get("parsed_info", {}).items():
            if k != "Diskografi":
                existing.setdefault("parsed_info", {})[k] = v or existing.get("parsed_info", {}).get(k, "")
        data = existing

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def parse_with_groq(raw_text):
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON. 
Keluarkan hanya JSON valid, fleksibel jika ada field baru.
Teks mentah:
\"\"\"{raw_text}\"\"\"
"""
    for key in API_KEYS:
        if not key:
            continue
        client = Groq(api_key=key)
        for attempt in range(MAX_RETRIES):
            try:
                completion = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                return completion.choices[0].message.content
            except Exception as e:
                print(f"⚠️ Key {key} gagal: {e}")
                time.sleep(RETRY_DELAY)
        print(f"⚠️ Key {key} habis atau gagal. Coba key berikutnya.")
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
        try:
            data = json.loads(json_text)
        except Exception:
            # JSON invalid → simpan raw sementara
            raw_fail_path = os.path.join(FAILED_RAW_DIR, f"{file}.txt")
            with open(raw_fail_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"⚠️ JSON tidak valid untuk {file}, menyimpan teks mentah di {raw_fail_path}")
            continue

        artist = data.get("parsed_info", {}).get("Bio / Profil", {}).get("Nama lengkap & nama panggung", "Unknown")
        album_list = data.get("parsed_info", {}).get("Diskografi", [])
        if not album_list:
            album_list = [{"Nama album/single": os.path.splitext(file)[0]}]

        for album_entry in album_list:
            album_name = album_entry.get("Nama album/single", os.path.splitext(file)[0])
            save_json(artist.strip().replace(" ", "_"), album_name.strip().replace(" ", "_"), data)

    except Exception as e:
        # Simpan raw text sementara jika semua key gagal
        raw_fail_path = os.path.join(FAILED_RAW_DIR, f"{file}.txt")
        with open(raw_fail_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"⚠️ Gagal memproses {file}: {e}. Teks mentah disimpan di {raw_fail_path}")