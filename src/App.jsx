import { useState } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function fetchPrediction() {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API_BASE}/predict`, {
        params: { lat: 12.34, lon: 56.78 }
      });
      setResult(data);
    } catch (err) {
      console.error(err);
      setResult({ error: err?.response?.data || err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 20, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Flash Flood Prediction</h1>
      <button onClick={fetchPrediction} disabled={loading}>
        {loading ? 'Loading…' : 'Get prediction'}
      </button>
      <pre style={{ whiteSpace: 'pre-wrap', marginTop: 16 }}>
        {result ? JSON.stringify(result, null, 2) : 'No data yet'}
      </pre>
    </div>
  );
}
