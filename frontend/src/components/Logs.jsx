import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_BASE = '';

function Logs({ token }) {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await axios.get(`${API_BASE}/trade-logs`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setLogs(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchLogs();
  }, [token]);

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Trade Logs</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Time</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Coin</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Buy</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Sell</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Amount</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Profit</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td style={{ borderBottom: '1px solid #eee' }}>{new Date(log.timestamp).toLocaleString()}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{log.coin}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{log.buy_exchange} @ {log.price_buy.toFixed(2)}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{log.sell_exchange} @ {log.price_sell.toFixed(2)}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{log.amount.toFixed(6)}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{log.profit.toFixed(2)}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{log.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Logs;
