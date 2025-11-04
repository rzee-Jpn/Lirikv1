import os
import json
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")

# --- UTILITAS ---
def clean_text(html_content):
    """Bersihkan HTML menjadi plain text."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def merge_data(existing, new):
    """Merge JSON lama dengan data baru secara fleksibel."""
    # Merge Bio
    bio_existing = existing.get("parsed_info", {}).get("Bio / Profil", {})
    bio_new = new.get("parsed_info", {}).get("Bio / Profil", {})
    for k, v in bio_new.items():
        if v:  # update only if there's new data
            bio_existing[k] = v
    existing["parsed_info"]["Bio / Profil"] = bio_existing

    # Merge Diskografi
    albums_existing = existing.get("parsed_info", {}).get("Diskografi", [])
    albums_new = new.get("parsed_info", {}).get("Diskografi", [])

    for album_new in albums_new:
        match = next((a for a in albums_existing if a.get("Nama album/single") == album_new.get("Nama album/single")), None)
        if match:
            # Update lagu list
            existing_songs = match.get("Lagu / Song List", [])
            for song_new in album_new.get("Lagu / Song List", []):
                if not any(s.get("Judul lagu") == song_new.get("Judul lagu") for s in existing_songs):
                    existing_songs.append(song_new)
            match["Lagu / Song List"] = existing_songs
            # Update field album lainnya jika ada data baru
            for key, val in album_new.items():
                if val and key != "Lagu / Song List":
                    match[key] = val
        else:
            albums_existing.append(album_new)

    existing["parsed_info"]["Diskografi"] = albums_existing
    return existing

def save_json(artist, album, data):
    """Simpan JSON per artis dan per album."""
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                data = merge_data(existing, data)
            except:
                pass  # fallback: tulis ulang data baru

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def parse_with_groq(raw_text):
    """Meminta Groq untuk menstrukturkan data HTML menjadi JSON."""
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik/artis dari teks mentah menjadi JSON. 
Jika tidak ada data, field dikosongi. Teks mentah bisa memiliki bio artis, album, lagu, lirik, dll. 
JSON harus fleksibel, bisa menambah field baru jika ditemukan data baru. 
Berikan output hanya JSON valid.

Contoh struktur minimal (boleh ada field tambahan):
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
    try:
        json_text = parse_with_groq(text)
        try:
            data = json.loads(json_text)
        except:
            # fallback kalau JSON gagal: simpan minimal
            data = {"raw_text": text, "parsed_info": {"Bio / Profil": {}, "Diskografi": []}}
            print(f"⚠️ JSON tidak valid untuk {file}, menyimpan teks mentah.")

        artist = data.get("parsed_info", {}).get("Bio / Profil", {}).get("Nama lengkap & nama panggung", "Unknown") or "Unknown"
        album_list = data.get("parsed_info", {}).get("Diskografi", [])
        if album_list:
            for album_entry in album_list:
                album_name = album_entry.get("Nama album/single", os.path.splitext(file)[0])
                save_json(artist.strip().replace(" ", "_"), album_name.strip().replace(" ", "_"), data)
        else:
            # tidak ada album → simpan 1 file per artis
            save_json(artist.strip().replace(" ", "_"), os.path.splitext(file)[0], data)

    except Exception as e:
        print(f"⚠️ Gagal memproses {file}: {e}")