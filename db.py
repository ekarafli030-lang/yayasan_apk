import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "yayasan.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tabel Users (Admin & Mahasantri)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nama_lengkap TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'mahasantri')),
            nim_nip TEXT NOT NULL,
            divisi_kamar TEXT NOT NULL,
            status_aktif TEXT DEFAULT 'Aktif'
        )
    """)

    # 2. Tabel Data Digital Yayasan (Pengumuman, SOP, Dokumen Resmi)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_digital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_dokumen TEXT NOT NULL,
            judul TEXT NOT NULL,
            kategori TEXT NOT NULL,
            isi_ringkas TEXT NOT NULL,
            tanggal_terbit TEXT NOT NULL,
            penulis TEXT NOT NULL
        )
    """)

    # 3. Tabel Sistem Operasional (Presensi & Kegiatan Harian)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operasional_absensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kegiatan TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            waktu_checkin TEXT NOT NULL,
            status_kehadiran TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 4. Tabel Pelayanan Administrasi Harian (Surat, Izin, Berkas)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS layanan_administrasi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_tiket TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            jenis_layanan TEXT NOT NULL,
            keperluan TEXT NOT NULL,
            tanggal_pengajuan TEXT NOT NULL,
            status TEXT DEFAULT 'Menunggu',
            catatan_admin TEXT DEFAULT '-',
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Cek apakah data user sudah ada
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users_seed = [
            (
                "admin",
                generate_password_hash("admin123"),
                "Administrator Utama Yayasan",
                "admin",
                "NIP-YYS-001",
                "Pusat Kendali Operasional",
                "Aktif",
            ),
            (
                "rafli",
                generate_password_hash("santri123"),
                "Muhammad Rafli Eka Prastyo",
                "mahasantri",
                "MS-2026-005",
                "Software Dev // Asrama Al-Khawarizmi",
                "Aktif",
            ),
            (
                "zaki",
                generate_password_hash("santri123"),
                "Ahmad Zaki Mubarak",
                "mahasantri",
                "MS-2026-012",
                "Cyber Security // Asrama Ibnu Sina",
                "Aktif",
            ),
        ]
        cursor.executemany("""
            INSERT INTO users (username, password, nama_lengkap, role, nim_nip, divisi_kamar, status_aktif)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, users_seed)

        # Data awal Dokumen & Pengumuman Digital
        digital_seed = [
            (
                "DOC-2026-01",
                "Protokol Operasional Jam Malam & Lab Komputer",
                "SOP Operasional",
                "Penggunaan laboratorium riset malam hari wajib didaftarkan melalui portal administrasi sebelum pukul 20.00 WIB.",
                "2026-11-01",
                "Divisi Operasional",
            ),
            (
                "DOC-2026-02",
                "Jadwal Evaluasi Proyek Akhir Semester Ganjil",
                "Pengumuman Akademik",
                "Seluruh Mahasantri diharapkan menyiapkan repositori aplikasi dan dokumentasi sistem untuk sidang evaluasi pekan depan.",
                "2026-11-08",
                "Bagian Akademik",
            ),
        ]
        cursor.executemany("""
            INSERT INTO data_digital (kode_dokumen, judul, kategori, isi_ringkas, tanggal_terbit, penulis)
            VALUES (?, ?, ?, ?, ?, ?)
        """, digital_seed)

        # Data awal Log Operasional Presensi
        absensi_seed = [
            (2, "Halaqah Pagi & Apel Operasional", "2026-11-10", "05:30:12", "Hadir"),
            (2, "Sesi Praktikum Pengembangan Web", "2026-11-10", "08:05:44", "Hadir"),
            (3, "Halaqah Pagi & Apel Operasional", "2026-11-10", "05:32:19", "Hadir"),
        ]
        cursor.executemany("""
            INSERT INTO operasional_absensi (user_id, kegiatan, tanggal, waktu_checkin, status_kehadiran)
            VALUES (?, ?, ?, ?, ?)
        """, absensi_seed)

        # Data awal Layanan Administrasi Harian
        admin_seed = [
            (
                "ADM-2611-001",
                2,
                "Surat Keterangan Mahasantri Aktif",
                "Persyaratan administrasi pendaftaran beasiswa dan kompetisi IT nasional.",
                "2026-11-09",
                "Disetujui",
                "Dokumen telah ditandatangani secara digital. Silakan unduh atau ambil di ruang sekretariat.",
            ),
            (
                "ADM-2611-002",
                3,
                "Izin Penggunaan Lab Server Malam",
                "Simulasi pengujian keamanan jaringan untuk tugas akhir kelompok.",
                "2026-11-10",
                "Menunggu",
                "Sedang diverifikasi oleh kepala operasional asrama.",
            ),
        ]
        cursor.executemany("""
            INSERT INTO layanan_administrasi (kode_tiket, user_id, jenis_layanan, keperluan, tanggal_pengajuan, status, catatan_admin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, admin_seed)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database yayasan.db berhasil diinisiasi beserta data awal.")