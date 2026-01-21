import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Settings = () => {
  const [start, setStart] = useState("08:00");
  const [end, setEnd] = useState("17:00");

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/shifts').then(res => {
        if(res.data.length > 0) { setStart(res.data[0].start); setEnd(res.data[0].end); }
    });
  }, []);

  const saveShift = async () => {
      await axios.post('http://127.0.0.1:5000/api/shifts', {start_time: start, end_time: end});
      alert("Đã lưu cấu hình!");
  }

  return (
    <div className="card-custom fade-in" style={{maxWidth: '500px'}}>
      <h5 className="mb-4">Cấu hình Ca Làm Việc</h5>
      <div className="mb-3">
        <label>Giờ Bắt Đầu:</label>
        <input type="time" className="form-control" value={start} onChange={e=>setStart(e.target.value)}/>
      </div>
      <div className="mb-3">
        <label>Giờ Kết Thúc:</label>
        <input type="time" className="form-control" value={end} onChange={e=>setEnd(e.target.value)}/>
      </div>
      <button className="btn btn-primary w-100" onClick={saveShift}>Lưu Thay Đổi</button>
    </div>
  );
};

export default Settings;