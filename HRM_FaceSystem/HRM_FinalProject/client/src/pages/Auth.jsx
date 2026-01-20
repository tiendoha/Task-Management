import React, { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';

const Auth = ({ onLoginSuccess }) => {
  const [isLogin, setIsLogin] = useState(true); // true: Login, false: Register
  const webcamRef = useRef(null);
  
  // Form Data
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullname, setFullname] = useState("");
  const [msg, setMsg] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  // State mới: Lưu ảnh đã chụp tạm thời
  const [capturedImage, setCapturedImage] = useState(null);

  // --- XỬ LÝ ĐĂNG NHẬP ---
  const handleLogin = async () => {
    try {
      const res = await axios.post('http://127.0.0.1:5000/api/login', { username, password });
      if (res.data.success) {
        onLoginSuccess(res.data.user);
      } else {
        setMsg("❌ " + res.data.message);
      }
    } catch (e) { setMsg("Lỗi Server"); }
  };

  // --- XỬ LÝ 1: BẤM QUÉT KHUÔN MẶT ---
  const handleCapture = useCallback(() => {
    if (!webcamRef.current) return;
    const imageSrc = webcamRef.current.getScreenshot();
    
    if (imageSrc) {
        setCapturedImage(imageSrc); // Lưu ảnh vào biến tạm
        setMsg("✅ Đã lấy mẫu khuôn mặt! Hãy bấm Đăng Ký.");
    } else {
        setMsg("⚠️ Camera chưa sẵn sàng.");
    }
  }, [webcamRef]);

  // --- XỬ LÝ 2: GỬI LÊN SERVER ---
  const handleRegister = async () => {
    if (!capturedImage) return setMsg("Vui lòng bấm Quét khuôn mặt trước!");
    if (!username || !password || !fullname || !email || !phone) 
        return setMsg("Vui lòng điền đủ thông tin!");

    setMsg("⏳ Đang gửi dữ liệu...");
    try {
      const res = await axios.post('http://127.0.0.1:5000/api/register', {
        username, password, name: fullname, image: capturedImage
      });
      
      if (res.data.success) {
        alert(res.data.message);
        setIsLogin(true); // Chuyển về login
        setMsg("");
        setCapturedImage(null); // Reset ảnh
      } else {
        setMsg("❌ " + res.data.message);
        // Nếu lỗi (ví dụ không tìm thấy mặt), cho phép chụp lại
        setCapturedImage(null); 
      }
    } catch (e) { setMsg("Lỗi Server"); }
  };

  // Hàm reset khi chuyển tab
  const switchMode = (mode) => {
      setIsLogin(mode);
      setMsg("");
      setCapturedImage(null);
  }

  return (
    <div className="auth-container">
      <div className="auth-box">
        {/* CỘT TRÁI: FORM */}
        <div className="auth-form">
          <h2 className="fw-bold text-primary mb-4">
            {isLogin ? "Đăng Nhập" : "Đăng Ký Mới"}
          </h2>
          
          {msg && <div className={`alert p-2 small ${msg.includes('✅') ? 'alert-success' : 'alert-danger'}`}>{msg}</div>}

          <div className="mb-3">
            <label>Tài khoản</label>
            <input className="form-control" value={username} onChange={e=>setUsername(e.target.value)} placeholder="Nhập tên đăng nhập..." />
          </div>
          
          <div className="mb-3">
            <label>Mật khẩu</label>
            <input type="password" className="form-control" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Nhập mật khẩu..." />
          </div>

          {!isLogin && (
            <>
              <div className="mb-3">
                <label>Họ và Tên</label>
                <input className="form-control" value={fullname} onChange={e=>setFullname(e.target.value)} placeholder="Nguyễn Văn A" />
              </div>
              <div className="row">
                  <div className="col-6 mb-3">
                    <label>Email</label>
                    <input className="form-control" value={email} onChange={e=>setEmail(e.target.value)} placeholder="a@gmail.com" />
                  </div>
                  <div className="col-6 mb-3">
                    <label>SĐT</label>
                    <input className="form-control" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="09xxxx" />
                  </div>
              </div>
            </>
          )}

          {/* NÚT BẤM LOGIC */}
          {isLogin ? (
              <button className="btn btn-primary w-100 py-2 fw-bold mt-2" onClick={handleLogin}>
                ĐĂNG NHẬP
              </button>
          ) : (
              <div className="d-grid gap-2">
                  {/* Nút 1: Quét mặt (Chưa chụp thì hiện nút này) */}
                  {!capturedImage ? (
                      <button className="btn btn-info text-white fw-bold" onClick={handleCapture}>
                        📸 1. QUÉT KHUÔN MẶT
                      </button>
                  ) : (
                      // Nếu chụp rồi thì hiện nút Chụp lại
                      <button className="btn btn-secondary fw-bold" onClick={() => {setCapturedImage(null); setMsg("Hãy quét lại.")}}>
                        🔄 QUÉT LẠI
                      </button>
                  )}

                  {/* Nút 2: Đăng ký (Disabled nếu chưa có ảnh) */}
                  <button 
                    className="btn btn-primary fw-bold"
                    onClick={handleRegister}
                    disabled={!capturedImage} 
                  >
                    💾 2. LƯU ĐĂNG KÝ
                  </button>
              </div>
          )}

          <div className="text-center mt-3">
            <span className="text-muted small">
              {isLogin ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
            </span>
            <a href="#" onClick={(e) => { e.preventDefault(); switchMode(!isLogin); }}>
              {isLogin ? "Đăng ký ngay" : "Đăng nhập ngay"}
            </a>
          </div>
        </div>

        {/* CỘT PHẢI: CAMERA HOẶC ẢNH ĐÃ CHỤP */}
        {!isLogin ? (
           <div className="auth-camera">
              {capturedImage ? (
                  // Nếu đã chụp -> Hiện ảnh tĩnh để người dùng check
                  <img src={capturedImage} alt="Captured" style={{width: '100%', height: '100%', objectFit: 'cover'}} />
              ) : (
                  // Nếu chưa chụp -> Hiện Camera thật
                  <>
                    <Webcam 
                        audio={false} ref={webcamRef} screenshotFormat="image/jpeg" 
                        width="100%" height="100%" videoConstraints={{facingMode: "user"}}
                        style={{objectFit: 'cover'}}
                    />
                    <div className="scan-line"></div>
                  </>
              )}
              
              <div className="position-absolute bottom-0 w-100 text-center text-white bg-dark bg-opacity-50 p-2">
                {capturedImage ? "✅ Ảnh mẫu đã được lưu" : "Giữ khuôn mặt trong khung hình"}
              </div>
           </div>
        ) : (
           <div className="auth-camera d-flex align-items-center justify-content-center bg-light">
              <img src="https://cdn-icons-png.flaticon.com/512/295/295128.png" alt="Login" width="150" style={{opacity: 0.5}} />
           </div>
        )}
      </div>
    </div>
  );
};

export default Auth;