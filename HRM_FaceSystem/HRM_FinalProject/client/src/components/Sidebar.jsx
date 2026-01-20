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
      
      <div className="mt-auto">
        <button className="btn btn-outline-danger w-100" onClick={onLogout}>
          🚪 Đăng Xuất
        </button>
      </div>
    </div>
  );
};

export default Sidebar;