import os
import json
import re
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
UNKNOWN_DIR = os.path.join(OUT_DIR, "unknown")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")

# --- UTILITAS ---
def clean_text(html_content):
    """Hapus HTML, dapatkan teks bersih"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def save_json(artist, album, data):
    """Simpan JSON, merge jika sudah ada file lama"""
    artist_folder = os.path.join(OUT_DIR, artist)
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # Merge Bio
        existing_bio = existing.get("parsed_info", {}).get("Bio / Profil", {})
        new_bio = data.get("parsed_info", {}).get("Bio / Profil", {})
        existing_bio.update({k: v for k, v in new_bio.items() if v})
        existing["parsed_info"]["Bio / Profil"] = existing_bio

        # Merge Diskografi
        existing_disks = existing.get("parsed_info", {}).get("Diskografi", [])
        new_disks = data.get("parsed_info", {}).get("Diskografi", [])
        for nd in new_disks:
            # Cek album sama atau baru
            album_names = [ed.get("Nama album/single", "") for ed in existing_disks]
            if nd.get("Nama album/single", "") not in album_names:
                existing_disks.append(nd)
        data["parsed_info"]["Diskografi"] = existing_disks
        data["parsed_info"]["Bio / Profil"] = existing_bio

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def save_unknown(file_name, raw_text):
    """Simpan file yang gagal parsing ke folder unknown"""
    os.makedirs(UNKNOWN_DIR, exist_ok=True)
    path = os.path.join(UNKNOWN_DIR, f"{file_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"raw_text": raw_text, "parsed_info": {"Bio / Profil": {}, "Diskografi": []}}, f, ensure_ascii=False, indent=2)
    print(f"⚠️ Disimpan di unknown: {path}")

def parse_with_groq(raw_text):
    """Minta Groq parsing struktur JSON fleksibel"""
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON fleksibel.
Jika tidak ada info, kosongkan saja. Jangan menghapus field yang sudah ada sebelumnya.
Format JSON minimal:

{{
  "raw_text": "...",
  "parsed_info": {{
    "Bio / Profil": {{}},
    "Diskografi": []
  }}
}}

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

def extract_chord_lyrics(text):
    """
    Pisahkan chord dan lirik.
    Asumsikan chord ditulis seperti [C], [Am], dsb di atas lirik.
    Return list of dict: {"chord": "...", "lyrics": "..."}
    """
    lines = text.splitlines()
    song_data = []
    current_chord = ""
    current_lyrics = ""
    chord_pattern = re.compile(r"(\[?[A-G][#b]?(m|maj7|sus2|sus4|dim|aug)?\]?)")

    for line in lines:
        if chord_pattern.search(line):
            # Simpan chord sebelumnya
            if current_lyrics:
                song_data.append({"chord": current_chord.strip(), "lyrics": current_lyrics.strip()})
                current_lyrics = ""
            current_chord = line.strip()
        else:
            current_lyrics += line + "\n"
    # Append terakhir
    if current_lyrics or current_chord:
        song_data.append({"chord": current_chord.strip(), "lyrics": current_lyrics.strip()})
    return song_data

# --- PROSES UTAMA ---
for file in os.listdir(RAW_DIR):
    if not file.endswith(".html"):
        continue
    file_path = os.path.join(RAW_DIR, file)
    print(f"🧠 Memproses: {file}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    raw_text = clean_text(html)

    try:
        # Parsing utama dengan Groq
        json_text = parse_with_groq(raw_text)
        data = json.loads(json_text)

        # Jika ada lirik, pisahkan chord
        for disk in data.get("parsed_info", {}).get("Diskografi", []):
            for song in disk.get("Lagu / Song List", []):
                lyrics = song.get("Chord & lyrics", "")
                if lyrics:
                    song["Chord & lyrics"] = extract_chord_lyrics(lyrics)

        # Tentukan artist & album
        artist = data["parsed_info"]["Bio / Profil"].get("Nama lengkap & nama panggung", "Unknown")
        album = data["parsed_info"]["Diskografi"][0].get("Nama album/single", os.path.splitext(file)[0]) if data["parsed_info"]["Diskografi"] else os.path.splitext(file)[0]

        save_json(artist.strip().replace(" ", "_"), album.strip().replace(" ", "_"), data)
    except Exception as e:
        print(f"⚠️ Gagal memproses {file}: {e}")
        save_unknown(os.path.splitext(file)[0], raw_text)