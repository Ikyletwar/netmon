# Network Monitor

A minimal, terminal-first network scanner that reveals every active device on your local network — no cloud, no tracking, no browser sandbox limits. Runs as a local Python web service on Linux and streams results live to a clean dashboard.

Built for one purpose: **see who is on your network, right now.**

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Features](#features)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Security Notes](#security-notes)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Author](#author)

---

## Why This Exists

Every "network scanner" app on the internet wants you to sign up, run it in the cloud, or install a bloated GUI. This project does the opposite:

- **Runs entirely on your laptop.** No external servers, no accounts.
- **One folder, four files.** Easy to read, easy to audit, easy to modify.
- **Terminal-native setup.** Copy, paste, run. No IDE, no project manager.
- **Live dashboard.** WebSocket pushes results the moment a scan finishes.
- **Minimal.** No framework overhead, no build step, no `node_modules`.

The dashboard is not the product. The **scan** is the product. The dashboard just makes it readable.

---

## Features

- **ARP-based device discovery** across the local `/24` subnet — fast, Layer-2 accurate.
- **Automatic subnet detection** from the laptop's active interface.
- **Real-time updates** via WebSocket — no page reload needed.
- **Automatic periodic rescans** every 30 seconds (configurable).
- **Manual "Scan Now" trigger** from the dashboard.
- **Hostname resolution** for each detected device (reverse DNS, best-effort).
- **MAC address capture** for device identification.
- **Local + public IP display** for context.
- **Dark / light mode** toggle, remembered across sessions.
- **Responsive layout** — usable on phone (same Wi-Fi) or desktop.
- **Fallback to `nmap`** if `scapy` cannot run (e.g. missing permissions).
- **Zero frontend dependencies** — no React, no Tailwind CDN, no build step.

---

## How It Works

```
┌──────────────────────────────────────────────────────┐
│  LAPTOP (running server.py)                          │
│                                                      │
│  ┌────────────┐   WebSocket   ┌───────────────────┐  │
│  │  Browser   │◄─────────────►│  FastAPI server   │  │
│  │ (index.html│               │  ├─ scan_loop()   │  │
│  │  + inline  │   HTTP GET    │  ├─ scanner.py    │  │
│  │  JS + CSS) │◄─────────────►│  └─ local_info.py │  │
│  └────────────┘               └─────────┬─────────┘  │
│                                         │            │
└─────────────────────────────────────────┼────────────┘
                                          │ ARP / ICMP
                                          ▼
                              ┌───────────────────────┐
                              │  Local Network        │
                              │  ├─ Device A          │
                              │  ├─ Device B          │
                              │  └─ ...               │
                              └───────────────────────┘
```

1. `server.py` starts a FastAPI app with a background scan loop.
2. Every `SCAN_INTERVAL` seconds, `scanner.py` sends an **ARP request** (`who-has`) to every address in the local `/24` subnet via `scapy`.
3. Every active device on the network replies with its **MAC address**.
4. The server collects replies, resolves hostnames (reverse DNS), and pushes the result to all connected dashboards via **WebSocket**.
5. The dashboard renders the table instantly — no polling, no refresh.

### Why ARP and not ICMP (ping)?

ARP works at **Layer 2**. It does not depend on the target device having ICMP enabled (many phones, IoT devices, and Windows machines block ping by default). Every device connected to a LAN *must* respond to ARP to communicate — otherwise it cannot talk to the router. So ARP sweep is more reliable than ping sweep for device discovery.

### Why not "just from the browser"?

Browsers run in a sandbox. JavaScript cannot open raw sockets, cannot send ARP, cannot scan LAN devices. Any "scanner" that claims to do this from pure browser is either using a public API (privacy risk) or lying. This project puts the scanner in the backend, where it belongs.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | Python 3.10+ | Runtime |
| Web framework | FastAPI | HTTP + WebSocket server |
| ASGI server | Uvicorn | Runs the app |
| Scanner | Scapy | ARP sweep (Layer 2) |
| Scanner fallback | nmap | ICMP sweep if Scapy fails |
| Network info | Python `socket`, `ipaddress` | Local IP + subnet |
| Frontend | Vanilla HTML / CSS / JS | Zero dependencies, zero build |

---

## Requirements

### Operating System

- **Linux** (tested on Debian/Ubuntu and Arch). Should also work on macOS; Windows support requires Npcap and is untested.

### Runtime

- **Python 3.10 or newer**
- **`sudo` access** — required for raw ARP packets (Scapy needs `CAP_NET_RAW`).

### System packages

- `python3`, `python3-pip`
- Optional but recommended: `nmap` (fallback scanner)

Install on Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-pip nmap
```

Install on Arch:

```bash
sudo pacman -S python python-pip nmap
```

---

## Installation

**One paste. Everything is created for you.**

Copy this into a terminal and press Enter. It creates `~/netmon`, writes all four files, and installs dependencies system-wide (no virtualenv).

```bash
mkdir -p ~/netmon && cd ~/netmon

# ... (paste the full installer block from the project's INSTALL section)
```

If you prefer to install manually, drop the four files into `~/netmon` and run:

```bash
sudo python3 -m pip install --break-system-packages scapy fastapi "uvicorn[standard]"
```

> **Note on `--break-system-packages`:** Debian 12+ and Ubuntu 23.04+ mark the system Python as "externally managed." This flag bypasses that guard for a user who explicitly wants system-wide installs. If you prefer a clean environment, use `pipx` or `pip install --user` instead — but then you must call the installed `uvicorn` with the right interpreter and `sudo` may lose it from `PATH`.

---

## Usage

```bash
cd ~/netmon
sudo python3 server.py
```

Then open:

```
http://localhost:8000
```

You will see:

- **Local IP** — the IP of the interface the scan uses
- **Public IP** — your internet-facing IP (fetched from `api.ipify.org`)
- **Subnet** — the detected subnet, e.g. `192.168.1.0/24`
- **Perangkat Aktif** — count of devices found in the last scan
- **Device table** — IP, MAC, hostname, status

The first scan starts automatically about 1 second after launch. Subsequent scans run every 30 seconds.

To stop the server: **Ctrl+C**.

To trigger a scan manually: click **Scan Now** on the dashboard.

---

## Project Structure

```
~/netmon/
├── server.py        # FastAPI app + WebSocket + scan loop
├── scanner.py       # ARP sweep (scapy) + nmap fallback
├── local_info.py    # Local IP + public IP helpers
├── index.html       # Dashboard (inline CSS + JS)
├── .gitignore       # Excludes __pycache__, *.db, venv
└── README.md        # This file
```

**Only four source files.** No `src/`, no `packages/`, no `dist/`. Every file is under 200 lines. Read them all in five minutes.

---

## Configuration

All config is via environment variables. No config file, no `.env` parser.

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_INTERVAL` | `30` | Seconds between automatic scans |
| `PORT` | `8000` | HTTP port for the server |

Example:

```bash
sudo SCAN_INTERVAL=10 PORT=9090 python3 server.py
```

If you need to force a specific subnet (e.g. auto-detect picks the wrong interface), edit `scanner.py` and change `get_local_subnet()` to return a hardcoded CIDR string.

---

## API Endpoints

The server exposes a small HTTP + WebSocket API. Useful if you want to script it or build your own frontend.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves `index.html` |
| `GET` | `/api/status` | Local IP, public IP, subnet, scan state |
| `GET` | `/api/devices` | Last scan results (list of devices) |
| `POST` | `/api/scan` | Trigger an immediate scan |
| `WS` | `/ws` | Real-time device updates |

### WebSocket message types

```json
{ "type": "init",         "devices": [...], "subnet": "192.168.1.0/24" }
{ "type": "scan_started" }
{ "type": "scan",         "devices": [...], "scanned_at": 1699999999 }
{ "type": "error",        "error": "Permission denied" }
```

Each device object:

```json
{
  "ip": "192.168.1.7",
  "mac": "a4:2b:8c:11:22:33",
  "hostname": "android-phone.lan"
}
```

---

## Security Notes

This project **only listens on your local machine** by default? No — it listens on `0.0.0.0:8000`, meaning **anything on your LAN can reach it**. Understand the trade-offs before exposing it:

- **No authentication.** Anyone on your network can open `http://<your-ip>:8000` and see the device list.
- **No TLS.** Plain HTTP. Do not use over the public internet.
- **No rate limiting.** A malicious local user could hammer `/api/scan`.
- **Requires `sudo`.** The server runs as root to send raw ARP. That is a real privilege escalation surface — audit `scanner.py` before running if that matters to you.

**Recommendations:**

1. Use only on trusted networks (home, private office).
2. If you must run it on a shared network, bind to `127.0.0.1` by editing `server.py` and replacing `host="0.0.0.0"` with `host="127.0.0.1"`.
3. Do not port-forward port 8000 on your router.
4. Do not commit `.db` files or environment-specific configs (the included `.gitignore` handles this).

---

## Limitations

ARP sweep is fast and reliable, but it is not magic. Know the boundaries:

| Limitation | Explanation |
|------------|-------------|
| **Single broadcast domain only** | ARP does not cross routers. Devices on other VLANs, subnets, or routed networks will not appear. |
| **Only active devices** | Devices that are asleep, powered off, or have Wi-Fi disabled will not respond. This is by design — the goal is "currently online." |
| **`/24` assumption** | Auto-detection assumes a `/24` subnet (254 hosts). If you use `/16` or `/22`, edit `scanner.py` and set the CIDR explicitly. |
| **Some AP isolation** | Guest Wi-Fi networks and "AP isolation" modes block device-to-device ARP on purpose. Devices will not be visible. |
| **Hostname may be blank** | Reverse DNS often fails on home networks. MAC address is the reliable identifier. |
| **No MAC vendor lookup** | The MAC is captured but the vendor (e.g. "Apple", "TP-Link") is not looked up — that would require an external API or an offline OUI database. |
| **Requires root** | Scapy needs raw socket access. `sudo` is not optional. |

---

## Troubleshooting

### `Permission denied` or empty device list

**Cause:** not running as root, or Scapy cannot open a raw socket.  
**Fix:**

```bash
sudo python3 server.py
```

### `scapy` not found after install

**Cause:** installed to user site, but `sudo python3` uses a different interpreter.  
**Fix:**

```bash
sudo python3 -m pip install --break-system-packages scapy
```

or install to the exact interpreter used by `sudo`:

```bash
which python3          # check path
sudo /usr/bin/python3 -m pip install scapy
```

### Dashboard shows `Terputus` / disconnected

**Cause:** WebSocket cannot reach the server — usually firewall or wrong host.  
**Fix:** check server logs; ensure you opened `http://localhost:8000` (not `https`); check `ufw`/`firewalld`.

### Wrong subnet detected (e.g. VPN interface)

**Cause:** you have multiple interfaces (VPN, Docker, Tailscale) and `get_local_subnet()` picked the wrong one.  
**Fix:** open `scanner.py`, replace `get_local_subnet()` body with a hardcoded CIDR:

```python
def get_local_subnet():
    return "192.168.1.0/24"
```

### `nmap` fallback runs every time (slow)

**Cause:** Scapy failed silently — usually a permission issue.  
**Fix:** check you are running as root; run `sudo python3 -c "from scapy.all import ARP; print('ok')"` to verify.

### Devices on Wi-Fi not visible

**Cause:** AP isolation / guest network. Some routers block client-to-client traffic.  
**Fix:** connect devices to the same non-isolated SSID, or use a wired switch.

---

## License

MIT — see `LICENSE` file if included, or use freely under MIT terms.

---

## Author

**Ikyletwar** — [github.com/Ikyletwar](https://github.com/Ikyletwar)

Built with the Azathoth code generation framework.

---

---

# Network Monitor (Bahasa Indonesia)

Pemindai jaringan minimalis berbasis terminal yang menampilkan **semua perangkat aktif** di jaringan lokalmu — tanpa cloud, tanpa tracking, tanpa batasan sandbox browser. Berjalan sebagai layanan web Python lokal di Linux dan mengalirkan hasil secara live ke dashboard yang bersih.

Dibuat untuk satu tujuan: **lihat siapa saja yang sedang terhubung ke jaringanmu, saat ini juga.**

---

## Daftar Isi

- [Kenapa Proyek Ini Ada](#kenapa-proyek-ini-ada)
- [Fitur](#fitur-1)
- [Cara Kerja](#cara-kerja-1)
- [Tech Stack](#tech-stack-1)
- [Kebutuhan Sistem](#kebutuhan-sistem-1)
- [Instalasi](#instalasi-1)
- [Penggunaan](#penggunaan-1)
- [Struktur Proyek](#struktur-proyek-1)
- [Konfigurasi](#konfigurasi-1)
- [Endpoint API](#endpoint-api-1)
- [Catatan Keamanan](#catatan-keamanan-1)
- [Batasan](#batasan-1)
- [Troubleshooting](#troubleshooting-1)
- [Lisensi](#lisensi-1)
- [Penulis](#penulis-1)

---

## Kenapa Proyek Ini Ada

Hampir semua "aplikasi pemindai jaringan" di internet minta kamu daftar, jalan di cloud, atau install GUI berat. Proyek ini kebalikannya:

- **Berjalan sepenuhnya di laptopmu.** Tidak ada server eksternal, tidak ada akun.
- **Satu folder, empat file.** Mudah dibaca, mudah diaudit, mudah dimodifikasi.
- **Setup ala terminal.** Copy, paste, jalankan. Tanpa IDE, tanpa project manager.
- **Dashboard live.** WebSocket mendorong hasil begitu scan selesai.
- **Minimalis.** Tanpa overhead framework, tanpa build step, tanpa `node_modules`.

Dashboard bukanlah produknya. **Scan**-nya yang jadi produk. Dashboard hanya membuatnya mudah dibaca.

---

## Fitur

- **Deteksi perangkat via ARP** di seluruh subnet `/24` lokal — cepat dan akurat di Layer 2.
- **Deteksi subnet otomatis** dari interface aktif laptop.
- **Update real-time** lewat WebSocket — tanpa reload halaman.
- **Scan berkala otomatis** setiap 30 detik (bisa diubah).
- **Tombol "Scan Now"** untuk trigger manual dari dashboard.
- **Resolusi hostname** untuk setiap perangkat terdeteksi (reverse DNS, best-effort).
- **Tangkap alamat MAC** untuk identifikasi perangkat.
- **Tampil IP lokal + publik** untuk konteks.
- **Mode gelap / terang** yang diingat antar sesi.
- **Layout responsif** — bisa dibuka dari HP (selama satu Wi-Fi) atau desktop.
- **Fallback ke `nmap`** kalau `scapy` gagal (misal izin kurang).
- **Nol dependency frontend** — tanpa React, tanpa Tailwind CDN, tanpa build step.

---

## Cara Kerja

```
┌──────────────────────────────────────────────────────┐
│  LAPTOP (menjalankan server.py)                      │
│                                                      │
│  ┌────────────┐   WebSocket   ┌───────────────────┐  │
│  │  Browser   │◄─────────────►│  Server FastAPI   │  │
│  │ (index.html│               │  ├─ scan_loop()   │  │
│  │  + inline  │   HTTP GET    │  ├─ scanner.py    │  │
│  │  JS + CSS) │◄─────────────►│  └─ local_info.py │  │
│  └────────────┘               └─────────┬─────────┘  │
│                                         │            │
└─────────────────────────────────────────┼────────────┘
                                          │ ARP / ICMP
                                          ▼
                              ┌───────────────────────┐
                              │  Jaringan Lokal       │
                              │  ├─ Perangkat A       │
                              │  ├─ Perangkat B       │
                              │  └─ ...               │
                              └───────────────────────┘
```

1. `server.py` menjalankan aplikasi FastAPI dengan loop scan di background.
2. Setiap `SCAN_INTERVAL` detik, `scanner.py` mengirim **ARP request** (`who-has`) ke seluruh alamat di subnet `/24` lokal via `scapy`.
3. Setiap perangkat aktif di jaringan membalas dengan **alamat MAC**-nya.
4. Server mengumpulkan balasan, me-resolve hostname (reverse DNS), dan mendorong hasilnya ke semua dashboard yang terhubung via **WebSocket**.
5. Dashboard langsung merender tabel — tanpa polling, tanpa refresh.

### Kenapa ARP, bukan ICMP (ping)?

ARP bekerja di **Layer 2**. Tidak bergantung pada perangkat target mengaktifkan ICMP (banyak HP, perangkat IoT, dan Windows memblokir ping secara default). Setiap perangkat yang terhubung ke LAN *wajib* membalas ARP untuk bisa berkomunikasi — kalau tidak, dia tidak bisa bicara dengan router. Jadi ARP sweep lebih andal daripada ping sweep untuk deteksi perangkat.

### Kenapa tidak "langsung dari browser"?

Browser berjalan di sandbox. JavaScript tidak bisa membuka raw socket, tidak bisa mengirim ARP, tidak bisa scan perangkat LAN. Aplikasi "scanner" apa pun yang mengklaim bisa dari browser murni itu entah pakai API publik (risiko privasi) atau bohong. Proyek ini menaruh scanner di backend, di tempat yang seharusnya.

---

## Tech Stack

| Layer | Teknologi | Fungsi |
|-------|-----------|--------|
| Backend | Python 3.10+ | Runtime |
| Web framework | FastAPI | Server HTTP + WebSocket |
| ASGI server | Uvicorn | Menjalankan app |
| Scanner | Scapy | ARP sweep (Layer 2) |
| Fallback scanner | nmap | ICMP sweep jika Scapy gagal |
| Info jaringan | Python `socket`, `ipaddress` | IP lokal + subnet |
| Frontend | HTML / CSS / JS murni | Nol dependency, nol build |

---

## Kebutuhan Sistem

### Sistem Operasi

- **Linux** (sudah dites di Debian/Ubuntu dan Arch). Harusnya juga jalan di macOS; dukungan Windows butuh Npcap dan belum dites.

### Runtime

- **Python 3.10 atau lebih baru**
- **Akses `sudo`** — dibutuhkan untuk paket ARP mentah (Scapy butuh `CAP_NET_RAW`).

### Paket sistem

- `python3`, `python3-pip`
- Opsional tapi disarankan: `nmap` (scanner fallback)

Install di Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-pip nmap
```

Install di Arch:

```bash
sudo pacman -S python python-pip nmap
```

---

## Instalasi

**Satu paste. Semua dibuat untukmu.**

Copy ini ke terminal lalu Enter. Script akan membuat `~/netmon`, menulis keempat file, dan menginstall dependency secara system-wide (tanpa virtualenv).

```bash
mkdir -p ~/netmon && cd ~/netmon

# ... (paste blok installer lengkap dari bagian INSTALL proyek)
```

Kalau mau install manual, taruh keempat file di `~/netmon` lalu jalankan:

```bash
sudo python3 -m pip install --break-system-packages scapy fastapi "uvicorn[standard]"
```

> **Catatan soal `--break-system-packages`:** Debian 12+ dan Ubuntu 23.04+ menandai Python sistem sebagai "externally managed". Flag ini melewati proteksi itu untuk user yang memang ingin install system-wide. Kalau kamu lebih suka environment bersih, pakai `pipx` atau `pip install --user` — tapi konsekuensinya, `uvicorn` yang terinstall harus dipanggil dengan interpreter yang tepat, dan `sudo` bisa saja tidak menemukannya di `PATH`.

---

## Penggunaan

```bash
cd ~/netmon
sudo python3 server.py
```

Lalu buka:

```
http://localhost:8000
```

Kamu akan melihat:

- **IP Lokal** — IP interface yang dipakai untuk scan
- **IP Publik** — IP internetmu (diambil dari `api.ipify.org`)
- **Subnet** — subnet terdeteksi, misal `192.168.1.0/24`
- **Perangkat Aktif** — jumlah perangkat di scan terakhir
- **Tabel perangkat** — IP, MAC, hostname, status

Scan pertama mulai otomatis sekitar 1 detik setelah launch. Scan berikutnya tiap 30 detik.

Untuk menghentikan server: **Ctrl+C**.

Untuk memicu scan manual: klik **Scan Now** di dashboard.

---

## Struktur Proyek

```
~/netmon/
├── server.py        # App FastAPI + WebSocket + loop scan
├── scanner.py       # ARP sweep (scapy) + fallback nmap
├── local_info.py    # Helper IP lokal + IP publik
├── index.html       # Dashboard (inline CSS + JS)
├── .gitignore       # Kecualikan __pycache__, *.db, venv
└── README.md        # File ini
```

**Hanya empat file sumber.** Tanpa `src/`, tanpa `packages/`, tanpa `dist/`. Setiap file di bawah 200 baris. Bisa dibaca semua dalam lima menit.

---

## Konfigurasi

Semua konfigurasi via environment variable. Tanpa file config, tanpa parser `.env`.

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `SCAN_INTERVAL` | `30` | Detik antar scan otomatis |
| `PORT` | `8000` | Port HTTP server |

Contoh:

```bash
sudo SCAN_INTERVAL=10 PORT=9090 python3 server.py
```

Kalau perlu paksa subnet tertentu (misal auto-detect salah pilih interface), edit `scanner.py` dan ubah `get_local_subnet()` agar mengembalikan string CIDR hardcoded.

---

## Endpoint API

Server mengekspos API HTTP + WebSocket kecil. Berguna kalau kamu mau scripting atau bikin frontend sendiri.

| Method | Path | Deskripsi |
|--------|------|-----------|
| `GET` | `/` | Menyajikan `index.html` |
| `GET` | `/api/status` | IP lokal, IP publik, subnet, status scan |
| `GET` | `/api/devices` | Hasil scan terakhir (list perangkat) |
| `POST` | `/api/scan` | Memicu scan segera |
| `WS` | `/ws` | Update perangkat real-time |

### Tipe pesan WebSocket

```json
{ "type": "init",         "devices": [...], "subnet": "192.168.1.0/24" }
{ "type": "scan_started" }
{ "type": "scan",         "devices": [...], "scanned_at": 1699999999 }
{ "type": "error",        "error": "Permission denied" }
```

Objek perangkat:

```json
{
  "ip": "192.168.1.7",
  "mac": "a4:2b:8c:11:22:33",
  "hostname": "android-phone.lan"
}
```

---

## Catatan Keamanan

Proyek ini **hanya listen di localhost**? Tidak — dia listen di `0.0.0.0:8000`, artinya **apa pun di LAN-mu bisa mengaksesnya**. Pahami trade-off sebelum mengeksposnya:

- **Tanpa autentikasi.** Siapa saja di jaringanmu bisa buka `http://<ip-kamu>:8000` dan lihat daftar perangkat.
- **Tanpa TLS.** HTTP polos. Jangan dipakai di internet publik.
- **Tanpa rate limiting.** User lokal jahat bisa nge-hammer `/api/scan`.
- **Butuh `sudo`.** Server berjalan sebagai root untuk mengirim ARP mentah. Itu adalah permukaan privilege escalation yang nyata — audit `scanner.py` sebelum menjalankan kalau itu penting bagimu.

**Rekomendasi:**

1. Gunakan hanya di jaringan tepercaya (rumah, kantor privat).
2. Kalau harus di jaringan bersama, bind ke `127.0.0.1` dengan mengedit `server.py` — ganti `host="0.0.0.0"` menjadi `host="127.0.0.1"`.
3. Jangan port-forward port 8000 di router.
4. Jangan commit file `.db` atau config khusus environment (`.gitignore` bawaan sudah menangani ini).

---

## Batasan

ARP sweep itu cepat dan andal, tapi bukan sihir. Kenali batasnya:

| Batasan | Penjelasan |
|---------|------------|
| **Hanya satu broadcast domain** | ARP tidak melewati router. Perangkat di VLAN, subnet, atau jaringan routed lain tidak akan muncul. |
| **Hanya perangkat aktif** | Perangkat yang tidur, mati, atau Wi-Fi-nya mati tidak akan membalas. Ini memang sesuai desain — tujuannya "sedang online". |
| **Asumsi `/24`** | Deteksi otomatis mengasumsikan subnet `/24` (254 host). Kalau kamu pakai `/16` atau `/22`, edit `scanner.py` dan set CIDR-nya eksplisit. |
| **Beberapa AP isolation** | Wi-Fi guest dan mode "AP isolation" memblokir ARP antar-client dengan sengaja. Perangkat tidak akan terlihat. |
| **Hostname bisa kosong** | Reverse DNS sering gagal di jaringan rumah. Alamat MAC adalah identifier yang andal. |
| **Tanpa lookup vendor MAC** | MAC ditangkap tapi vendor (misal "Apple", "TP-Link") tidak dicari — itu butuh API eksternal atau database OUI offline. |
| **Butuh root** | Scapy butuh akses raw socket. `sudo` bukan opsional. |

---

## Troubleshooting

### `Permission denied` atau daftar perangkat kosong

**Penyebab:** tidak jalan sebagai root, atau Scapy tidak bisa membuka raw socket.  
**Solusi:**

```bash
sudo python3 server.py
```

### `scapy` tidak ditemukan setelah install

**Penyebab:** terinstall ke user site, tapi `sudo python3` pakai interpreter lain.  
**Solusi:**

```bash
sudo python3 -m pip install --break-system-packages scapy
```

atau install ke interpreter yang sama dengan yang dipakai `sudo`:

```bash
which python3          # cek path
sudo /usr/bin/python3 -m pip install scapy
```

### Dashboard menampilkan `Terputus` / disconnected

**Penyebab:** WebSocket tidak bisa menjangkau server — biasanya firewall atau host salah.  
**Solusi:** cek log server; pastikan buka `http://localhost:8000` (bukan `https`); cek `ufw`/`firewalld`.

### Subnet terdeteksi salah (misal interface VPN)

**Penyebab:** kamu punya banyak interface (VPN, Docker, Tailscale) dan `get_local_subnet()` memilih yang salah.  
**Solusi:** buka `scanner.py`, ganti body `get_local_subnet()` dengan CIDR hardcoded:

```python
def get_local_subnet():
    return "192.168.1.0/24"
```

### Fallback `nmap` jalan terus (lambat)

**Penyebab:** Scapy gagal diam-diam — biasanya masalah izin.  
**Solusi:** pastikan jalan sebagai root; jalankan `sudo python3 -c "from scapy.all import ARP; print('ok')"` untuk verifikasi.

### Perangkat Wi-Fi tidak terlihat

**Penyebab:** AP isolation / guest network. Beberapa router memblokir trafik client-to-client.  
**Solusi:** hubungkan perangkat ke SSID yang sama dan tidak terisolasi, atau pakai switch kabel.

---

## Lisensi

MIT — lihat file `LICENSE` jika disertakan, atau gunakan bebas di bawah ketentuan MIT.

---

## Penulis

**Ikyletwar** — [github.com/Ikyletwar](https://github.com/Ikyletwar)

Dibangun dengan framework code generation Azathoth.
