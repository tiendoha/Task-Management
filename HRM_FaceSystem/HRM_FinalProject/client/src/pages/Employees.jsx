import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Employees = () => {
  const [users, setUsers] = useState([]);

  const loadUsers = () => {
    axios.get('http://127.0.0.1:5000/api/employees').then(res => setUsers(res.data));
  };

  useEffect(() => { loadUsers(); }, []);

  const handleDelete = async (id) => {
    if(window.confirm("Xóa nhân viên này?")) {
      await axios.delete(`http://127.0.0.1:5000/api/employees/${id}`);
      loadUsers();
    }
  };

  return (
    <div className="card-custom fade-in">
      <table className="table table-hover">
        <thead className="table-light">
          <tr><th>ID</th><th>Họ Tên</th><th>Chức Vụ</th><th>Ca Làm</th><th>Hành Động</th></tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id}>
              <td>#{u.id}</td>
              <td className="fw-bold">{u.name}</td>
              <td>{u.role}</td>
              <td>{u.shift}</td>
              <td><button className="btn btn-sm btn-outline-danger" onClick={()=>handleDelete(u.id)}>Xóa</button></td>
            </tr>
          ))}
          {users.length === 0 && <tr><td colSpan="5" className="text-center">Trống</td></tr>}
        </tbody>
      </table>
    </div>
  );
};

export default Employees;