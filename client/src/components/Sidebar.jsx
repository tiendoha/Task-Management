import React from 'react';

const Sidebar = ({ currentView, setCurrentView, onLogout }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Tổng Quan', icon: '📊' },
    { id: 'checkin', label: 'Chấm Công', icon: '📸' },
    { id: 'employees', label: 'Nhân Sự', icon: '👥' },
    { id: 'settings', label: 'Cài Đặt', icon: '⚙️' },
  ];

  return (
    <div className="sidebar-container">
      <div className="brand">HRM FaceID</div>
      
      {/* Danh sách Menu */}
      <div style={{ flex: 1 }}>
        {menuItems.map((item) => (
          <div 
            key={item.id}
            className={`menu-item ${currentView === item.id ? 'active' : ''}`}
            onClick={() => setCurrentView(item.id)}
          >
            <span className="menu-icon">{item.icon}</span>
            {item.label}
          </div>
        ))}
      </div>
      
      {/* NÚT ĐĂNG XUẤT (Nằm dưới cùng) */}
      <div className="mt-auto pt-3 border-top">
        <button 
          className="btn btn-outline-danger w-100 btn-sm fw-bold d-flex align-items-center justify-content-center gap-2" 
          onClick={onLogout}
        >
          <span>🚪</span> Đăng Xuất
        </button>
      </div>
    </div>
  );
};

export default Sidebar;