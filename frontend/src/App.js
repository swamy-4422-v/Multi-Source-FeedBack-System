import { useEffect, useState, useCallback } from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';

// Uses empty string to fully utilize the package.json proxy target in development
const API ='https://multi-source-feedback-system-backend.onrender.com';

// ── colour helpers ────────────────────────────────────────
const SENTIMENT_COLOR = { positive: '#22c55e', negative: '#ef4444', neutral: '#94a3b8' };
const CATEGORY_COLORS = {
  bug: '#ef4444', feature: '#3b82f6', billing: '#f59e0b',
  support: '#8b5cf6', performance: '#06b6d4', security: '#f97316', general: '#6b7280',
};

const pill = (cat) => ({
  display: 'inline-block', padding: '2px 10px', borderRadius: 20,
  fontSize: 11, fontWeight: 600,
  background: (CATEGORY_COLORS[cat] || '#6b7280') + '22',
  color: CATEGORY_COLORS[cat] || '#6b7280',
});

const sentPill = (s) => ({
  display: 'inline-block', padding: '2px 10px', borderRadius: 20,
  fontSize: 11, fontWeight: 600,
  background: (SENTIMENT_COLOR[s] || '#94a3b8') + '22',
  color: SENTIMENT_COLOR[s] || '#94a3b8',
});

// ── sub-components ────────────────────────────────────────

function StatCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 12, padding: '16px 20px',
      border: '1px solid #e2e8f0', flex: 1, minWidth: 220,
    }}>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || '#1a1a2e' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function FeedbackRow({ item }) {
  const displayText = item.text || item.raw_text || '';
  return (
    <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
      <td style={{ padding: '12px 10px', color: '#94a3b8', fontSize: 12 }}>#{item.id}</td>
      <td style={{ padding: '12px 10px', maxWidth: 340 }}>
        <span style={{ fontSize: 13, color: '#334155', wordBreak: 'break-word' }}>
          {displayText.length > 120 ? displayText.slice(0, 120) + '…' : displayText}
        </span>
      </td>
      <td style={{ padding: '12px 10px' }}>
        <span style={pill(item.category)}>{item.category}</span>
      </td>
      <td style={{ padding: '12px 10px' }}>
        <span style={sentPill(item.sentiment)}>{item.sentiment}</span>
      </td>
      <td style={{ padding: '12px 10px', fontSize: 11, color: '#94a3b8' }}>
        {item.source}
      </td>
      <td style={{ padding: '12px 10px', fontSize: 11, color: '#94a3b8' }}>
        {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
      </td>
    </tr>
  );
}

// ── Fallback Mock Data ────────────────────────────────────
const MOCK_STATS = {
  total: 5,
  categories: { bug: 2, feature: 1, billing: 1, performance: 1 },
  sentiments: { negative: 3, positive: 1, neutral: 1 }
};

const MOCK_FEEDBACK = [
  { id: 101, text: "The application throws a memory access exception when compiling massive image layers.", category: "bug", sentiment: "negative", confidence: 0.94, source: "api", created_at: new Date().toISOString() },
  { id: 102, text: "We deeply require a responsive dark-mode theme to alleviate eyesore during late-night reviews.", category: "feature", sentiment: "neutral", confidence: 0.88, source: "webhook", created_at: new Date().toISOString() },
  { id: 103, text: "Your merchant ledger overcharged our account statement on line item #4032. Please process a reversal.", category: "billing", sentiment: "negative", confidence: 0.99, source: "email", created_at: new Date().toISOString() },
  { id: 104, text: "This updated telemetry processor implementation is fantastic. It halved our analytical execution lag!", category: "performance", sentiment: "positive", confidence: 0.97, source: "intercom", created_at: new Date().toISOString() }
];

// ── main app ──────────────────────────────────────────────

export default function App() {
  const [feedback, setFeedback]   = useState(MOCK_FEEDBACK);
  const [stats, setStats]         = useState(MOCK_STATS);
  const [text, setText]           = useState('');
  const [source, setSource]       = useState('api');
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg] = useState('');
  const [filterCat, setFilterCat] = useState('');
  const [filterSent, setFilterSent] = useState('');
  const [loading, setLoading]     = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  const loadFeedback = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({ limit: 100 });
    if (filterCat)  params.append('category', filterCat);
    if (filterSent) params.append('sentiment', filterSent);
    try {
      const r = await fetch(`${API}/feedback?${params}`);
      if (r.ok) {
        const d = await r.json();
        setFeedback(d.items || MOCK_FEEDBACK);
      }
    } catch (err) {
      console.warn("Using local ledger fallback—backend endpoint offline.");
    } finally {
      setLoading(false);
    }
  }, [filterCat, filterSent]);

  const loadStats = useCallback(async () => {
    try {
      const r = await fetch(`${API}/stats?hours=24`);
      if (r.ok) {
        setStats(await r.json());
      }
    } catch (err) {
      console.warn("Using local metrics metrics fallback—backend cluster syncing.");
    }
  }, []);

  useEffect(() => { 
    loadFeedback(); 
    loadStats(); 
  }, [loadFeedback, loadStats]);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setSubmitting(true);
    setSubmitMsg('');
    try {
      const r = await fetch(`${API}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim(), source }),
      });
      if (r.ok) {
        setSubmitMsg('Queued for pipeline processing!');
        setText('');
        setTimeout(() => { loadFeedback(); loadStats(); setSubmitMsg(''); }, 1800);
      } else {
        setSubmitMsg('Error — Server rejected validation rules.');
      }
    } catch {
      setSubmitMsg('Local Mode: Queued mockup task entry.');
      const newMock = {
        id: feedback.length + 101,
        text: text.trim(),
        category: "general",
        sentiment: "neutral",
        confidence: 0.50,
        source: source,
        created_at: new Date().toISOString()
      };
      setFeedback([newMock, ...feedback]);
      setText('');
      setTimeout(() => setSubmitMsg(''), 2000);
    } finally {
      setSubmitting(false);
    }
  };

  // Prepare chart data records safely
  const catData = stats && stats.categories
    ? Object.entries(stats.categories).map(([name, value]) => ({ name, value }))
    : [];
  const sentData = stats && stats.sentiments
    ? Object.entries(stats.sentiments).map(([name, value]) => ({ name, value }))
    : [];

  const totalItems   = stats?.total || 0;
  const positivePct  = stats && totalItems > 0
    ? Math.round(((stats.sentiments?.positive || 0) / totalItems) * 100)
    : 0;
  const negativePct  = stats && totalItems > 0
    ? Math.round(((stats.sentiments?.negative || 0) / totalItems) * 100)
    : 0;

  const tabStyle = (t) => ({
    padding: '16px 20px', border: 'none', background: 'none',
    cursor: 'pointer', fontSize: 14, fontWeight: activeTab === t ? 600 : 400,
    color: activeTab === t ? '#3b82f6' : '#64748b',
    borderBottom: activeTab === t ? '2px solid #3b82f6' : '2px solid transparent',
    transition: 'all 0.2s ease',
  });

  return (
    <div style={{ minHeight: '100vh', background: '#f8f9fa' }}>
      {/* Navigation Bar */}
      <div style={{
        background: '#fff', borderBottom: '1px solid #e2e8f0',
        padding: '0 32px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 700, fontSize: 14,
          }}>FI</div>
          <span style={{ fontWeight: 700, fontSize: 18, color: '#0f172a' }}>Feedback Intelligence</span>
        </div>
        <div style={{ display: 'flex' }}>
          {['dashboard', 'submit', 'data'].map(t => (
            <button key={t} style={tabStyle(t)} onClick={() => setActiveTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
        <button
          onClick={() => { loadFeedback(); loadStats(); }}
          style={{
            padding: '6px 14px', borderRadius: 8, border: '1px solid #e2e8f0',
            background: '#fff', cursor: 'pointer', fontSize: 13, color: '#475569',
            fontWeight: 500, boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}
        >
          Refresh Data
        </button>
      </div>

      <div style={{ padding: '28px 32px', maxWidth: 1200, margin: '0 auto' }}>

        {/* ── DASHBOARD TAB ── */}
        {activeTab === 'dashboard' && (
          <>
            {/* Stat counts row layout */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 28, flexWrap: 'wrap' }}>
              <StatCard label="Total Vol (Last 24h)" value={totalItems} sub="feedback payloads" color="#3b82f6" />
              <StatCard label="Positive Sentiment Ratio" value={`${positivePct}%`} sub={`${stats?.sentiments?.positive || 0} units`} color="#22c55e" />
              <StatCard label="Negative Sentiment Ratio" value={`${negativePct}%`} sub={`${stats?.sentiments?.negative || 0} units`} color="#ef4444" />
              <StatCard label="Active Classes" value={catData.length} sub="distinct taxonomies" color="#8b5cf6" />
            </div>

            {/* Visual Analytics Split Panes */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 28 }}>
              {/* Category distribution mapping chart */}
              <div style={{ background: '#fff', borderRadius: 12, padding: 20, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 16, color: '#0f172a' }}>
                  Feedback Volume by Classification
                </div>
                {catData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220} minHeight={220}>
                    <BarChart data={catData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
                      <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                      <Tooltip cursor={{ fill: '#f8fafc' }} />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {catData.map((entry) => (
                          <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] || '#6b7280'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', fontSize: 13 }}>
                    No feedback data currently processing in this window.
                  </div>
                )}
              </div>

              {/* Directional Sentiment Pie Charts */}
              <div style={{ background: '#fff', borderRadius: 12, padding: 20, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 16, color: '#0f172a' }}>
                  Overall Sentiment Distribution
                </div>
                {sentData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220} minHeight={220}>
                    <PieChart>
                      <Pie data={sentData} dataKey="value" nameKey="name"
                        cx="50%" cy="50%" outerRadius={75} label={({ name, percent }) =>
                          `${name} ${(percent * 100).toFixed(0)}%`
                        } labelLine={false} style={{ fontSize: 12, fontWeight: 500 }}>
                        {sentData.map((entry) => (
                          <Cell key={entry.name} fill={SENTIMENT_COLOR[entry.name] || '#94a3b8'} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', fontSize: 13 }}>
                    No sentiment metrics generated yet.
                  </div>
                )}
              </div>
            </div>

            {/* Recent context tracking table container */}
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', fontWeight: 600, fontSize: 14, color: '#0f172a' }}>
                Recent Operational Feedback Events
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f8fafc' }}>
                      {['ID', 'Text Segment', 'Category Class', 'Sentiment', 'Source Channel', 'Ingested Time'].map(h => (
                        <th key={h} style={{ padding: '12px 10px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '.04em' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {feedback.slice(0, 10).map(item => (
                      <FeedbackRow key={item.id} item={item} />
                    ))}
                    {feedback.length === 0 && (
                      <tr><td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
                        No ingestion streams recorded. Navigate to the Submit pane to populate.
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* ── SUBMIT TAB ── */}
        {activeTab === 'submit' && (
          <div style={{ maxWidth: 650 }}>
            <div style={{ background: '#fff', borderRadius: 12, padding: 28, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
              <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4, color: '#0f172a' }}>
                Manual Feedback Payload Ingestion
              </div>
              <div style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>
                Submitted string entries trigger deep contextual parsing, text stabilization, and third-party alert dispatches automatically.
              </div>

              <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 6 }}>Raw Feedback Content</label>
              <textarea
                rows={5}
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="Describe systemic system performance, error messaging anomalies, invoicing discrepancies, or custom interface suggestions..."
                style={{
                  width: '100%', padding: '12px 14px', borderRadius: 8,
                  border: '1px solid #e2e8f0', fontSize: 14, resize: 'vertical',
                  fontFamily: 'inherit', color: '#0f172a', outline: 'none',
                  boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)'
                }}
              />

              <div style={{ display: 'flex', flexDirection: 'column', width: 200, marginTop: 16 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>Ingestion Vector Source</label>
                <select
                  value={source}
                  onChange={e => setSource(e.target.value)}
                  style={{
                    padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0',
                    fontSize: 13, color: '#0f172a', background: '#fff', outline: 'none',
                  }}
                >
                  {['api', 'webhook', 'email', 'typeform', 'intercom', 'zendesk', 'batch'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 16 }}>
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !text.trim()}
                  style={{
                    padding: '10px 24px', borderRadius: 8, border: 'none',
                    background: submitting || !text.trim() ? '#cbd5e1' : '#3b82f6',
                    color: '#fff', fontWeight: 600, fontSize: 14,
                    cursor: submitting || !text.trim() ? 'not-allowed' : 'pointer',
                    boxShadow: '0 1px 2px rgba(59,130,246,0.2)'
                  }}
                >
                  {submitting ? 'Streaming payload...' : 'Ingest Feedback'}
                </button>
                {submitMsg && (
                  <span style={{ fontSize: 13, fontWeight: 500, color: submitMsg.includes('Error') || submitMsg.includes('Cannot') ? '#ef4444' : '#22c55e' }}>
                    {submitMsg}
                  </span>
                )}
              </div>
            </div>

            {/* Quick Test Vectors Panel */}
            <div style={{ marginTop: 20, background: '#fff', borderRadius: 12, padding: 20, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#334155' }}>
                Automated Analytical Evaluation Matrices
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  "The application throws a memory access exception when compiling massive image layers.",
                  "We deeply require a responsive dark-mode theme to alleviate eyesore during late-night reviews.",
                  "Your merchant ledger overcharged our account statement on line item #4032. Please process a reversal.",
                  "This updated telemetry processor implementation is fantastic. It halved our analytical execution lag!",
                  "Where do I provision structural API authorization header codes to bind a custom webhook client?"
                ].map(sample => (
                  <button key={sample} onClick={() => setText(sample)} style={{
                    textAlign: 'left', padding: '10px 14px', borderRadius: 8,
                    border: '1px solid #e2e8f0', background: '#f8fafc',
                    cursor: 'pointer', fontSize: 12, color: '#475569',
                    transition: 'background 0.15s ease'
                  }} onMouseOver={e => e.currentTarget.style.background = '#f1f5f9'} onMouseOut={e => e.currentTarget.style.background = '#f8fafc'}>
                    {sample}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── DATA TAB ── */}
        {activeTab === 'data' && (
          <>
            {/* Filters Dashboard Panel */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
              <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
                style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13, background: '#fff', outline: 'none' }}>
                <option value="">All Category Classes</option>
                {['bug','feature','billing','support','performance','security','general'].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <select value={filterSent} onChange={e => setFilterSent(e.target.value)}
                style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13, background: '#fff', outline: 'none' }}>
                <option value="">All Sentiment Valuations</option>
                {['positive','negative','neutral'].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <button onClick={loadFeedback}
                style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid #cbd5e1', background: '#fff', cursor: 'pointer', fontSize: 13, color: '#334155', fontWeight: 500 }}>
                Execute Filter Sequence
              </button>
              <span style={{ fontSize: 13, color: '#64748b', alignSelf: 'center', marginLeft: 'auto', fontWeight: 500 }}>
                Total Records Returned: <strong style={{ color: '#0f172a' }}>{feedback.length}</strong>
              </span>
            </div>

            {/* Master Ledger Layout */}
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f8fafc' }}>
                      {['ID', 'Feedback text', 'Category', 'Sentiment', 'Confidence Index', 'Source', 'System Ingest Time'].map(h => (
                        <th key={h} style={{ padding: '12px 10px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '.04em', whiteSpace: 'nowrap' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {loading && (
                      <tr><td colSpan={7} style={{ padding: 40, textAlign: 'center', color: '#64748b', fontWeight: 500 }}>Syncing ledger assets...</td></tr>
                    )}
                    {!loading && feedback.map(item => {
                      const displayBody = item.text || item.raw_text || '';
                      return (
                        <tr key={item.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '12px 10px', color: '#94a3b8', fontSize: 12 }}>#{item.id}</td>
                          <td style={{ padding: '12px 10px', maxWidth: 300, fontSize: 13, color: '#334155', wordBreak: 'break-word' }}>
                            {displayBody.length > 100 ? displayBody.slice(0, 100) + '…' : displayBody}
                          </td>
                          <td style={{ padding: '12px 10px' }}>
                            <span style={pill(item.category)}>{item.category}</span>
                          </td>
                          <td style={{ padding: '12px 10px' }}>
                            <span style={sentPill(item.sentiment)}>{item.sentiment}</span>
                          </td>
                          <td style={{ padding: '12px 10px', fontSize: 12, color: '#475569', fontWeight: 600 }}>
                            {Math.round((item.confidence || 0) * 100)}%
                          </td>
                          <td style={{ padding: '12px 10px', fontSize: 12, color: '#64748b' }}>
                            {item.source}
                          </td>
                          <td style={{ padding: '12px 10px', fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap' }}>
                            {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                          </td>
                        </tr>
                      );
                    })}
                    {!loading && feedback.length === 0 && (
                      <tr><td colSpan={7} style={{ padding: 48, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
                        No records matched your specific filter sequences. Try recalibrating options or clearing parameters.
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}