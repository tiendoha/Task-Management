import React, { useState, useEffect } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

// Components
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Auth from './pages/Auth';

// Pages
import Dashboard from './pages/Dashboard';
import Checkin from './pages/Checkin';
import Employees from './pages/Employees';
import Settings from './pages/Settings';

const App = () => {
  const [currentUser, setCurrentUser] = useState(null);
  const [currentView, setCurrentView] = useState('dashboard');
  const [isLoading, setIsLoading] = useState(true);

  // 1. KHI MỞ APP: Kiểm tra xem đã đăng nhập trước đó chưa
  useEffect(() => {
    const storedUser = localStorage.getItem('user_info');
    if (storedUser) {
      setCurrentUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  // 2. KHI ĐĂNG NHẬP THÀNH CÔNG
  const handleLoginSuccess = (user) => {
    setCurrentUser(user);
    localStorage.setItem('user_info', JSON.stringify(user)); // Lưu vào máy
  };

  // 3. KHI ĐĂNG XUẤT (Logic quan trọng)
  const handleLogout = () => {
    // Xóa thông tin trong máy
    localStorage.removeItem('user_info'); 
    // Reset biến user về null -> App sẽ tự chuyển về màn hình Auth
    setCurrentUser(null);
    setCurrentView('dashboard');
  };

  if (isLoading) return null; // Hoặc hiện loading spinner

  // Nếu chưa đăng nhập -> Hiện trang Auth
  if (!currentUser) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  // Nếu đã đăng nhập -> Hiện giao diện chính
  const renderBody = () => {
    switch (currentView) {
      case 'dashboard': return <Dashboard />;
      case 'checkin':   return <Checkin />;
      case 'employees': return <Employees />;
      case 'settings':  return <Settings />;
      default:          return <Dashboard />;
    }
  };

  const getTitle = () => {
    const titles = { dashboard: 'Tổng Quan', checkin: 'Máy Chấm Công', employees: 'Quản Lý Nhân Sự', settings: 'Cài Đặt Hệ Thống' };
    return titles[currentView];
  };

  return (
    <div className="app-layout">
      {/* Truyền hàm handleLogout vào Sidebar */}
      <Sidebar 
        currentView={currentView} 
        setCurrentView={setCurrentView} 
        onLogout={handleLogout} 
      />

      <div className="main-wrapper">
        <Header title={getTitle()} user={currentUser} />
        <div className="app-body">
          {renderBody()}
        </div>
      </div>
    </div>
  );
};

export default App;