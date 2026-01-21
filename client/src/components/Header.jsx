import React from 'react';

const Header = ({ title }) => {
  return (
    <div style={{
      height: '70px', 
      background: 'white', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'space-between', 
      padding: '0 30px',
      borderBottom: '1px solid #eee'
    }}>
      <h4 className="m-0 fw-bold text-dark">{title}</h4>
      <div className="d-flex align-items-center gap-3">
        <span className="badge bg-light text-dark border">Admin User</span>
        <div style={{width: '35px', height: '35px', borderRadius: '50%', background: '#007bff', color:'white', display:'flex', alignItems:'center', justifyContent:'center'}}>
          A
        </div>
      </div>
    </div>
  );
};

export default Header;