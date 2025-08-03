import React, { useEffect, useState } from 'react';
import axios from 'axios';

// Base URL for API. Empty string uses current origin.
const API_BASE = '';

function Settings({ token }) {
  const [exchangeKeys, setExchangeKeys] = useState([]);
  const [botConfigs, setBotConfigs] = useState([]);
  const [newKey, setNewKey] = useState({ exchange: '', api_key: '', api_secret: '', api_password: '', is_enabled: false });
  const [newConfig, setNewConfig] = useState({ mode: 'sandbox', coins: 'BTC,ETH', budget: 0, max_trade_size: 0, slippage_tolerance: 0.005, stop_loss: 0.1, daily_limit: 0.2, profit_take: 0.2 });
  const [message, setMessage] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    try {
      const [keysRes, configsRes] = await Promise.all([
        axios.get(`${API_BASE}/exchange-keys`, { headers }),
        axios.get(`${API_BASE}/bot-configs`, { headers }),
      ]);
      setExchangeKeys(keysRes.data);
      setBotConfigs(configsRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAddKey = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/exchange-keys`, newKey, { headers });
      setMessage('Exchange key added');
      setNewKey({ exchange: '', api_key: '', api_secret: '', api_password: '', is_enabled: false });
      loadData();
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to add key');
    }
  };

  const handleAddConfig = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/bot-configs`, newConfig, { headers });
      setMessage('Configuration added');
      setNewConfig({ ...newConfig, budget: 0, max_trade_size: 0 });
      loadData();
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to add configuration');
    }
  };

  const startBot = async (id) => {
    try {
      await axios.post(`${API_BASE}/bot-configs/${id}/start`, null, { headers });
      setMessage(`Bot ${id} started`);
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to start bot');
    }
  };

  const stopBot = async (id) => {
    try {
      await axios.post(`${API_BASE}/bot-configs/${id}/stop`, null, { headers });
      setMessage(`Bot ${id} stopped`);
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to stop bot');
    }
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Settings</h2>
      {message && <p>{message}</p>}
      <h3>Exchange API Keys</h3>
      <form onSubmit={handleAddKey} style={{ marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder="Exchange name (e.g. binance)"
          value={newKey.exchange}
          onChange={(e) => setNewKey({ ...newKey, exchange: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="API key"
          value={newKey.api_key}
          onChange={(e) => setNewKey({ ...newKey, api_key: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="API secret"
          value={newKey.api_secret}
          onChange={(e) => setNewKey({ ...newKey, api_secret: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="API password (optional)"
          value={newKey.api_password}
          onChange={(e) => setNewKey({ ...newKey, api_password: e.target.value })}
        />
        <label>
          <input
            type="checkbox"
            checked={newKey.is_enabled}
            onChange={(e) => setNewKey({ ...newKey, is_enabled: e.target.checked })}
          />
          Enabled
        </label>
        <button type="submit">Add Key</button>
      </form>
      <ul>
        {exchangeKeys.map((key) => (
          <li key={key.id}>{key.exchange} (enabled: {key.is_enabled ? 'yes' : 'no'})</li>
        ))}
      </ul>
      <h3>Bot Configurations</h3>
      <form onSubmit={handleAddConfig} style={{ marginBottom: '1rem' }}>
        <select value={newConfig.mode} onChange={(e) => setNewConfig({ ...newConfig, mode: e.target.value })}>
          <option value="sandbox">Sandbox</option>
          <option value="live">Live</option>
        </select>
        <input
          type="text"
          placeholder="Coins (comma separated)"
          value={newConfig.coins}
          onChange={(e) => setNewConfig({ ...newConfig, coins: e.target.value })}
        />
        <input
          type="number"
          placeholder="Budget (USDT)"
          value={newConfig.budget}
          onChange={(e) => setNewConfig({ ...newConfig, budget: parseFloat(e.target.value) })}
        />
        <input
          type="number"
          placeholder="Max trade size (USDT)"
          value={newConfig.max_trade_size}
          onChange={(e) => setNewConfig({ ...newConfig, max_trade_size: parseFloat(e.target.value) })}
        />
        <input
          type="number"
          step="0.0001"
          placeholder="Slippage tolerance (decimal)"
          value={newConfig.slippage_tolerance}
          onChange={(e) => setNewConfig({ ...newConfig, slippage_tolerance: parseFloat(e.target.value) })}
        />
        <button type="submit">Add Configuration</button>
      </form>
      <ul>
        {botConfigs.map((cfg) => (
          <li key={cfg.id}>
            {cfg.mode.toUpperCase()} coins {cfg.coins} budget {cfg.budget} max trade {cfg.max_trade_size}
            <button onClick={() => startBot(cfg.id)} style={{ marginLeft: '0.5rem' }}>Start</button>
            <button onClick={() => stopBot(cfg.id)} style={{ marginLeft: '0.5rem' }}>Stop</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Settings;
