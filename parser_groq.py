import os
import json
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAW_DIR = "data_raw"
OUT_DIR = "data_output"
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")  # model default

# --- UTILITAS ---
def clean_text(html_content):
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return html_content  # fallback jika BeautifulSoup gagal

def save_json(artist, album, data):
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing["parsed_info"]["Diskografi"].extend(data["parsed_info"].get("Diskografi", []))
            data = existing
        except Exception:
            pass  # jika gagal load, timpa saja

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def parse_with_groq(raw_text):
    prompt = f"""
Strukturkan data musik/artis dari teks mentah menjadi JSON. Format output:

{{
  "raw_text": "...",
  "parsed_info": {{
    "Bio / Profil": {{
      "Nama lengkap & nama panggung": "",
      "Asal / domisili": "",
      "Tanggal lahir": "",
      "Genre musik": "",
      "Influences / inspirasi": "",
      "Cerita perjalanan musik": "",
      "Foto profil": "",
      "Link media sosial": ""
    }},
    "Diskografi": [
      {{
        "Nama album/single": "",
        "Tanggal rilis": "",
        "Label": "",
        "Jumlah lagu": "",
        "Cover art": "",
        "Produksi oleh / kolaborator tetap": "",
        "Lagu / Song List": [
          {{
            "Judul lagu": "",
            "Composer": "",
            "Lyricist": "",
            "Featuring": "",
            "Tahun rilis": "",
            "Album asal": "",
            "Durasi": "",
            "Genre": "",
            "Key": "",
            "Chord & lyrics": "",
            "Terjemahan": ""
          }}
        ]
      }}
    ]
  }}
}}

Teks mentah:
\"\"\"{raw_text}\"\"\"

Keluarkan **hanya JSON valid**.
"""
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return completion.choices[0].message.content

# --- PROSES UTAMA ---
os.makedirs(OUT_DIR, exist_ok=True)

for file in sorted(os.listdir(RAW_DIR)):
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

        bio = data.get("parsed_info", {}).get("Bio / Profil", {})
        diskografi = data.get("parsed_info", {}).get("Diskografi", [])

        if not diskografi:
            raise ValueError("Diskografi kosong")

        artist = bio.get("Nama lengkap & nama panggung", "Unknown").strip().replace(" ", "_")
        album = diskografi[0].get("Nama album/single", os.path.splitext(file)[0]).strip().replace(" ", "_")

        save_json(artist, album, data)

    except json.JSONDecodeError:
        print(f"⚠️ JSON tidak valid untuk {file}, menyimpan teks mentah.")
        save_json("Unknown", os.path.splitext(file)[0], {"raw_text": text, "parsed_info": {}})
    except Exception as e:
        print(f"⚠️ Gagal memproses {file}: {e}")