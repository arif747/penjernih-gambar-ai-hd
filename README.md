# Penjernih Gambar AI HD — deploy online

Aplikasi web responsif untuk HP. Pemrosesan gambar memakai model AI Real-ESRGAN melalui Replicate. File HTML tidak menyimpan token API; token hanya ada di environment variable server.

## Cara paling mudah: deploy ke Render

Anda perlu akun GitHub, akun Render, dan API token Replicate. Saya tidak dapat membuat akun, menerima token rahasia, atau menerbitkan situs ke akun Anda dari chat ini; langkah di bawah memublikasikannya dari akun Anda.

### A. Siapkan token AI
1. Buat/login akun di https://replicate.com/
2. Buat API token di pengaturan akun Replicate.
3. Simpan token secara rahasia. Jangan tempel token ke `index.html` atau unggah ke GitHub.

Periksa harga model/akun di Replicate sebelum digunakan; pemrosesan AI dapat berbayar.

### B. Upload proyek ke GitHub
1. Unduh ZIP ini dan ekstrak.
2. Buat repository baru di https://github.com/new (misalnya `penjernih-gambar-ai-hd`).
3. Upload file di dalam folder proyek ke repository. Pastikan `index.html`, `server.py`, `requirements.txt`, dan `render.yaml` ada di root repository. `Dockerfile` juga boleh disertakan.

### C. Deploy di Render
1. Buka https://render.com/ lalu daftar/login.
2. Pilih **New + → Web Service** dan hubungkan repository GitHub tadi.
3. Jika Render menawarkan Blueprint dari `render.yaml`, Anda bisa memilihnya. Jika membuat Web Service manual:
   - Runtime: **Python**
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Pada **Environment**, tambahkan:
   - Key: `REPLICATE_API_TOKEN`
   - Value: token Replicate Anda
5. Deploy dan tunggu sampai status layanan menjadi **Live**.
6. Buka URL Render yang diberikan, misalnya `https://nama-layanan.onrender.com`, di browser HP.

### D. Uji aplikasi
- Buka `/api/health` di URL hosting. `token_configured` harus `true`.
- Kembali ke halaman utama, pilih gambar, pilih 2× atau 4×, lalu tekan **Jernihkan dengan AI**.
- Jika API gagal, lihat pesan pada halaman dan log di dashboard Render.

## File proyek
- `index.html` — antarmuka HP, pilih gambar, bandingkan, unduh hasil.
- `server.py` — backend FastAPI yang memanggil Replicate dan tidak membocorkan token ke browser.
- `requirements.txt` — dependensi.
- `render.yaml` — konfigurasi deployment Render.
- `Dockerfile` — alternatif deploy di platform yang mendukung Docker.

## Catatan dan keamanan
- Situs belum diterbitkan otomatis: Anda harus masuk ke akun hosting dan memasukkan token rahasia.
- Model mengestimasi detail gambar; hasil tidak selalu memulihkan detail asli yang hilang.
- Foto yang dipilih dikirim ke penyedia AI untuk diproses. Hindari mengunggah foto sensitif dan periksa kebijakan privasi penyedia.
- Untuk aplikasi publik, tambahkan rate limiting/autentikasi dan pembatasan biaya. Template ini belum punya login pengguna atau kuota.
- Render free tier dapat tidur setelah tidak aktif dan mungkin memiliki batas sumber daya.
