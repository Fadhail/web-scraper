# API Contract - Web Scraper Agent (Joki Tugas AI)

Dokumentasi ini menjelaskan spesifikasi API Contract untuk **Web Scraper Agent** (Milik Fadel) yang diintegrasikan ke dalam platform Multi-Agent System **Joki Tugas AI**.

---

## 1. Informasi Umum
* **Tipe Agen**: `web_scraper`
* **Input Tipe**: `url`
* **Output Tipe**: `text`
* **Port Default**: `8000`
* **Protokol**: HTTP/1.1

### Aturan CORS & Keamanan
Sesuai panduan integrasi, agen ini menerapkan Cross-Origin Resource Sharing (CORS) dengan whitelist origin khusus untuk berkomunikasi dengan orkestrator sentral:
* **Allowed Origin**: `*`
* **Allowed Methods**: `POST`, `GET`, `OPTIONS`
* **Allowed Headers**: `*`

---

## 2. Spesifikasi Endpoint

### A. Healthcheck
Endpoint sederhana untuk memverifikasi apakah server agen sedang berjalan dan terhubung secara online.

* **URL**: `/`
* **Method**: `GET`
* **Response (HTTP 200 OK)**:
  ```json
  {
    "status": "online",
    "agent_type": "web_scraper",
    "owner": "fadel"
  }
  ```

---

### B. Pemrosesan Tugas Scraping
Endpoint utama untuk memicu tugas ekstraksi konten artikel/teks dari URL tertentu.

* **URL**: `/process`
* **Method**: `POST`
* **Headers**:
  * `Content-Type: application/json`

#### Request Body (JSON)
Orkestrator akan mengirimkan request JSON dengan struktur berikut:

```json
{
  "task_id": "req-12345-abc",
  "agent_type": "web_scraper",
  "payload": {
    "url": "",
    "keyword": "AI",
    "raw_text": "https://id.wikipedia.org/wiki/Kecerdasan_buatan"
  },
  "metadata": {
    "sender": "orchestrator",
    "timestamp": 1689694097
  }
}
```

> **Catatan Orkestrasi Baru**: Field `metadata` bersifat opsional dan diabaikan oleh agen. Agen akan secara otomatis mendeteksi target URL yang dikirimkan langsung melalui field `payload.raw_text`.

##### Penjelasan Parameter Request:
| Nama Field | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `task_id` | String | ID unik tugas dari pengguna. Wajib dikembalikan di dalam response secara persis. |
| `agent_type` | String | Harus bernilai `"web_scraper"`. |
| `payload` | Object | Menyimpan data parameter input tugas. |
| `payload.raw_text`| String | **(Prioritas Utama)** URL website target yang akan di-scrape. |
| `payload.url` | String | *(Alternatif/Opsional)* URL website target jika `raw_text` tidak diisi. |
| `payload.keyword` | String | *(Opsional)* Kata kunci pencarian jika dibutuhkan oleh agen. |
| `metadata` | Object | *(Opsional)* Informasi tambahan pengirim (dapat diabaikan). |

---

#### Response Sukses (HTTP 200 OK)
Jika proses scraping berhasil memilah konten utama dari URL target:

```json
{
  "status": "success",
  "task_id": "req-12345-abc",
  "data": {
    "result": "Kecerdasan buatan (artificial intelligence atau AI) adalah simulasi dari kecerdasan yang dimiliki oleh manusia yang dimodelkan di dalam mesin...",
    "file_url": null
  },
  "message": "Pemrosesan berhasil"
}
```

##### Penjelasan Parameter Response:
| Nama Field | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `status` | String | Bernilai `"success"`. |
| `task_id` | String | ID unik tugas yang dicocokkan secara persis dari request. |
| `data` | Object | Wrapper objek hasil proses. |
| `data.result` | String | Teks bersih hasil scraping (telah disaring dari tag script, style, header, nav, footer). |
| `data.file_url` | null | Selalu bernilai `null` karena agen ini hanya mengekstrak teks, bukan file fisik (seperti PDF/PPTX). |
| `message` | String | Pesan deskriptif hasil eksekusi agen. |

---

#### Response Gagal (HTTP 400 / 500)
Jika terjadi kesalahan validasi parameter input atau kegagalan saat menghubungi/memproses halaman web target:

```json
{
  "status": "error",
  "task_id": "req-12345-abc",
  "data": null,
  "message": "Error scraping the website: 404 Client Error: Not Found for url: https://contoh-salah.com"
}
```

##### Penjelasan Parameter Response:
| Nama Field | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `status` | String | Bernilai `"error"`. |
| `task_id` | String | ID unik tugas yang dicocokkan secara persis dari request (atau `"unknown"` jika request gagal diparsing). |
| `data` | null | Bernilai `null`. |
| `message` | String | Penjelasan rinci mengenai penyebab error. |

---

## 3. Logika Sirkuit Pintar (Type-Safe Smart Skip)
Orkestrator Joki Tugas AI memiliki mekanisme toleransi kegagalan (*Circuit Breaker*). Jika agen pendukung setelah `web_scraper` mati/offline, orkestrator akan memeriksa kecocokan tipe data input & output:
* **Output Web Scraper**: `text`
* Jika agen berikutnya (misalnya `typo_checker` atau `summarizer`) membutuhkan input tipe `text`, maka orkestrator akan melakukan *Smart Skip* (melewati agen yang mati tersebut dan langsung melempar teks hasil scraping ini ke agen berikutnya).
* Jika tipe data tidak cocok (misal agen berikutnya butuh `file` seperti `diagram_builder`), sistem orkestrator akan melakukan *Hard Stop* dan menetapkan status tugas menjadi `failed`.
