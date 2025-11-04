import os
import json
import time
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
FAILED_DIR = os.path.join(OUT_DIR, "failed_raw")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

# API keys (dapat 3 key)
API_KEYS = [os.getenv("GROQ_API_KEY1"), os.getenv("GROQ_API_KEY2"), os.getenv("GROQ_API_KEY3")]
MODEL = "llama-3.3-70b-versatile"
MAX_RETRY = 3
RETRY_DELAY = 60  # detik

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
        # Merge: tambahkan data baru tanpa menghapus field lama
        for key, value in data.get("parsed_info", {}).items():
            if key not in existing["parsed_info"]:
                existing["parsed_info"][key] = value
            elif isinstance(value, list):
                existing["parsed_info"][key].extend(value)
        data = existing

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def save_failed(file_name, text):
    failed_path = os.path.join(FAILED_DIR, f"{file_name}.txt")
    with open(failed_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"⚠️ Disimpan raw sementara: {failed_path}")

def parse_with_groq(raw_text, api_key):
    client = Groq(api_key=api_key)
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON.
Jika tidak tahu, kosongkan field. Tambahkan data baru jika ada.
Teks mentah:
\"\"\"{raw_text}\"\"\"
Keluarkan hanya JSON valid.
"""
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return completion.choices[0].message.content

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue
    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    text = clean_text(html)
    success = False

    for attempt in range(MAX_RETRY):
        for api_key in API_KEYS:
            if not api_key:
                continue
            try:
                json_text = parse_with_groq(text, api_key)
                data = json.loads(json_text)
                artist = data.get("parsed_info", {}).get("Bio / Profil", {}).get("Nama lengkap & nama panggung", "Unknown")
                album = data.get("parsed_info", {}).get("Diskografi", [{}])[0].get("Nama album/single", os.path.splitext(file)[0])
                save_json(artist.strip().replace(" ", "_"), album.strip().replace(" ", "_"), data)
                success = True
                break
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1}, API {api_key[:4]}..., gagal: {e}")
                time.sleep(2)
        if success:
            break
        print(f"⏳ Retry {attempt+1}/{MAX_RETRY} dalam {RETRY_DELAY}s...")
        time.sleep(RETRY_DELAY)

    if not success:
        save_failed(file, text)