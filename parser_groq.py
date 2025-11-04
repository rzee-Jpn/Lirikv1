import os
import json
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
API_KEYS = [
    os.getenv("GROQ_API_KEY1"),
    os.getenv("GROQ_API_KEY2"),
    os.getenv("GROQ_API_KEY3")
]
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
FAILED_DIR = os.path.join(OUT_DIR, "failed_raw")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

# --- UTILITAS ---
def clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {path}")

def merge_dict(old, new):
    """Merge dictionary lama dan baru secara fleksibel."""
    for key, value in new.items():
        if isinstance(value, dict):
            old[key] = merge_dict(old.get(key, {}), value)
        elif isinstance(value, list):
            # Tambahkan item baru jika tidak ada
            old_list = old.get(key, [])
            for item in value:
                if item not in old_list:
                    old_list.append(item)
            old[key] = old_list
        else:
            # Jangan timpa field lama kalau sudah ada, kecuali kosong
            if key not in old or not old[key]:
                old[key] = value
    return old

def parse_with_groq(raw_text, api_key_index=0):
    client = Groq(api_key=API_KEYS[api_key_index])
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data dari teks mentah menjadi JSON.
Isi hanya JSON, tapi field boleh kosong jika data tidak ada.

Teks mentah:
\"\"\"{raw_text}\"\"\"
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
    for idx, key in enumerate(API_KEYS):
        if not key:
            continue
        try:
            json_text = parse_with_groq(text, api_key_index=idx)
            data_new = json.loads(json_text)
            success = True
            break
        except Exception as e:
            print(f"⚠️ Gagal dengan API_KEY{idx+1}: {e}")

    if not success:
        failed_path = os.path.join(FAILED_DIR, f"{file}.txt")
        with open(failed_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"⚠️ JSON tidak valid, menyimpan teks mentah di {failed_path}")
        continue

    artist = data_new.get("parsed_info", {}).get("Bio / Profil", {}).get("Nama lengkap & nama panggung", "Unknown").strip().replace(" ", "_")
    album = data_new.get("parsed_info", {}).get("Diskografi", [{}])[0].get("Nama album/single", os.path.splitext(file)[0]).strip().replace(" ", "_")

    out_path = os.path.join(OUT_DIR, artist, f"{album}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    old_data = load_json(out_path)
    merged_data = merge_dict(old_data, data_new)
    save_json(out_path, merged_data)