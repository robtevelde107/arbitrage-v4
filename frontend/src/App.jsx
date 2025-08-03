import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom';

import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import Logs from './components/Logs';
import Login from './components/Login';

function App() {
  const navigate = useNavigate();
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }, [token]);

  const handleLogout = () => {
    setToken(null);
    navigate('/login');
  };

  return (
    <div>
      <nav style={{ display: 'flex', gap: '1rem', padding: '1rem', backgroundColor: '#0d47a1', color: 'white' }}>
        <Link style={{ color: 'white' }} to="/">Dashboard</Link>
        <Link style={{ color: 'white' }} to="/settings">Settings</Link>
        <Link style={{ color: 'white' }} to="/logs">Logs</Link>
        {token ? (
          <button onClick={handleLogout} style={{ marginLeft: 'auto', color: '#0d47a1', background: 'white', border: 'none', padding: '0.3rem 1rem', borderRadius: '4px' }}>Logout</button>
        ) : (
          <Link style={{ marginLeft: 'auto', color: 'white' }} to="/login">Login</Link>
        )}
      </nav>
      <Routes>
        <Route
          path="/"
          element={token ? <Dashboard token={token} /> : <Navigate to="/login" replace />} />
        <Route
          path="/settings"
          element={token ? <Settings token={token} setToken={setToken} /> : <Navigate to="/login" replace />} />
        <Route
          path="/logs"
          element={token ? <Logs token={token} /> : <Navigate to="/login" replace />} />
        <Route path="/login" element={<Login setToken={setToken} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
