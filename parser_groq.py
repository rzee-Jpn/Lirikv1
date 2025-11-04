import os
import json
from bs4 import BeautifulSoup

RAW_DIR = "data_raw"
CLEAN_DIR = "data_clean"

# === TEMPLATE BIO ARTIS ===
def template_bio(artis):
    return {
        "Nama lengkap & nama panggung": artis,
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

# === TEMPLATE ALBUM ===
def template_album(album_name):
    return {
        "Nama album/single": album_name,
        "Tanggal rilis": "",
        "Label": "",
        "Jumlah lagu": "",
        "Cover art": "",
        "Produksi oleh / kolaborator tetap": "",
        "Lagu / Song List": []
    }

# === TEMPLATE LAGU ===
def template_lagu(judul, album_name):
    return {
        "Judul lagu": judul,
        "Composer": "",
        "Lyricist": "",
        "Featuring": "",
        "Tahun rilis": "",
        "Album asal": album_name,
        "Durasi": "",
        "Genre": "",
        "Key": "",
        "Chord & lyrics": "",
        "Terjemahan": ""
    }

# === Fungsi parsing HTML lagu ===
def parse_html_song(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "lxml")

    judul = (
        soup.find("h1").get_text(strip=True)
        if soup.find("h1")
        else soup.title.get_text(strip=True)
        if soup.title
        else os.path.splitext(os.path.basename(file_path))[0]
    )

    teks = soup.get_text(separator="\n", strip=True)
    return judul, teks, html

# === Fungsi untuk merge (update incremental) ===
def merge_album_data(existing_data, new_album):
    """
    Menggabungkan data lama dan baru tanpa menimpa lagu yang sudah ada.
    Jika ada lagu baru -> tambahkan.
    Jika lagu sama tapi teks berbeda -> update.
    """
    existing_album = existing_data["parsed_info"]["Diskografi"][0]
    existing_songs = {s["Judul lagu"]: s for s in existing_album["Lagu / Song List"]}
    new_songs = new_album["Lagu / Song List"]

    updated = False

    for song in new_songs:
        judul = song["Judul lagu"]
        if judul not in existing_songs:
            # Tambah lagu baru
            existing_album["Lagu / Song List"].append(song)
            updated = True
        else:
            # Jika lirik berubah, update
            if song["Chord & lyrics"] != existing_songs[judul]["Chord & lyrics"]:
                existing_songs[judul]["Chord & lyrics"] = song["Chord & lyrics"]
                updated = True

    if updated:
        existing_album["Jumlah lagu"] = str(len(existing_album["Lagu / Song List"]))

    return existing_data, updated

# === Fungsi utama ===
def main():
    os.makedirs(CLEAN_DIR, exist_ok=True)

    for artis in os.listdir(RAW_DIR):
        artis_path = os.path.join(RAW_DIR, artis)
        if not os.path.isdir(artis_path):
            continue

        for album in os.listdir(artis_path):
            album_path = os.path.join(artis_path, album)
            if not os.path.isdir(album_path):
                continue

            print(f"🎧 Memproses {artis} - {album}")

            album_data = template_album(album)
            song_list = []
            raw_html_joined = ""

            for file in os.listdir(album_path):
                if not file.endswith(".html"):
                    continue
                file_path = os.path.join(album_path, file)
                judul, teks, raw_html = parse_html_song(file_path)

                lagu = template_lagu(judul, album)
                lagu["Chord & lyrics"] = teks
                song_list.append(lagu)
                raw_html_joined += f"\n<!-- {file} -->\n{raw_html}"

            album_data["Jumlah lagu"] = str(len(song_list))
            album_data["Lagu / Song List"] = song_list

            parsed_new = {
                "raw_text": raw_html_joined,
                "parsed_info": {
                    "Bio / Profil": template_bio(artis),
                    "Diskografi": [album_data]
                }
            }

            artis_out = os.path.join(CLEAN_DIR, artis)
            os.makedirs(artis_out, exist_ok=True)
            output_file = os.path.join(artis_out, f"{album}.json")

            # Jika sudah ada file lama → merge
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                merged, updated = merge_album_data(existing_data, album_data)
                if updated:
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(merged, f, ensure_ascii=False, indent=2)
                    print(f"🔁 Update: {output_file}")
                else:
                    print(f"⏩ Tidak ada perubahan: {output_file}")
            else:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(parsed_new, f, ensure_ascii=False, indent=2)
                print(f"✅ Baru dibuat: {output_file}")

if __name__ == "__main__":
    main()