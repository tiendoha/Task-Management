import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Dashboard = () => {
  const [stats, setStats] = useState({ total_employees: 0, present_today: 0, late_today: 0, absent: 0 });

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/stats').then(res => setStats(res.data));
  }, []);

  const StatCard = ({ label, value, color }) => (
    <div className="card-custom text-center">
      <h6 className="text-muted text-uppercase">{label}</h6>
      <h2 className="fw-bold my-2" style={{color: color}}>{value}</h2>
    </div>
  );

  return (
    <div className="fade-in">
      <div className="row g-4">
        <div className="col-md-3"><StatCard label="Tổng Nhân Sự" value={stats.total_employees} color="#007bff" /></div>
        <div className="col-md-3"><StatCard label="Điểm Danh" value={stats.present_today} color="#28a745" /></div>
        <div className="col-md-3"><StatCard label="Đi Muộn" value={stats.late_today} color="#ffc107" /></div>
        <div className="col-md-3"><StatCard label="Vắng Mặt" value={stats.absent} color="#dc3545" /></div>
      </div>
      
      {/* Chart giả lập */}
      <div className="card-custom mt-4">
        <h5>Biểu đồ chuyên cần hôm nay</h5>
        <div className="progress mt-3" style={{height: '40px'}}>
           <div className="progress-bar bg-success" style={{width: `${(stats.present_today/stats.total_employees)*100}%`}}>Có mặt</div>
           <div className="progress-bar bg-danger" style={{width: `${(stats.absent/stats.total_employees)*100}%`}}>Vắng</div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;