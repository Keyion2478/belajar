# 01. Product Requirements Document (PRD)
**Proyek:** Rclone Drive Manager (Desktop GUI)  
**Target Platform:** Windows 10 & 11 (64-bit)  
**Status:** Draft / Review  
**Versi:** 1.0.0  
**Penulis:** Senior Product Manager (Virtual Team)

---

## 1. Overview & Background
Banyak pengguna memanfaatkan integrasi cloud storage (khususnya Google Drive) untuk memperluas penyimpanan lokal dengan bantuan utilitas open-source populer **Rclone** dan **WinFsp**. Salah satu fitur paling dicari adalah **Rclone Union**, yaitu menggabungkan beberapa akun Google Drive terpisah (misalnya beberapa akun 15 GB atau akun institusi) menjadi satu "drive virtual raksasa" yang dipasang (*mount*) langsung ke Windows Explorer layaknya partisi harddisk lokal.

Namun, alur instalasi saat ini sangat manual:
- Mengharuskan pengguna mengutak-atik Command Prompt / PowerShell CLI.
- Menulis script VBScript secara manual untuk menjalankan proses secara *silent/hidden*.
- Menyiapkan Windows Task Scheduler secara manual.
- Rawan terjadi kesalahan manusia (*human error*), seperti salah meletakkan tanda petik, salah path direktori (typo path config/cache), token OAuth yang *expired* tanpa notifikasi jelas, dan bahaya disk C: kehabisan ruang akibat cache VFS yang terlalu besar.

**Rclone Drive Manager** hadir sebagai aplikasi antarmuka grafis (Desktop GUI) yang mempermudah, mengotomatisasi, dan mengamankan seluruh alur kerja tersebut dalam bentuk antarmuka visual yang modern dan intuitif.

---

## 2. Problem Statement
1. **Kerumitan Teknis CLI & Scripting:** Pengguna non-teknis kesulitan mengonfigurasi `rclone.conf`, membuat VBScript wrapper, dan mengatur Task Scheduler.
2. **Resiko Typo Fatal:** Kesalahan satu huruf pada path konfigurasi (contoh: `LC:\...` bukannya `C:\...`) membuat mount gagal total tanpa pesan kesalahan visual yang ramah.
3. **Visibilitas Status Akun Rendah:** Saat token OAuth Google kadaluwarsa (Error 401: Invalid Credentials), pengguna tidak mengetahui akun mana yang bermasalah dan mengira aplikasi atau sistem rusak.
4. **Resiko Kepenuhan Disk C: (Disk Overflow Hazard):** Parameter `--vfs-cache-dir` sering kali secara default mengarah ke drive sistem C:. Jika drive C: sekarat (< 5 GB) dan user menyetel cache 20 GB, Windows rentan mengalami freeze/crash.

---

## 3. Goals & Success Metrics

### A. Goals
* Menyediakan antarmuka GUI modern (Windows 11 dark/light aesthetic) untuk mengelola akun Rclone, membuat Union Drive, dan melakukan Mount hanya dengan beberapa klik.
* Menghilangkan kebutuhan menulis/mengedit script `.vbs` dan konfigurasi manual Task Scheduler oleh pengguna.
* Menyediakan deteksi kesehatan koneksi akun (Token Health Check) secara visual beserta tombol 1-klik Reconnect.
* Menyediakan proteksi kapasitas disk cache lokal sebelum mount dijalankan.

### B. Success Metrics (KPI)
* **Zero Scripting:** 100% alur (Add Account -> Create Union -> Mount -> Auto-start) dapat diselesaikan via antarmuka grafis.
* **Error Prevention:** Mencegah 100% kesalahan typo path konfigurasi melalui auto-discovery internal.
* **Mount Success Rate:** Pengguna dapat memvalidasi semua upstream sebelum proses mount dieksekusi.

### C. Non-Goals (Batasan Tegas)
* Aplikasi **TIDAK** menggantikan binary Rclone dengan kode custom protokol Google Drive; aplikasi tetap bertindak sebagai manager/orchestrator resmi di atas Rclone binary & WinFsp.
* Aplikasi pada rilis v1.0 **TIDAK** mendukung penyedia cloud selain Google Drive & Union (Dropbox, OneDrive, S3 direncanakan pada rilis mendatang).

---

## 4. User Personas & Use Cases

### Persona Utama: "Siswa/Mahasiswa & Content Creator Mandiri"
* **Karakteristik:** Memiliki beberapa akun Google Drive (akun pribadi, akun sekolah/kuliah) dan membutuhkan penyimpanan lokal besar untuk menyimpan bahan belajar, video footage, atau arsip proyek tanpa mengorbankan SSD internal yang sempit.
* **Tingkat Keahlian:** Mengerti cara download dan install software, tetapi tidak terbiasa dengan scripting Windows atau terminal CLI.

---

## 5. User Stories (Wajib ID)

