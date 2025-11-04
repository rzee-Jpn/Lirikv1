import os
import json
import time
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
API_KEYS = [
    os.getenv("GROQ_API_KEY1"),
    os.getenv("GROQ_API_KEY2"),
    os.getenv("GROQ_API_KEY3"),
]

RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
FAILED_RAW_DIR = os.path.join(OUT_DIR, "failed_raw")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
MAX_RETRIES = 3
SLEEP_ON_RATE_LIMIT = 5  # detik tunggu jika rate limit

# --- UTILITAS ---
def clean_text(html_content):
    """Bersihkan HTML menjadi teks."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(artist, album, data):
    """Simpan data JSON per album/artis, merge jika sudah ada."""
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # Merge diskografi baru ke yang lama
        if "Diskografi" in data.get("parsed_info", {}):
            existing_disk = existing["parsed_info"].get("Diskografi", [])
            new_disk = data["parsed_info"]["Diskografi"]
            # Tambahkan album baru jika belum ada
            for nd in new_disk:
                names_existing = [d.get("Nama album/single") for d in existing_disk]
                if nd.get("Nama album/single") not in names_existing:
                    existing_disk.append(nd)
            existing["parsed_info"]["Diskografi"] = existing_disk
        data = existing

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def save_failed_raw(filename, raw_text):
    os.makedirs(FAILED_RAW_DIR, exist_ok=True)
    out_path = os.path.join(FAILED_RAW_DIR, f"{filename}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(raw_text)
    print(f"⚠️ JSON tidak valid untuk {filename}, menyimpan teks mentah di {out_path}")

def parse_with_groq(raw_text):
    """Coba parsing menggunakan list API_KEYS secara rotasi."""
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON.
Isi field boleh dikosongi jika tidak ada data. Format JSON fleksibel, jangan ubah data lama.

Teks mentah:
\"\"\"{raw_text}\"\"\"

Keluarkan hanya JSON valid.
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
                msg = str(e)
                if "rate_limit" in msg.lower() or "429" in msg:
                    print(f"⚠️ Rate limit. Retry in {SLEEP_ON_RATE_LIMIT}s...")
                    time.sleep(SLEEP_ON_RATE_LIMIT)
                    continue
                else:
                    print(f"⚠️ Error Groq: {e}")
                    break
    raise RuntimeError("Semua API key gagal memproses data.")

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
        except json.JSONDecodeError:
            save_failed_raw(file, text)
            continue

        artist = data.get("parsed_info", {}).get("Bio / Profil", {}).get("Nama lengkap & nama panggung", "Unknown")
        album_list = data.get("parsed_info", {}).get("Diskografi", [])
        if not album_list:
            album_list = [{"Nama album/single": os.path.splitext(file)[0]}]

        for album_entry in album_list:
            album_name = album_entry.get("Nama album/single", os.path.splitext(file)[0])
            save_json(artist.strip().replace(" ", "_"), album_name.strip().replace(" ", "_"), data)

    except Exception as e:
        print(f"⚠️ Gagal memproses {file}: {e}")
        save_failed_raw(file, text)