import React, { useEffect, useState } from 'react';

function Dashboard({ token }) {
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    if (!token) return;
    // Determine websocket URL based on current location (ws or wss)
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    const wsUrl = `${proto}://${host}/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages((msgs) => [data, ...msgs.slice(0, 99)]);
      } catch (err) {
        console.error('Invalid message', err);
      }
    };
    ws.onerror = (err) => {
      console.error('WebSocket error', err);
    };
    return () => {
      ws.close();
    };
  }, [token]);

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Realtime Dashboard</h2>
      <p>This page streams live price spreads and executed trades.</p>
      <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #ddd', padding: '0.5rem' }}>
        {messages.length === 0 && <p>No updates yet.</p>}
        {messages.map((msg, idx) => (
          <div key={idx} style={{ marginBottom: '0.5rem', background: '#f5f5f5', padding: '0.5rem', borderRadius: '4px' }}>
            {msg.type === 'ticker' ? (
              <div>
                <strong>{msg.coin}</strong> spread {Math.round(msg.spread_percent * 10000) / 100}% between
                {` ${msg.best_buy.exchange}`} (buy {msg.best_buy.price.toFixed(2)}) and
                {` ${msg.best_sell.exchange}`} (sell {msg.best_sell.price.toFixed(2)}).
              </div>
            ) : msg.type === 'trade' ? (
              <div>
                <strong>TRADE:</strong> {msg.amount.toFixed(6)} {msg.coin} bought on {msg.buy[0]} and sold on {msg.sell[0]}.
                Profit: {msg.profit.toFixed(2)} USDT. Status: {msg.status}
                {msg.error && <span style={{ color: 'red' }}> Error: {msg.error}</span>}
              </div>
            ) : (
              <pre>{JSON.stringify(msg)}</pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