| ID User Story | Sebagai | Saya Ingin | Agar |
|---|---|---|---|
| `US-001` | Pengguna | Melihat status deteksi otomatis Rclone dan WinFsp di sistem | Saya tahu apakah komputer saya sudah siap digunakan atau perlu instalasi tambahan |
| `US-002` | Pengguna | Melihat daftar akun Google Drive yang terhubung beserta sisa kuota dan status kesehatannya (Aktif vs Expired) | Saya langsung tahu jika ada akun yang token login-nya mati tanpa harus membaca log teknis |
| `US-003` | Pengguna | Menghubungkan akun Google Drive baru melalui tombol visual yang membuka browser otomatis | Saya tidak perlu membuka terminal untuk menjalankan `rclone config` manual |
| `US-004` | Pengguna | Melakukan re-otentikasi (reconnect) akun yang expired dengan satu kali klik | Akses ke cloud saya pulih kembali dengan cepat |
| `US-005` | Pengguna | Memilih dan mencentang akun-akun mana saja yang ingin digabung ke dalam Union Pool | Saya memiliki satu virtual drive gabungan sesuai kapasitas yang saya inginkan |
| `US-006` | Pengguna | Memilih huruf drive lokal (misal G:, Z:), nama volume, dan folder cache lokal yang aman | Drive virtual muncul di Windows Explorer sesuai preferensi tanpa membuat drive C: penuh |
| `US-007` | Pengguna | Menjalankan (Mount) dan Menghentikan (Unmount) drive virtual secara instan via tombol GUI | Saya memegang kontrol penuh kapan drive aktif dan tidak aktif |
| `US-008` | Pengguna | Mengaktifkan/menonaktifkan fitur "Auto-Mount on Windows Startup" dengan satu toggle switch | Drive otomatis terpasang setiap kali PC dinyalakan tanpa repot membuka Task Scheduler |
| `US-009` | Pengguna | Membaca riwayat log aktivitas Rclone dalam panel log yang bersih | Saya dapat mendiagnosis masalah jika terjadi kendala jaringan |

---

## 6. Requirement Priority (MoSCoW)

* **Must Have (Kritis untuk MVP):**
  - `US-001`: Environment health check (Deteksi binary rclone.exe & WinFsp).
  - `US-002`: Account listing & status check (Quota & Token validity).
  - `US-003`: Tombol Add Google Drive account via OAuth browser flow.
  - `US-004`: Tombol Reconnect token expired.
  - `US-005`: Konfigurator Union Drive (pilih upstream remotes).
  - `US-006`: Parameter Mount & proteksi kapasitas cache disk.
  - `US-007`: Start Mount / Stop Unmount process controller.
* **Should Have:**
  - `US-008`: Windows Startup toggle (via Registry Run key atau Scheduled Task API).
  - `US-009`: Live log viewer dengan filter level log.
* **Could Have:**
  - Custom bandwidth speed limiter slider.
  - Desktop Tray Icon (minimize to tray).
* **Won't Have (v1.0):**
  - Sinkronisasi multi-cloud provider di luar Google Drive.

---

## 7. Scope & Out-of-Scope

* **In Scope:**
  - Aplikasi GUI Windows berbasis Python (CustomTkinter).
  - Pengelolaan konfigurasi `rclone.conf` secara aman tanpa merusak konfigurasi lain.
  - Eksekusi background process Rclone secara asynchronous & non-blocking.
  - Dukungan build standalone single `.exe` (via PyInstaller).
* **Out of Scope:**
  - Versi macOS atau Linux (fokus Windows WinFsp).
  - Modifikasi driver level rendah pada WinFsp.

---

## 8. Assumptions & Constraints
* `[ASUMSI]` Pengguna memiliki hak akses standar pada sistem Windows (admin privilege hanya dibutuhkan saat instalasi driver WinFsp jika belum ada).
* `[ASUMSI]` Akun Google Drive yang digunakan adalah akun legal pribadi atau institusi dengan izin OAuth standar.
* **Constraint:** Rclone memerlukan koneksi internet aktif untuk me-refresh token Google.
* **Constraint:** Driver WinFsp wajib terpasang agar proses mount virtual drive Windows dapat terjadi.

---

## 9. Risks & Mitigation

| Risiko | Dampak | Mitigasi Teknis |
|---|---|---|
| Salah satu token akun dalam Union expired | Drive union gagal di-mount | GUI melakukan pre-flight validation terhadap seluruh akun upstream sebelum mount dipanggil |
| Drive C: kehabisan ruang akibat cache VFS | Windows freeze/crash | GUI memeriksa sisa kapasitas drive target cache. Beri peringatan merah jika sisa disk < kuota cache |
| Huruf drive bentrok dengan drive fisik/flashdisk | Mount gagal | GUI otomatis mendeteksi huruf drive yang sedang dipakai (`Get-PSDrive`) dan hanya menyajikan huruf yang kosong |
| Proses Rclone menggantung saat aplikasi ditutup | Drive terkunci / error unmount | Terapkan graceful termination (`SIGTERM` / `taskkill`) saat aplikasi ditutup atau unmount dipicu |

---

## 10. Timeline & High-level Milestones
* **Fase 1:** Dokumentasi Lengkap & Arsitektur (PRD -> SRS -> SDD -> UI/UX -> Task Breakdown).
* **Fase 2:** Core Engine (Rclone Wrapper, Config Parser, Health Check, Process Manager).
* **Fase 3:** Antarmuka GUI (CustomTkinter: Dashboard, Account Manager, Mount Controller, Log Viewer).
* **Fase 4:** Integrasi, Startup Service, & Uji Coba Lapangan di Lingkungan Asli.
* **Fase 5:** Packaging Portable Single `.exe`.
