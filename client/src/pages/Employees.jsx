import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Webcam from 'react-webcam';
import { Modal, Button, Form } from 'react-bootstrap';

const Employees = () => {
  const [users, setUsers] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  
  // Webcam refs
  const webcamRef = useRef(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [showCamera, setShowCamera] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    id: '', username: '', password: '', name: '', 
    dob: '', phone: '', email: '', role: 'user'
  });

  const [passError, setPassError] = useState("");

  const loadUsers = () => {
    axios.get('http://127.0.0.1:5000/api/employees')
      .then(res => {
          console.log("Dữ liệu từ server:", res.data);
          if(Array.isArray(res.data)) setUsers(res.data);
          else setUsers([]);
      })
      .catch(err => {
          console.error(err)
          alert("Không tải được danh sách nhân viên!");
      });
  };

  useEffect(() => { loadUsers(); }, []);

  const validatePassword = (pwd) => {
    const regex = /^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{6,}$/;
    if (!regex.test(pwd)) {
      setPassError("Mật khẩu yếu: Cần 1 hoa, 1 số, 1 ký tự đặc biệt, >6 ký tự.");
      return false;
    }
    setPassError("");
    return true;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    if (name === 'password' && value) validatePassword(value);
  };

  const handleAddClick = () => {
    setIsEditMode(false);
    setFormData({ id: '', username: '', password: '', name: '', dob: '', phone: '', email: '', role: 'user' });
    setCapturedImage(null);
    setShowCamera(false);
    setPassError("");
    setShowModal(true);
  };

  const handleEditClick = (user) => {
    setIsEditMode(true);
    setFormData({ ...user, password: '', dob: user.dob || '', email: user.email || '', phone: user.phone || '' }); 
    setCapturedImage(null);
    setShowCamera(false);
    setPassError("");
    setShowModal(true);
  };

  const handleCapture = () => {
      if(webcamRef.current) {
          setCapturedImage(webcamRef.current.getScreenshot());
          setShowCamera(false);
      }
  }

  const handleSave = async () => {
      if(!isEditMode && !formData.password) return alert("Thiếu mật khẩu!");
      if(formData.password && !validatePassword(formData.password)) return alert("Mật khẩu chưa đạt yêu cầu!");
      if(!isEditMode && !capturedImage) return alert("Thiếu ảnh khuôn mặt!");
      if(!formData.username || !formData.name) return alert("Thiếu thông tin cơ bản!");

      const payload = { ...formData, image: capturedImage };

      try {
          if(isEditMode) {
              await axios.put(`http://127.0.0.1:5000/api/employees/${formData.id}`, payload);
          } else {
              await axios.post('http://127.0.0.1:5000/api/register', payload);
          }
          alert("Thành công!");
          setShowModal(false);
          loadUsers();
      } catch (err) {
          alert(err.response?.data?.message || "Lỗi Server");
      }
  };

  const handleDelete = async (id, name) => {
    if(window.confirm(`Xóa nhân viên ${name}?`)) {
      try {
        await axios.delete(`http://127.0.0.1:5000/api/employees/${id}`);
        loadUsers();
      } catch (e) { alert("Lỗi xóa nhân viên"); }
    }
  };

  return (
    <div className="card-custom">
      {/* --- PHẦN HEADER CỦA BẢNG (ĐÃ SỬA) --- */}
      <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">
          {/* Bên trái: Tiêu đề */}
          <h5 className="fw-bold text-dark m-0">Danh sách nhân viên</h5>

          {/* Bên phải: Button và Số lượng */}
          <div className="text-end">
              <Button variant="primary" onClick={handleAddClick} className="px-4 py-2 fw-bold shadow-sm mb-1">
                 <span style={{marginRight: '5px'}}>+</span> Thêm Mới
              </Button>
              <div><small className="text-muted">Tổng số: {users.length} người</small></div>
          </div>
      </div>

      {/* --- PHẦN BẢNG DỮ LIỆU --- */}
      <div className="table-responsive">
        <table className="table table-hover align-middle">
            <thead className="table-light">
            <tr>
                <th className="py-3">STT</th>
                <th className="py-3">Họ Tên</th>
                <th className="py-3">Ngày Sinh</th>
                <th className="py-3">Liên Hệ</th>
                <th className="py-3">Vai Trò</th>
                <th className="py-3 text-end">Thao Tác</th>
            </tr>
            </thead>
            <tbody>
            {users.length > 0 ? users.map((u, i) => (
                <tr key={u.id || i}>
                <td>{i + 1}</td>
                <td>
                    <div className="fw-bold text-primary">{u.name}</div>
                    <div className="small text-muted">@{u.username}</div>
                </td>
                <td>{u.dob || "-"}</td>
                <td>
                    <div className="small">📧 {u.email || "Trống"}</div>
                    <div className="small">📞 {u.phone || "Trống"}</div>
                </td>
                <td>
                    <span className={`badge ${u.role==='admin'?'bg-danger':'bg-info text-dark'}`}>
                        {u.role.toUpperCase()}
                    </span>
                </td>
                <td className="text-end">
                    <Button variant="light" size="sm" className="me-2 text-primary border" onClick={() => handleEditClick(u)}>✏️ Sửa</Button>
                    <Button variant="light" size="sm" className="text-danger border" onClick={() => handleDelete(u.id, u.name)}>🗑️ Xóa</Button>
                </td>
                </tr>
            )) : (
                <tr><td colSpan="6" className="text-center py-5 text-muted">Chưa có nhân viên nào</td></tr>
            )}
            </tbody>
        </table>
      </div>

      {/* --- PHẦN MODAL (Giữ nguyên code cũ) --- */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" backdrop="static" centered>
        {/* ... (Giữ nguyên nội dung bên trong Modal như cũ) ... */}
        <Modal.Header closeButton>
          <Modal.Title>{isEditMode ? "Sửa Thông Tin" : "Thêm Nhân Viên"}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
           <div className="row">
               <div className="col-md-7">
                   <Form>
                       <h6 className="text-primary border-bottom pb-2 mb-3">Tài Khoản</h6>
                       <Form.Group className="mb-2">
                           <Form.Label>Username</Form.Label>
                           <Form.Control 
                                name="username" value={formData.username} onChange={handleChange} 
                                disabled={isEditMode} placeholder="Ví dụ: nv01"
                           />
                       </Form.Group>
                       <Form.Group className="mb-2">
                           <Form.Label>Password {isEditMode && <small className="text-muted">(Để trống nếu giữ nguyên)</small>}</Form.Label>
                           <Form.Control 
                                type="password" name="password" value={formData.password} onChange={handleChange} 
                           />
                           {passError && <div className="text-danger small mt-1">{passError}</div>}
                       </Form.Group>
                       <Form.Group className="mb-3">
                           <Form.Label>Quyền hạn</Form.Label>
                           <Form.Select name="role" value={formData.role} onChange={handleChange}>
                               <option value="user">Nhân viên</option>
                               <option value="admin">Quản trị viên</option>
                           </Form.Select>
                       </Form.Group>

                       <h6 className="text-primary border-bottom pb-2 mb-3 mt-4">Cá Nhân</h6>
                       <Form.Group className="mb-2">
                           <Form.Label>Họ Tên</Form.Label>
                           <Form.Control name="name" value={formData.name} onChange={handleChange} />
                       </Form.Group>
                       <div className="row">
                           <div className="col-6 mb-2">
                               <Form.Label>Ngày sinh</Form.Label>
                               <Form.Control type="date" name="dob" value={formData.dob} onChange={handleChange} />
                           </div>
                           <div className="col-6 mb-2">
                               <Form.Label>SĐT</Form.Label>
                               <Form.Control name="phone" value={formData.phone} onChange={handleChange} />
                           </div>
                       </div>
                       <Form.Group className="mb-2">
                           <Form.Label>Email</Form.Label>
                           <Form.Control type="email" name="email" value={formData.email} onChange={handleChange} />
                       </Form.Group>
                   </Form>
               </div>

               <div className="col-md-5 border-start">
                   <h6 className="text-primary border-bottom pb-2 mb-3 text-center">Face ID</h6>
                   <div className="bg-dark d-flex align-items-center justify-content-center mb-3 rounded overflow-hidden" style={{height:'220px'}}>
                       {showCamera ? (
                           <Webcam audio={false} ref={webcamRef} screenshotFormat="image/jpeg" style={{width:'100%', height:'100%', objectFit:'cover'}} />
                       ) : capturedImage ? (
                           <img src={capturedImage} alt="Face" style={{width:'100%', height:'100%', objectFit:'cover'}} />
                       ) : (
                           <span className="text-white-50 small">Chưa có ảnh</span>
                       )}
                   </div>
                   
                   <div className="d-grid gap-2">
                       {!showCamera ? (
                           <Button variant="outline-primary" onClick={()=>{setShowCamera(true); setCapturedImage(null)}}>
                               {capturedImage ? "Chụp Lại" : "Bật Camera"}
                           </Button>
                       ) : (
                           <Button variant="success" onClick={handleCapture}>Chụp Ảnh</Button>
                       )}
                   </div>
               </div>
           </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>Đóng</Button>
          <Button variant="primary" onClick={handleSave} disabled={!!passError}>Lưu Lại</Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default Employees;