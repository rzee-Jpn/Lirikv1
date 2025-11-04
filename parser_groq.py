import os
import json
import re
from groq import Groq
from bs4 import BeautifulSoup

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY3"))
RAW_DIR = "data_raw"
OUT_DIR = "data_clean"
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")

# --- UTILITAS ---
def clean_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def format_chord_lyrics(raw_text):
    """
    Pisahkan chord dan lirik. Chord di atas lirik.
    Simple detection: baris yang mengandung chord (A-G, Am, Dm, dsb.)
    """
    lines = raw_text.split("\n")
    chord_lines = []
    lyric_lines = []
    chord_pattern = re.compile(r"\b([A-G][#b]?m?(7|maj7|sus4|dim)?)\b")
    for line in lines:
        if chord_pattern.search(line):
            chord_lines.append(line)
        else:
            lyric_lines.append(line)
    return {
        "chord_position": "di atas lirik",
        "chord": "\n".join(chord_lines),
        "lyrics": "\n".join(lyric_lines)
    }

def save_json(artist, album, data):
    artist_folder = os.path.join(OUT_DIR, artist or "unknown")
    os.makedirs(artist_folder, exist_ok=True)
    out_path = os.path.join(artist_folder, f"{album}.json")

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # Merge diskografi
        for new_album in data.get("parsed_info", {}).get("Diskografi", []):
            album_name = new_album.get("Nama album/single") or "unknown_album"
            # Cek jika album sudah ada
            matched = False
            for idx, existing_album in enumerate(existing["parsed_info"].get("Diskografi", [])):
                if existing_album.get("Nama album/single") == album_name:
                    # Merge lagu
                    for new_song in new_album.get("Lagu / Song List", []):
                        matched_song = False
                        for i, old_song in enumerate(existing_album.get("Lagu / Song List", [])):
                            if old_song.get("Judul lagu") == new_song.get("Judul lagu"):
                                # Merge lirik/chord/terjemahan
                                existing_album["Lagu / Song List"][i].update(new_song)
                                matched_song = True
                                break
                        if not matched_song:
                            existing_album["Lagu / Song List"].append(new_song)
                    matched = True
                    break
            if not matched:
                existing["parsed_info"]["Diskografi"].append(new_album)
        data = existing

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Disimpan: {out_path}")

def parse_with_groq(raw_text):
    prompt = f"""
Kamu adalah sistem yang menstrukturkan data musik dari teks mentah menjadi JSON dengan format fleksibel. 
Jika ada lirik dan chord gitar, pisahkan di field 'Chord & lyrics' dengan chord di atas lirik. 
Jika terjemahan tersedia, simpan di field 'Terjemahan'.

Output JSON harus valid.

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
        except json.JSONDecodeError:
            # Jika JSON invalid, simpan raw_text ke folder unknown
            data = {"raw_text": text, "parsed_info": {"Bio / Profil": {}, "Diskografi": []}}
            save_json("unknown", os.path.splitext(file)[0], data)
            print(f"⚠️ JSON tidak valid untuk {file}, disimpan sebagai raw.")
            continue

        # Format chord & lirik untuk setiap lagu jika tersedia
        for album in data.get("parsed_info", {}).get("Diskografi", []):
            for idx, song in enumerate(album.get("Lagu / Song List", [])):
                raw_lyrics = song.get("Chord & lyrics") or song.get("Lyrics") or ""
                if raw_lyrics:
                    song["Chord & lyrics"] = format_chord_lyrics(raw_lyrics)
                    if "Lyrics" in song:
                        del song["Lyrics"]

        artist = data["parsed_info"]["Bio / Profil"].get("Nama lengkap & nama panggung") or "unknown"
        album_name = (data["parsed_info"]["Diskografi"][0].get("Nama album/single")
                      if data["parsed_info"]["Diskografi"] else os.path.splitext(file)[0])
        save_json(artist.strip().replace(" ", "_"), album_name.strip().replace(" ", "_"), data)

    except Exception as e:
        # Jika Groq gagal, simpan mentah
        data = {"raw_text": text, "parsed_info": {"Bio / Profil": {}, "Diskografi": []}}
        save_json("unknown", os.path.splitext(file)[0], data)
        print(f"⚠️ Gagal memproses {file}: {e}")