import os
import re
import json
from bs4 import BeautifulSoup
from pathlib import Path

# =======================
# KONFIGURASI DASAR
# =======================
INPUT_DIR = "data_raw"
OUTPUT_DIR = "data_clean"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =======================
# CLEANER HTML
# =======================
def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n").strip()
    text = re.sub(r'\n+', '\n', text)
    return text


# =======================
# PEMISAH BAGIAN LIRIK
# =======================
def extract_lyrics_sections(text):
    sections = {"kanji": "", "romaji": "", "terjemahan": ""}
    current = None
    for line in text.splitlines():
        l = line.strip().lower()
        if "kanji" in l:
            current = "kanji"
            continue
        elif "romaji" in l:
            current = "romaji"
            continue
        elif "indonesia" in l or "terjemahan" in l:
            current = "terjemahan"
            continue
        if current:
            sections[current] += line + "\n"
    return sections


# =======================
# PROFIL ARTIS TEMPLATE
# =======================
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


# =======================
# DETEKSI FEATURING / COMPOSER
# =======================
def detect_metadata(text):
    featuring = ""
    composer = ""
    lyricist = ""

    feat_match = re.search(r"(?:feat\.?|ft\.?)\s+([A-Za-z0-9 '&-]+)", text, re.IGNORECASE)
    if feat_match:
        featuring = feat_match.group(1).strip()

    comp_match = re.search(r"(?:music by|composed by|composer:)\s*([A-Za-z0-9 '&,-]+)", text, re.IGNORECASE)
    if comp_match:
        composer = comp_match.group(1).strip()

    lyr_match = re.search(r"(?:lyrics? by|written by|lirik oleh)\s*([A-Za-z0-9 '&,-]+)", text, re.IGNORECASE)
    if lyr_match:
        lyricist = lyr_match.group(1).strip()

    return featuring, composer, lyricist


# =======================
# PARSER PER LAGU
# =======================
def parse_songs(album_text, album_name):
    pattern = r"Lagu\s+([A-Za-z0-9&'\" ]+)\s+\"([^\"]+)\""
    parts = re.split(pattern, album_text)
    chunks = []
    for i in range(1, len(parts), 3):
        artist_ref = parts[i].strip()
        song_title = parts[i + 1].strip()
        content = parts[i + 2].strip()
        chunks.append((song_title, content))
    if not chunks:
        chunks = [("Unknown Song", album_text)]

    lagu_list = []
    for song_title, song_text in chunks:
        sections = extract_lyrics_sections(song_text)
        featuring, composer, lyricist = detect_metadata(song_text)

        tanggal = re.search(r"dirilis(?: pada)? ([0-9]{1,2} [A-Za-z]+ [0-9]{4})", song_text)
        tanggal_rilis = tanggal.group(1) if tanggal else ""
        durasi = re.search(r"(\d:\d{2})", song_text)
        durasi_str = durasi.group(1) if durasi else ""

        label = ""
        for l in ["Virgin Music", "Sony Music", "Universal", "Warner"]:
            if l.lower() in song_text.lower():
                label = l

        lagu_list.append({
            "Judul lagu": song_title,
            "Composer": composer,
            "Lyricist": lyricist,
            "Featuring": featuring,
            "Tahun rilis": tanggal_rilis[-4:] if tanggal_rilis else "",
            "Album asal": album_name,
            "Durasi": durasi_str,
            "Genre": "",
            "Key": "",
            "Chord & lyrics": sections["kanji"].strip(),
            "Terjemahan": sections["terjemahan"].strip()
        })

    return lagu_list


# =======================
# GABUNG DATA ARTIS
# =======================
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


# =======================
# MAIN PROCESS
# =======================
if __name__ == "__main__":
    print("🔍 Mendeteksi file HTML di data_raw/...")

    found_files = list(Path(INPUT_DIR).rglob("*.html"))
    if not found_files:
        print("⚠️ Tidak ditemukan file HTML di dalam data_raw/.")
        exit(0)

    for file_path in found_files:
        # Ambil nama artis dari nama folder induk
        artist_name = file_path.parent.name
        album_name = file_path.stem.replace("_", " ").title()

        print(f"\n🎤 Memproses artis: {artist_name}")
        print(f"💿 Album/Sumber: {album_name}")

        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()

        clean_text = clean_html(html)
        lagu_list = parse_songs(clean_text, album_name)

        parsed_info = {
            "Bio / Profil": make_artist_profile(artist_name),
            "Diskografi": [{
                "Nama album/single": album_name,
                "Tanggal rilis": "",
                "Label": "",
                "Jumlah lagu": str(len(lagu_list)),
                "Cover art": "",
                "Produksi oleh / kolaborator tetap": "",
                "Lagu / Song List": lagu_list
            }]
        }

        merge_artist_data(parsed_info, artist_name)

    print("\n✅ Semua file HTML telah diproses dan disimpan ke data_clean/")
