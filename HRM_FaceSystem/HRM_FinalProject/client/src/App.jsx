import React, { useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Footer from './components/Footer';
import Auth from './pages/Auth'; // Import trang Auth

import Dashboard from './pages/Dashboard';
import Checkin from './pages/Checkin';
import Employees from './pages/Employees';
import Settings from './pages/Settings';

const App = () => {
  // State User: null nghĩa là chưa đăng nhập
  const [currentUser, setCurrentUser] = useState(null);
  const [currentView, setCurrentView] = useState('dashboard');

  // Nếu chưa đăng nhập -> Hiện trang Auth
  if (!currentUser) {
    return <Auth onLoginSuccess={(user) => setCurrentUser(user)} />;
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
    const titles = { dashboard: 'Tổng Quan', checkin: 'Máy Chấm Công', employees: 'Nhân Sự', settings: 'Cài Đặt' };
    return titles[currentView];
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setCurrentView('dashboard');
  };

  return (
    <div className="app-layout">
      {/* Sidebar cố định */}
      <div className="sidebar">
         <Sidebar currentView={currentView} setCurrentView={setCurrentView} />
      </div>

      {/* Wrapper chính */}
      <div className="main-wrapper">
        <Header title={getTitle()} user={currentUser} />
        
        {/* Body full màn hình */}
        <div className="app-body">
          {renderBody()}
        </div>

        <Footer />
      </div>
    </div>
  );
};

export default App;