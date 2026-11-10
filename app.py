from datetime import datetime
from functools import wraps
import random
from db import get_db_connection, init_db
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "cyber_yayasan_secret_key_2026"

# Pastikan database langsung siap saat aplikasi dijalankan
init_db()


# Decorator Proteksi Login & Role
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Silakan login terlebih dahulu untuk mengakses sistem.", "error")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Akses ditolak: Anda tidak memiliki otoritas ke halaman tersebut.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route("/")
def index():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("mahasantri_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["nama_lengkap"] = user["nama_lengkap"]
            session["role"] = user["role"]
            session["nim_nip"] = user["nim_nip"]
            session["divisi_kamar"] = user["divisi_kamar"]

            flash(f"Selamat datang di Sistem Yayasan, {user['nama_lengkap']}.", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("mahasantri_dashboard"))

        flash("Username atau password tidak valid.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesi Anda telah diakhiri dengan aman.", "info")
    return redirect(url_for("login"))


# ==========================================
# ROUTES ADMIN: DATA DIGITAL, OPERASIONAL & ADMINISTRASI
# ==========================================

@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    conn = get_db_connection()

    mahasantri_list = conn.execute(
        "SELECT * FROM users WHERE role = 'mahasantri' ORDER BY id DESC"
    ).fetchall()

    dokumen_list = conn.execute(
        "SELECT * FROM data_digital ORDER BY id DESC"
    ).fetchall()

    absensi_list = conn.execute("""
        SELECT o.*, u.nama_lengkap, u.nim_nip, u.divisi_kamar
        FROM operasional_absensi o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.id DESC LIMIT 25
    """).fetchall()

    administrasi_list = conn.execute("""
        SELECT l.*, u.nama_lengkap, u.nim_nip, u.divisi_kamar
        FROM layanan_administrasi l
        JOIN users u ON l.user_id = u.id
        ORDER BY CASE WHEN l.status = 'Menunggu' THEN 0 ELSE 1 END, l.id DESC
    """).fetchall()

    # Ringkasan Statistik Cepat
    stats = {
        "total_mahasantri": len(mahasantri_list),
        "total_dokumen": len(dokumen_list),
        "total_absensi": len(absensi_list),
        "permohonan_menunggu": sum(1 for item in administrasi_list if item["status"] == "Menunggu"),
    }

    conn.close()
    return render_template(
        "admin_dashboard.html",
        mahasantri_list=mahasantri_list,
        dokumen_list=dokumen_list,
        absensi_list=absensi_list,
        administrasi_list=administrasi_list,
        stats=stats,
    )


@app.route("/admin/mahasantri/tambah", methods=["POST"])
@login_required(role="admin")
def tambah_mahasantri():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    nama_lengkap = request.form.get("nama_lengkap", "").strip()
    nim_nip = request.form.get("nim_nip", "").strip()
    divisi_kamar = request.form.get("divisi_kamar", "").strip()

    if not all([username, password, nama_lengkap, nim_nip, divisi_kamar]):
        flash("Seluruh kolom data Mahasantri wajib diisi.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO users (username, password, nama_lengkap, role, nim_nip, divisi_kamar, status_aktif)
            VALUES (?, ?, ?, 'mahasantri', ?, ?, 'Aktif')
            """,
            (username, generate_password_hash(password), nama_lengkap, nim_nip, divisi_kamar),
        )
        conn.commit()
        flash(f"Akun Mahasantri {nama_lengkap} berhasil ditambahkan.", "success")
    except Exception:
        flash("Username sudah terdaftar. Gunakan username lain.", "error")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/mahasantri/hapus/<int:user_id>", methods=["POST"])
@login_required(role="admin")
def hapus_mahasantri(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ? AND role = 'mahasantri'", (user_id,))
    conn.commit()
    conn.close()
    flash("Data Mahasantri berhasil dihapus dari sistem.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/digital/tambah", methods=["POST"])
@login_required(role="admin")
def tambah_data_digital():
    judul = request.form.get("judul", "").strip()
    kategori = request.form.get("kategori", "").strip()
    isi_ringkas = request.form.get("isi_ringkas", "").strip()

    if not all([judul, kategori, isi_ringkas]):
        flash("Lengkapi judul, kategori, dan isi informasi digital.", "error")
        return redirect(url_for("admin_dashboard"))

    kode_dokumen = f"DOC-{datetime.now().strftime('%y%m')}-{random.randint(10, 99)}"
    tanggal_terbit = datetime.now().strftime("%Y-%m-%d")
    penulis = session.get("nama_lengkap", "Admin Yayasan")

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO data_digital (kode_dokumen, judul, kategori, isi_ringkas, tanggal_terbit, penulis)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (kode_dokumen, judul, kategori, isi_ringkas, tanggal_terbit, penulis),
    )
    conn.commit()
    conn.close()

    flash(f"Dokumen digital {kode_dokumen} berhasil dipublikasikan.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/digital/hapus/<int:doc_id>", methods=["POST"])
@login_required(role="admin")
def hapus_data_digital(doc_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM data_digital WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    flash("Dokumen digital berhasil dihapus.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/administrasi/proses/<int:req_id>", methods=["POST"])
@login_required(role="admin")
def proses_administrasi(req_id):
    status = request.form.get("status", "Menunggu")
    catatan_admin = request.form.get("catatan_admin", "").strip() or "Telah diverifikasi oleh Admin."

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE layanan_administrasi
        SET status = ?, catatan_admin = ?
        WHERE id = ?
        """,
        (status, catatan_admin, req_id),
    )
    conn.commit()
    conn.close()

    flash(f"Status permohonan administrasi berhasil diperbarui menjadi {status}.", "success")
    return redirect(url_for("admin_dashboard"))


# ==========================================
# ROUTES MAHASANTRI: PORTAL OPERASIONAL & LAYANAN
# ==========================================

@app.route("/mahasantri")
@login_required(role="mahasantri")
def mahasantri_dashboard():
    user_id = session["user_id"]
    conn = get_db_connection()

    dokumen_list = conn.execute(
        "SELECT * FROM data_digital ORDER BY id DESC"
    ).fetchall()

    absensi_saya = conn.execute(
        "SELECT * FROM operasional_absensi WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()

    layanan_saya = conn.execute(
        "SELECT * FROM layanan_administrasi WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()

    conn.close()
    return render_template(
        "mahasantri_dashboard.html",
        dokumen_list=dokumen_list,
        absensi_saya=absensi_saya,
        layanan_saya=layanan_saya,
    )


@app.route("/mahasantri/absen", methods=["POST"])
@login_required(role="mahasantri")
def mahasantri_absen():
    kegiatan = request.form.get("kegiatan", "").strip()
    status_kehadiran = request.form.get("status_kehadiran", "Hadir").strip()

    if not kegiatan:
        flash("Pilih kegiatan operasional terlebih dahulu.", "error")
        return redirect(url_for("mahasantri_dashboard"))

    now = datetime.now()
    tanggal = now.strftime("%Y-%m-%d")
    waktu_checkin = now.strftime("%H:%M:%S")

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO operasional_absensi (user_id, kegiatan, tanggal, waktu_checkin, status_kehadiran)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session["user_id"], kegiatan, tanggal, waktu_checkin, status_kehadiran),
    )
    conn.commit()
    conn.close()

    flash(f"Presensi kegiatan '{kegiatan}' berhasil tercatat pada {waktu_checkin}.", "success")
    return redirect(url_for("mahasantri_dashboard"))


@app.route("/mahasantri/administrasi/ajukan", methods=["POST"])
@login_required(role="mahasantri")
def ajukan_administrasi():
    jenis_layanan = request.form.get("jenis_layanan", "").strip()
    keperluan = request.form.get("keperluan", "").strip()

    if not all([jenis_layanan, keperluan]):
        flash("Jenis layanan dan rincian keperluan wajib diisi.", "error")
        return redirect(url_for("mahasantri_dashboard"))

    kode_tiket = f"ADM-{datetime.now().strftime('%y%m')}-{random.randint(100, 999)}"
    tanggal_pengajuan = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO layanan_administrasi (kode_tiket, user_id, jenis_layanan, keperluan, tanggal_pengajuan)
        VALUES (?, ?, ?, ?, ?)
        """,
        (kode_tiket, session["user_id"], jenis_layanan, keperluan, tanggal_pengajuan),
    )
    conn.commit()
    conn.close()

    flash(f"Permohonan administrasi dengan nomor tiket {kode_tiket} berhasil dikirim.", "success")
    return redirect(url_for("mahasantri_dashboard"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)