# 🌸 Drive-Chan: Rclone Google Drive Union Manager

Aplikasi GUI Desktop modern untuk Windows untuk mengelola, menggabungkan (*Union*), dan memasang (*Mount*) multi-akun Google Drive ke Windows Explorer secara otomatis tanpa repot menyentuh terminal CLI atau mengedit script VBScript manual.

---

## 🌟 Fitur Utama

1. **Dashboard Satu Klik (Mount / Unmount):**
   * Pasang dan lepas virtual drive Google Drive ke Windows Explorer secara instan.
   * Langsung buka virtual drive di File Explorer dengan tombol visual.
   * Indikator status mount real-time.

2. **Manajemen Akun Google Drive & Health Check:**
   * Deteksi otomatis semua akun Google Drive yang tersimpan di `rclone.conf`.
   * Menampilkan kapasitas kuota (Total, Digunakan, Sisa) per akun.
   * Indikator visual hijau/merah jika token OAuth kadaluwarsa (*Invalid Credentials*).
   * **Tombol 1-Klik Reconnect / Login Ulang** tanpa harus mengetik perintah CLI.
   * Tambah akun Google Drive baru langsung lewat alur browser visual.

3. **Union Pool Builder & Prioritas Pengisian Akun:**
   * **Pilihan Strategi Pengisian (Create Policy):**
     * ⬇️ *Isi Berurutan dari Atas ke Bawah (`epff`)*: Akun #1 diisi terus sampai penuh, baru beralih ke Akun #2, Akun #3, dst.
     * ⚖️ *Ratakan ke Akun Paling Kosong (`epmfs`)*: File otomatis disebar ke akun yang paling longgar kuotanya.
     * 📦 *Habiskan Akun Paling Penuh Dulu (`eplfs`)*: Prioritaskan menghabiskan akun yang tersisa sedikit.
   * **Tombol Urutan Prioritas (⬆️ Naik / ⬇️ Turun):**
     * Kamu bisa menaik-turunkan posisi akun (misal: taruh akun 15 GB di Prioritas #1 dan #2, akun 400 GB di #3, dan akun 5 TB di urutan bawah).
   * Tombol uji validitas gabungan otomatis menyimpan sebelum pengujian.

4. **Pengaturan Mount & Proteksi Disk Cache:**
   * Pilih huruf drive lokal (Drive Letter) yang masih kosong (otomatis mendeteksi huruf yang belum dipakai).
   * Kustomisasi nama label volume (misal: `Drive-Chan >//<`).
   * **Proteksi Disk C:** Dilengkapi meteran sisa ruang disk target cache dengan peringatan warna merah jika drive target hampir penuh, mencegah Windows crash akibat cache VFS yang meluap.

5. **Otomatisasi Booting Windows (Auto-Start):**
   * Cukup aktifkan switch **"Jalankan Otomatis saat Windows Booting"**.
   * Aplikasi otomatis membuat pemicu silent di folder Startup Windows tanpa perlu membuka Task Scheduler manual.

6. **Log Viewer Real-time:**
   * Tinjau aktivitas dan riwayat error rclone langsung dari dalam aplikasi.

7. **Monitor Transfer & Sinkronisasi Real-time:**
   * **Live Upload Progress:** Dilengkapi tab **"📤 Monitor Transfer"** dan banner live di Dashboard yang menampilkan:
     * Nama file yang sedang diunggah dari cache lokal ke Google Drive.
     * Persentase progress bar visual (0% - 100%).
     * Ukuran terkirim / total (misal `500 MB / 1.38 GB`).
     * Kecepatan unggah langsung (`⚡ X MB/s`) dan estimasi waktu sisa (`⏳ ETA`).

8. **Zona Upload Cepat & Drag & Drop Anti-Freeze:**
   * **Bebas Not Responding:** Ketika menyalin atau menyeret (*drag & drop*) file/folder besar langsung ke jendela aplikasi Drive-Chan, file disalin di latar belakang menggunakan streaming buffer 4MB tanpa membebani Windows Explorer.
   * **Pilihan File & Folder:** Tersedia tombol visual `📄 Pilih File` dan `📁 Pilih Folder`.
   * **Pemilihan Subfolder Tujuan:** Bisa menentukan folder target di dalam Drive-Chan sebelum menyalin.
   * File yang selesai disalin otomatis masuk antrean unggah VFS Cache ke Google Drive.

---

## 🚀 Cara Menjalankan Aplikasi

### Opsi 1: Menjalankan Langsung via Script Batch
Cukup klik ganda file:
```
run.bat
```

### Opsi 2: Menjalankan via Terminal
Pastikan Python sudah terpasang:
```bash
python main.py
```

---

## 📦 Cara Membangun File `.exe` Mandiri (Standalone)
Jika ingin membagikan aplikasi ini ke laptop lain tanpa perlu menginstal Python:
1. Klik ganda file:
   ```
   build_exe.bat
   ```
2. Tunggu proses PyInstaller selesai.
3. File executable akan siap di dalam folder:
   ```
   dist\DriveChanManager\DriveChanManager.exe
   ```
