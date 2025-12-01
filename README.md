# 🛒 Smart Mart - AI Self Checkout System

Sistem kasir cerdas berbasis **Artificial Intelligence (Computer Vision)** yang memungkinkan pelanggan melakukan *self-checkout* menggunakan kamera HP atau Webcam. Terintegrasi dengan Dashboard Admin untuk manajemen stok dan laporan keuangan real-time.

## 🚀 Fitur Utama
* **AI Object Detection:** Mendeteksi produk (Indomie, Teh Botol, dll) secara otomatis menggunakan model CNN MobileNetV2.
* **Hybrid Checkout:** Pelanggan scan sendiri, pembayaran dikonfirmasi Admin (Tunai/Debit) atau otomatis (QRIS).
* **Dual Interface:**
    * **Kiosk Mode (HP):** Scanner responsif untuk pelanggan.
    * **Admin Console (Laptop):** Dashboard antrian bayar, stok, dan laporan.
* **Real-time Database:** Stok berkurang otomatis & pencatatan omzet harian.
* **Voice Assistant:** Feedback suara saat produk terdeteksi.

## 🛠️ Teknologi yang Digunakan
* **Backend:** Python Flask, SocketIO (WebSocket).
* **AI Engine:** TensorFlow/Keras (MobileNetV2 Transfer Learning).
* **Database:** SQLite (SQLAlchemy).
* **Frontend:** HTML5, Tailwind CSS, JavaScript.

## 📂 Struktur Project
* `app.py`: Main backend logic.
* `best_checkout_model.h5`: Model AI yang sudah dilatih.
* `training_model.ipynb`: Source code pelatihan model (Google Colab).
* `templates/`: File HTML (Dashboard, Scanner, Inventory).

## 📦 Cara Menjalankan
1.  Clone repository ini.
2.  Install library: `pip install -r requirements.txt`
3.  Jalankan aplikasi: `python app.py`
4.  Akses Admin: `localhost:5000` (User: `admin` / Pass: `admin`)
5.  Akses Kasir: `localhost:5000` (User: `kasir` / Pass: `kasir`)

---
Dibuat untuk Tugas Akhir / Proyek Pribadi.