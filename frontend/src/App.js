// App.js
import React, { useMemo, useRef, useState, useEffect } from "react";
import "./App.css";

export default function App() {
  const API_BASE = "http://127.0.0.1:8000";
  const DETECT_URL = `${API_BASE}/detect`;

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const [showCamera, setShowCamera] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const isMobile = useMemo(
    () => /Android|iPhone|iPad/i.test(navigator.userAgent),
    []
  );

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const setNewFile = (f) => {
    setError("");
    setResult(null);
    setFile(f || null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(f ? URL.createObjectURL(f) : "");
  };

  const onDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) setNewFile(f);
  };
  const onDragOver = (e) => e.preventDefault();

  const onSubmit = async (e) => {
  e.preventDefault();
  setError("");
  setResult(null);

  if (!file) return setError("Pilih gambar dulu.");

  setLoading(true);
  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(DETECT_URL, { method: "POST", body: formData });

    // kalau status code error (400/500) -> ambil pesan backend
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || "Request gagal");
    }

    const data = await res.json();

    // ✅ kalau backend bilang ok: false (misal bukan label gizi)
    if (!data.ok) {
      setError(data.message || "Gambar bukan label gizi / tabel gizi tidak terdeteksi.");
      setResult(null);
      return;
    }

    // ✅ sukses
    setResult(data);
  } catch (err) {
    setError(err?.message || "Terjadi kesalahan.");
  } finally {
    setLoading(false);
  }
};

  const resetAll = () => {
  setError("");
  setResult(null);
  setFile(null);

  if (preview) URL.revokeObjectURL(preview);
  setPreview("");

  const input = document.getElementById("fileInput");
  if (input) input.value = "";
};

  // ===== Kamera Desktop =====
  const openLaptopCamera = async () => {
    setError("");
    setShowCamera(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch (e) {
      setShowCamera(false);
      setError("Kamera tidak bisa diakses (izin ditolak / device tidak ada).");
    }
  };

  const closeLaptopCamera = () => {
    const v = videoRef.current;
    if (v?.srcObject) v.srcObject.getTracks().forEach((t) => t.stop());
    setShowCamera(false);
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");

    // mirror preview (optional)
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const f = new File([blob], "camera.jpg", { type: "image/jpeg" });
      setNewFile(f);
      closeLaptopCamera();
    }, "image/jpeg");
  };

  const scrollToChecker = () => {
    document.getElementById("cek-label")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="page">
      {/* TOPBAR */}
      <header className="topbar topbar-hero">
        <div className="topbar-inner">
          <div className="brand-wrap">
            <div className="logo-badge">
              <img src="/asset/nutriva.png" alt="Nutriva logo" />
            </div>
          </div>

          <nav className="nav">
            <a href="#beranda">BERANDA</a>
            <a href="#cek-label">CEK LABEL</a>
            <a href="#hasil">HASIL</a>
            <a href="#referensi">REFERENSI</a>
          </nav>
        </div>
      </header>

      {/* HERO (warna, bukan image) */}
      <section id="beranda" className="hero2">
        <div className="hero2-overlay" />
        <div className="hero2-inner">
          <h1 className="hero2-title">
            Nutriva
            <br />
            <span className="hero2-subtitle-text">
              Foto Labelnya, Pahami Isinya!
            </span>
          </h1>
          <p className="hero2-subtitle">Nutriva membantu mendeteksi dan membaca label makanan kemasan secara otomatis. Cukup unggah gambar, dan informasi gizi utama ditampilkan dengan jelas untuk mendukung pemilihan makan yang lebih bijak.</p><br></br>
          <button className="hero2-cta" onClick={scrollToChecker}>
            Cek Label Gizi
          </button>
        </div>
      </section>

      {/* ===== SECTION SEBELUM KAMERA DETEKSI (yang kamu maksud) ===== */}
      <section id="cek-label" className="checker-section">
  <div className="checker-inner">

    {(result || error) && (
      <button
        type="button"
        className="back-btn"
        onClick={resetAll}
        aria-label="Reset"
      >
        ←
      </button>
    )}
<br /><br /><br />
          <h2 className="checker-title">Cek Label Gizi</h2>
          <p className="checker-subtitle">
            Upload foto tabel gizi atau ambil langsung dari kamera.
          </p>

          <div className="checker-card">
            {(result || error) && (
    <button
      type="button"
      className="back-btn"
      onClick={resetAll}
      aria-label="Reset"
      title="Reset"
    >
      ←
    </button>
  )}
            <form onSubmit={onSubmit}>
              <div className="dropzone" onDrop={onDrop} onDragOver={onDragOver}>
                {preview ? (
                  <img className="preview" src={preview} alt="preview" />
                ) : (
                  <>
                    <label className="btn btn-green" htmlFor="fileInput">
                      Upload foto tabel
                    </label>
                    <div className="drop-hint">atau tarik ke sini</div>
                  </>
                )}

                <input
                  id="fileInput"
                  type="file"
                  accept="image/*"
                  onChange={(e) => setNewFile(e.target.files?.[0] || null)}
                  hidden
                />
              </div>

              <div className="or-text">atau</div>

              <div className="camera-row">
                {isMobile ? (
                  <>
                    <label className="btn btn-blue" htmlFor="cameraInput">
                      Foto dengan kamera
                    </label>
                    <input
                      id="cameraInput"
                      type="file"
                      accept="image/*"
                      capture="environment"
                      hidden
                      onChange={(e) => setNewFile(e.target.files?.[0] || null)}
                    />
                  </>
                ) : (
                  <button
                    type="button"
                    className="btn btn-blue"
                    onClick={openLaptopCamera}
                  >
                    Foto dengan kamera
                  </button>
                )}
              </div>

              <button className="btn btn-submit" type="submit" disabled={loading}>
                {loading ? "Memproses..." : "Deteksi"}
              </button>

              {error && <div className="alert alert-error">{error}</div>}
            </form>
          </div>
        </div>
      </section>

      {/* ===== HASIL VISUALISASI (CARD) ===== */}
<section id="hasil" className="viz-section">
  <div className="viz-inner">
    <h2 className="ref-title">Hasil</h2>
    <br />
    <div className="viz-grid">
      <MetricCard label="Energi Total" value={result?.nutrition?.energi_kkal} unit="kkal" />
      <MetricCard label="Lemak Total" value={result?.nutrition?.lemak_total_g} unit="gram" />
      <MetricCard label="Lemak Jenuh" value={result?.nutrition?.lemak_jenuh_g} unit="gram" />
      <MetricCard label="Protein" value={result?.nutrition?.protein_g} unit="gram" />
      <MetricCard label="Karbohidrat" value={result?.nutrition?.karbohidrat_g} unit="gram" />
      <MetricCard label="Garam" value={result?.nutrition?.garam_mg} unit="miligram" />
    </div>
  </div>
</section>

      {/* REFERENSI */}
    <section id="referensi" className="ref-section">
      <br /><br /><br />
      <div className="ref-inner">
        {/* Kiri: teks */}
        <div className="ref-left">
          <h2 className="ref-title">Referensi</h2>

          {/* <p className="ref-text">
            <b>Takaran saji.</b> Satu sendok makan gula setara dengan 12,5 gram, satu
            sendok teh garam setara dengan 2000 mg, dan satu sendok makan lemak
            setara dengan 13,4 gram. Takaran ini digunakan untuk memudahkan
            pemahaman jumlah kandungan dalam makanan berdasarkan ukuran rumah tangga
            sehari-hari.
          </p> */}

          <p className="ref-text">
            <b>Kalori dan Protein dalam makanan/minuman.</b> Referensi nilai kalori
            dan protein pada makanan/minuman diambil dari daftar konversi zat gizi
            berdasarkan hasil Susenas Maret 2024 oleh Badan Pusat Statistik.{" "}
            <a
              className="ref-link"
              href="https://web-api.bps.go.id/download.php?f=zTS62PYRRKN23dg2oD9J2y93SEVYT1NEd2o0OHcvb0lyWnVXM2VKODFPdFpmSk44MU5Ua1k4STBYM0dDN2E4cFVmY0pKUUlCeXByMDhCVThOSDAwSTY0Y0E4YytHOE45ZGhHM1ZoT1pTVTZrbUF6aUdiWWdUTG53L2RQUytxTkhJd0M2aktYenNOdlUyYUovUVd2dExibi9xcDFwYWpQeU85ZjZzbjFZRGlIS3hZY2htMEQxdDZ4NjBteTN2NVFPemxlQzRzWlZXOUcwSlVXSHRuVFhGR3NyenBkZWsweDA4OGluaW45Y005bVRSaTZiSHRjQkdXMk4xc09KNU1xQStPMzFVN2JwWE9UOUQ1Wkt5VGFCYnlSTm8yeGZQcm5jcHNjRFEzVC9HQ0Nua2drdEx0d1lUYS81dDFOdXRzQU02Q3pSc2c0dnZKYkNlQ0wv&_gl=1*1hnqbo0*_ga*OTAxMzAyOTQwLjE3NjcyNTU0NjM.*_ga_XXTTVXWHDB*czE3NjcyNTU0NjIkbzEkZzAkdDE3NjcyNTU0NjIkajYwJGwwJGgw"
              target="_blank"
              rel="noopener noreferrer"
            >
              lihat disini
            </a>
          </p>
        </div>

        {/* Kanan: card gambar */}
        <div className="ref-card">
          <p className="ref-card-title">
            <b>Angka Kecukupan Gizi Harian.</b>
          </p>

          <img
            src="/asset/akg.png"
            alt="AKG"
            className="ref-img"
          />
        </div>
      </div>
    </section>

      {/* MODAL KAMERA - TANPA KOTAK PUTIH */}
      {showCamera && (
        <div className="cam-backdrop" onClick={closeLaptopCamera}>
          <div className="cam-wrap" onClick={(e) => e.stopPropagation()}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="cam-video"
              style={{ transform: "scaleX(-1)" }}
            />
            <canvas ref={canvasRef} hidden />

            <div className="cam-actions">
              <button className="btn btn-green" type="button" onClick={capturePhoto}>
                Ambil Foto
              </button>
              <button className="btn btn-ghost" type="button" onClick={closeLaptopCamera}>
                Batal
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="footer">
        <div className="footer-inner footer-center">
          <img
            src="/asset/nutriva.png"
            alt="Nutriva"
            className="footer-logo"
          />
        </div>
      </footer>
    </div>
  );
}

function MetricCard({ label, value, unit }) {
  const num = value === null || value === undefined ? 0 : Number(value);
  const display = Number.isFinite(num) ? (Number.isInteger(num) ? num : num.toFixed(1)) : 0;

  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{display}</div>
      <div className="metric-unit">{unit}</div>
    </div>
  );
}