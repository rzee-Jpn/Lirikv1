import os
import json

# ===============================
# Contoh data album & lagu
# ===============================
albums_data = [
    {
        "album": "Album 1",
        "penyanyi": "Fujii Kaze",
        "tahun_rilis": "2022",
        "lagu": [
            {
                "judul_lagu": "Grace",
                "tanggal_rilis": "10 Oktober 2022",
                "jenis_rilis": "Digital single",
                "tema_lirik": "Anugerah",
                "lokasi_syuting": "Uttarakhand, India",
                "deskripsi_lirik": "Lirik lagu ini menceritakan tentang perjalanan spiritual, dari kehampaan hingga menemukan Tuhan dan menjadi bebas.",
                "lirik_asli": [
                    "Grace, grace, grace, grace",
                    "Koe o karashite, sakebu kotoba mo nakute",
                    "Watashi wa tada mi o hiita ano kage kara"
                ],
                "lirik_terjemahan": [
                    "Anugerah, anugerah, anugerah, anugerah",
                    "Suara nan serak, kata-kata 'tuk diteriakkan pun menghilang",
                    "Diriku baru saja menarik tubuh ini dari bayangan itu"
                ]
            },
            {
                "judul_lagu": "Song2",
                "tanggal_rilis": "15 Oktober 2022",
                "jenis_rilis": "Digital single",
                "tema_lirik": "Cinta",
                "lokasi_syuting": "Tokyo, Japan",
                "deskripsi_lirik": "Lirik tentang cinta dan kehidupan.",
                "lirik_asli": [
                    "Original text 1",
                    "Original text 2"
                ],
                "lirik_terjemahan": [
                    "Terjemahan 1",
                    "Terjemahan 2"
                ]
            }
        ]
    },
    {
        "album": "Album 2",
        "penyanyi": "Fujii Kaze",
        "tahun_rilis": "2023",
        "lagu": [
            {
                "judul_lagu": "Lagu1",
                "tanggal_rilis": "5 Januari 2023",
                "jenis_rilis": "Digital single",
                "tema_lirik": "Kehidupan",
                "lokasi_syuting": "Osaka, Japan",
                "deskripsi_lirik": "Tentang perjalanan hidup.",
                "lirik_asli": ["Teks asli 1", "Teks asli 2"],
                "lirik_terjemahan": ["Terjemahan 1", "Terjemahan 2"]
            }
        ]
    }
]

# ===============================
# Folder utama tempat simpan JSON
# ===============================
album_root = "albums"

# ===============================
# Generate folder, metadata, dan lirik
# ===============================
for album in albums_data:
    album_name = album["album"].replace(" ", "_")
    album_path = os.path.join(album_root, album_name)
    lirik_path = os.path.join(album_path, "lirik")
    os.makedirs(lirik_path, exist_ok=True)

    metadata = {
        "album": album["album"],
        "penyanyi": album["penyanyi"],
        "tahun_rilis": album["tahun_rilis"],
        "jumlah_lagu": len(album["lagu"]),
        "lagu": []
    }

    for lagu in album["lagu"]:
        # Nama file JSON lagu
        lagu_file_name = f"{lagu['judul_lagu'].replace(' ', '_')}.json"
        lagu_file_path = os.path.join(lirik_path, lagu_file_name)

        # Simpan lirik per lagu
        with open(lagu_file_path, "w", encoding="utf-8") as f:
            json.dump({
                "judul_lagu": lagu["judul_lagu"],
                "penyanyi": album["penyanyi"],
                "tanggal_rilis": lagu["tanggal_rilis"],
                "jenis_rilis": lagu["jenis_rilis"],
                "tema_lirik": lagu["tema_lirik"],
                "lokasi_syuting": lagu["lokasi_syuting"],
                "deskripsi_lirik": lagu["deskripsi_lirik"],
                "lirik": {
                    "bahasa_asli": lagu["lirik_asli"],
                    "terjemahan": lagu["lirik_terjemahan"]
                }
            }, f, ensure_ascii=False, indent=2)

        # Tambahkan lagu ke metadata album
        metadata["lagu"].append({
            "judul": lagu["judul_lagu"],
            "file_lirik": f"lirik/{lagu_file_name}"
        })

    # Simpan metadata album
    metadata_file_path = os.path.join(album_path, "metadata_album.json")
    with open(metadata_file_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

print("✅ Semua album & lirik berhasil dibuat!")
