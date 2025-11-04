import os
import re
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ============ CONFIG ============
INPUT_DIR = "data_raw"
OUTPUT_DIR = "data_clean"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.2-70b-text"  # model baru pengganti llama-3.1-70b-versatile
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ============ UTIL FUNGI ============
def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n").strip()
    text = re.sub(r'\n+', '\n', text)
    return text


def call_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }

    resp = requests.post(GROQ_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        raise Exception(f"Error code: {resp.status_code} - {resp.text}")

    return resp.json()["choices"][0]["message"]["content"]


# ============ TEMPLATE DATA ============
def make_artist_profile(name):
    return {
        "Nama lengkap & nama panggung": name,
        "Asal / domisili": "",
        "Tanggal lahir": "",
        "Genre musik": "",
        "Influences / inspirasi": "",
        "Cerita perjalanan musik": "",
        "Foto profil": "",
        "Link media sosial": {
            "BandLab": "",
            "YouTube": "",
            "Spotify": "",
            "Instagram": ""
        }
    }


def merge_artist_data(parsed_info, artist_name):
    folder = Path(OUTPUT_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / f"{artist_name.lower().replace(' ', '_')}.json"

    if not file_path.exists():
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(parsed_info, f, indent=2, ensure_ascii=False)
        print(f"🆕 File baru dibuat: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        existing_data = json.load(f)

    for new_album in parsed_info.get("Diskografi", []):
        existing_album = next(
            (a for a in existing_data["Diskografi"]
             if a["Nama album/single"].lower() == new_album["Nama album/single"].lower()),
            None
        )
        if existing_album:
            for new_song in new_album.get("Lagu / Song List", []):
                existing_titles = [s["Judul lagu"].lower() for s in existing_album["Lagu / Song List"]]
                if new_song["Judul lagu"].lower() not in existing_titles:
                    existing_album["Lagu / Song List"].append(new_song)
        else:
            existing_data["Diskografi"].append(new_album)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Data artis '{artist_name}' diperbarui: {file_path}")


# ============ MAIN ============
for artist_folder in Path(INPUT_DIR).iterdir():
    if not artist_folder.is_dir():
        continue

    artist_name = artist_folder.name
    print(f"\n🎤 Memproses artis: {artist_name}")

    for file_path in artist_folder.glob("*.html"):
        print(f"🧠 Memproses: {file_path.name}")
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()

        text = clean_html(html)

        prompt = f"""
Kamu adalah asisten yang mem-parsing data lagu Jepang.
Dari teks berikut, ekstrak informasi lengkap menjadi JSON dengan struktur berikut:

{{
  "Bio / Profil": {{
    "Nama lengkap & nama panggung": "...",
    "Asal / domisili": "...",
    "Tanggal lahir": "...",
    "Genre musik": "...",
    "Influences / inspirasi": "...",
    "Cerita perjalanan musik": "...",
    "Foto profil": "...",
    "Link media sosial": {{
      "BandLab": "",
      "YouTube": "",
      "Spotify": "",
      "Instagram": ""
    }}
  }},
  "Diskografi": [
    {{
      "Nama album/single": "...",
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

Teks yang perlu kamu analisis:
{text}
        """

        try:
            groq_output = call_groq(prompt)
            data = json.loads(groq_output)
        except Exception as e:
            print(f"⚠️ Gagal memproses {file_path.name}: {e}")
            continue

        merge_artist_data(data, artist_name)

print("\n✅ Semua file selesai diproses.")