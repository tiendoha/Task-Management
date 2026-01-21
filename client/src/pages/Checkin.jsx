import React, { useState, useRef, useEffect } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';

const Checkin = () => {
  const webcamRef = useRef(null);
  const isProcessingRef = useRef(false);

  // State quản lý
  const [logs, setLogs] = useState([]);
  const [msg, setMsg] = useState("Sẵn sàng...");
  const [isScanning, setIsScanning] = useState(false);
  const [scanIntervalId, setScanIntervalId] = useState(null);
  const [timeoutId, setTimeoutId] = useState(null);

  // Load lịch sử chấm công
  const fetchLogs = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:5000/api/logs');
      setLogs(res.data);
    } catch (e) { }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  // --- LOGIC DỪNG QUÉT ---
  const stopScanning = () => {
    setIsScanning(false);
    if (scanIntervalId) clearInterval(scanIntervalId);
    if (timeoutId) clearTimeout(timeoutId);
    setScanIntervalId(null);
    setTimeoutId(null);
    isProcessingRef.current = false;
  };

  // --- LOGIC GỬI ẢNH ĐI CHECKIN ---
  const performScan = async () => {
    // Nếu đang xử lý hoặc đã dừng quét thì không làm gì
    if (!webcamRef.current || isProcessingRef.current || !isScanning) return;

    isProcessingRef.current = true;
    const img = webcamRef.current.getScreenshot();

    try {
      const res = await axios.post('http://127.0.0.1:5000/api/checkin', { image: img });

      if (res.data.success) {
        stopScanning(); // Dừng ngay khi thành công
        setMsg(`✅ ${res.data.name} (${res.data.status})`);
        setLogs(prev => [
          { name: res.data.name, time: new Date().toLocaleTimeString(), status: res.data.status },
          ...prev
        ]);
        fetchLogs(); // Reload full log để chắc chắn
      } else {
        setMsg(`⏳ ${res.data.message}`);
        // Nếu thất bại (chưa nhận ra), đợi 2s rồi quét tiếp
        if (isScanning) {
          setTimeoutId(setTimeout(() => {
            isProcessingRef.current = false;
            performScan();
          }, 2000));
        }
      }
    } catch (e) {
      setMsg("❌ Lỗi kết nối Server");
      // Lỗi mạng, cũng đợi 3s rồi thử lại
      if (isScanning) {
        setTimeoutId(setTimeout(() => {
          isProcessingRef.current = false;
          performScan();
        }, 3000));
      }
    }
  };

  // --- LOGIC BẮT ĐẦU QUÉT TỰ ĐỘNG ---
  const startAutoScan = () => {
    if (isScanning) return;
    setIsScanning(true);
    setMsg("🔍 Đang tìm khuôn mặt...");
    isProcessingRef.current = false; // Reset khóa

    // Tự tắt sau 30s nếu không thấy ai
    setTimeoutId(setTimeout(() => { stopScanning(); setMsg("❌ Hết giờ! Không nhận diện được."); }, 30000));

    // Bắt đầu vòng lặp
    setTimeout(() => performScan(), 500);
  };

  // Dọn dẹp khi rời trang
  useEffect(() => {
    return () => stopScanning();
  }, []);

  const handleExport = () => window.open('http://127.0.0.1:5000/api/export_excel', '_blank');

  return (
    <div className="checkin-container">

      {/* 1. KHUNG CAMERA (BÊN TRÁI) */}
      <div className="left-panel">
        {/* Phần hiển thị Camera */}
        <div className="camera-view">
          <Webcam
            audio={false} ref={webcamRef} screenshotFormat="image/jpeg"
            className="webcam-fit" videoConstraints={{ facingMode: "user" }}
          />
          {isScanning && <div className="scan-line"></div>}

          {/* Thông báo trạng thái đè lên trên */}
          <div className="position-absolute top-0 w-100 p-2 text-center text-white bg-dark bg-opacity-75" style={{ zIndex: 10 }}>
            {msg}
          </div>
        </div>

        {/* Phần nút bấm điều khiển */}
        <div className="controls-area">
          {!isScanning ? (
            <button
              className="btn btn-primary w-100 py-3 fw-bold fs-5 shadow-sm"
              onClick={startAutoScan}
            >
              🚀 BẮT ĐẦU CHẤM CÔNG
            </button>
          ) : (
            <button
              className="btn btn-danger w-100 py-3 fw-bold fs-5 shadow-sm"
              onClick={stopScanning}
            >
              ⏹ DỪNG QUÉT
            </button>
          )}
        </div>
      </div>

      {/* 2. DANH SÁCH LOG (BÊN PHẢI) */}
      <div className="right-panel">
        <div className="logs-header">
          <span>Lịch sử hôm nay</span>
          <button onClick={handleExport} className="btn btn-sm btn-outline-success py-0" style={{ fontSize: '0.8rem' }}>Excel</button>
        </div>
        <div className="logs-list">
          <ul className="list-group list-group-flush">
            {logs.map((l, i) => (
              <li key={i} className="list-group-item py-2 px-3 border-bottom">
                <div className="d-flex justify-content-between align-items-center">
                  <div>
                    <div className="fw-bold text-dark" style={{ fontSize: '0.95rem' }}>{l.name}</div>
                    <small className="text-muted" style={{ fontSize: '0.75rem' }}>{l.time}</small>
                  </div>
                  <span className={`badge ${l.status === 'Đi muộn' ? 'bg-danger' : 'bg-success'}`} style={{ fontSize: '0.75rem' }}>
                    {l.status}
                  </span>
                </div>
              </li>
            ))}
            {logs.length === 0 && <li className="text-center text-muted p-4 small">Chưa có ai chấm công hôm nay</li>}
          </ul>
        </div>
      </div>

    </div>
  );
};

export default Checkin;