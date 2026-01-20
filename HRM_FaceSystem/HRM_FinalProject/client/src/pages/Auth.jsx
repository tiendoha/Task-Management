import React, { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import '../App.css'; // Đảm bảo import CSS

const Auth = ({ onLoginSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const webcamRef = useRef(null);
  
  // State Form
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullname, setFullname] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [msg, setMsg] = useState("");

  // State Ảnh
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
    } catch (e) { setMsg("Lỗi kết nối Server"); }
  };

  // --- XỬ LÝ CHỤP ẢNH ---
  const handleCapture = useCallback(() => {
    if (!webcamRef.current) return;
    const imageSrc = webcamRef.current.getScreenshot();
    if (imageSrc) {
        setCapturedImage(imageSrc);
        setMsg("✅ Đã lấy mẫu khuôn mặt!");
    }
  }, [webcamRef]);

  // --- XỬ LÝ ĐĂNG KÝ ---
  const handleRegister = async () => {
    if (!capturedImage) return setMsg("⚠️ Vui lòng quét khuôn mặt trước!");
    if (!username || !password || !fullname || !email || !phone) return setMsg("⚠️ Vui lòng điền đủ thông tin!");

    setMsg("⏳ Đang xử lý...");
    try {
      const res = await axios.post('http://127.0.0.1:5000/api/register', {
        username, password, name: fullname, email, phone, image: capturedImage
      });
      if (res.data.success) {
        alert(res.data.message);
        setIsLogin(true); // Về trang login
        setMsg("");
        setCapturedImage(null);
      } else {
        setMsg("❌ " + res.data.message);
      }
    } catch (e) { setMsg("Lỗi Server"); }
  };

  const switchMode = (mode) => {
      setIsLogin(mode); setMsg(""); setCapturedImage(null);
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        
        {/* 1. CỘT TRÁI: FORM NHẬP LIỆU */}
        <div className="auth-form-section">
          <h1 className="auth-title">{isLogin ? "Xin Chào" : "Tạo Tài Khoản"}</h1>
          <p className="auth-subtitle">{isLogin ? "Đăng nhập để quản lý nhân sự" : "Đăng ký thông tin nhân viên mới"}</p>
          
          {msg && <div className={`alert p-2 mb-3 rounded small ${msg.includes('✅')?'alert-success':'alert-danger'}`}>{msg}</div>}

          <div className="form-group">
             <label className="form-label">Tài khoản</label>
             <input className="form-input" value={username} onChange={e=>setUsername(e.target.value)} placeholder="Nhập username..." />
          </div>
          
          <div className="form-group">
             <label className="form-label">Mật khẩu</label>
             <input type="password" className="form-input" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Nhập password..." />
          </div>

          {!isLogin && (
            <>
              <div className="form-group">
                 <label className="form-label">Họ và Tên</label>
                 <input className="form-input" value={fullname} onChange={e=>setFullname(e.target.value)} placeholder="Nguyễn Văn A" />
              </div>
              <div style={{display:'flex', gap:'10px'}}>
                  <div className="form-group" style={{flex:1}}>
                     <label className="form-label">Email</label>
                     <input className="form-input" value={email} onChange={e=>setEmail(e.target.value)} placeholder="email@example.com" />
                  </div>
                  <div className="form-group" style={{flex:1}}>
                     <label className="form-label">SĐT</label>
                     <input className="form-input" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="09xxxx" />
                  </div>
              </div>
            </>
          )}

          {/* Buttons */}
          <div className="mt-2">
             {isLogin ? (
                 <button className="btn-primary" onClick={handleLogin}>ĐĂNG NHẬP HỆ THỐNG</button>
             ) : (
                 <div className="d-grid gap-2">
                    {/* Nếu chưa chụp thì hiện nút chụp, chụp rồi thì hiện nút Lưu */}
                    {!capturedImage ? (
                        <button className="btn-secondary" onClick={()=>{}}>👉 Vui lòng nhìn sang phải để quét mặt</button>
                    ) : (
                        <button className="btn-primary" onClick={handleRegister}>LƯU ĐĂNG KÝ</button>
                    )}
                 </div>
             )}
          </div>

          <div className="auth-switch">
             {isLogin ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
             <a onClick={()=>switchMode(!isLogin)}>{isLogin ? "Đăng ký ngay" : "Đăng nhập ngay"}</a>
          </div>
        </div>

        {/* 2. CỘT PHẢI: CAMERA / HÌNH ẢNH */}
        <div className="auth-visual-section">
           {isLogin ? (
               // Màn hình Login: Hiện hình minh họa đẹp
               <div style={{textAlign:'center', padding:'20px'}}>
                   <img src="https://cdni.iconscout.com/illustration/premium/thumb/face-recognition-login-illustration-download-in-svg-png-gif-file-formats--scan-scanning-id-security-technology-pack-network-communication-illustrations-4366687.png" 
                        alt="Login Visual" style={{width:'80%', opacity: 0.9}} />
                   <h5 className="mt-3 text-primary">HRM FaceID System</h5>
               </div>
           ) : (
               // Màn hình Register: Hiện Camera
               <div className="auth-camera-container">
                   {capturedImage ? (
                       <>
                         <img src={capturedImage} alt="Captured" style={{width:'100%', height:'100%', objectFit:'cover'}} />
                         <div className="position-absolute bottom-0 w-100 p-2 text-center">
                            <button className="btn btn-sm btn-light" onClick={()=>setCapturedImage(null)}>🔄 Quét lại</button>
                         </div>
                       </>
                   ) : (
                       <>
                         <Webcam 
                            audio={false} ref={webcamRef} screenshotFormat="image/jpeg" 
                            className="auth-webcam" videoConstraints={{facingMode:"user"}}
                         />
                         <div className="scan-line"></div>
                         <button 
                            className="btn btn-primary position-absolute bottom-0 start-50 translate-middle-x mb-3 w-50"
                            onClick={handleCapture}
                         >
                            📸 CHỤP ẢNH
                         </button>
                       </>
                   )}
               </div>
           )}
        </div>

      </div>
    </div>
  );
};

export default Auth;