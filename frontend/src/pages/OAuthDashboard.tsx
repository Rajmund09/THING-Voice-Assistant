/**
 * OAuthDashboard.tsx — THING Phase 4A
 * Service connection cards UI for OAuth integrations.
 * Displays Google, Spotify, Slack, Microsoft, and Notion with connect/disconnect controls.
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plug, RefreshCw, CheckCircle2, XCircle, ExternalLink } from 'lucide-react';

const SERVER_URL = 'http://localhost:5000';

// ── Service Definitions ───────────────────────────────────────────────
interface ServiceDef {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  color: string;
  gradient: string;
  icon: string;
}

const SERVICES: ServiceDef[] = [
  {
    id: 'google',
    name: 'Google',
    description: 'Connect Google to access your Calendar and unlock voice-powered scheduling.',
    capabilities: [
      "What's on my calendar today?",
      "Do I have meetings tomorrow?",
      "Schedule a team sync at 3pm",
      "Show my events this week",
    ],
    color: '#4285F4',
    gradient: 'linear-gradient(135deg, #4285F4 0%, #34A853 100%)',
    icon: '🗓️',
  },
  {
    id: 'spotify',
    name: 'Spotify',
    description: 'Control Spotify playback via SDK — no browser windows, instant response.',
    capabilities: [
      "Play Blinding Lights on Spotify",
      "Play my Discover Weekly",
      "Pause Spotify",
      "Skip on Spotify",
    ],
    color: '#1DB954',
    gradient: 'linear-gradient(135deg, #1DB954 0%, #191414 100%)',
    icon: '🎵',
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Send messages and read channels in your Slack workspace via API.',
    capabilities: [
      "Send slack message to #general saying hello",
      "Read last 5 messages in #dev",
      "List my Slack channels",
      "Post in #random: happy friday",
    ],
    color: '#4A154B',
    gradient: 'linear-gradient(135deg, #4A154B 0%, #E01E5A 100%)',
    icon: '💬',
  },
  {
    id: 'microsoft',
    name: 'Microsoft',
    description: 'Access Outlook, Teams, and OneDrive with Microsoft identity integration.',
    capabilities: [
      "Read my Outlook emails",
      "Check my Teams calendar",
      "List OneDrive files",
    ],
    color: '#00A4EF',
    gradient: 'linear-gradient(135deg, #00A4EF 0%, #FFB900 100%)',
    icon: '🪟',
  },
  {
    id: 'notion',
    name: 'Notion',
    description: 'Read and write Notion pages and databases from THING voice commands.',
    capabilities: [
      "Add a task to my Notion inbox",
      "Search my Notion workspace",
      "Read my project notes",
    ],
    color: '#000000',
    gradient: 'linear-gradient(135deg, #374151 0%, #111827 100%)',
    icon: '📝',
  },
];

// ── Types ─────────────────────────────────────────────────────────────
type ConnectionStatus = Record<string, boolean>;

interface OAuthDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  socket?: any;
}

// ── Component ─────────────────────────────────────────────────────────
export default function OAuthDashboard({ isOpen, onClose, socket }: OAuthDashboardProps) {
  const [status, setStatus] = useState<ConnectionStatus>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [polling, setPolling] = useState<string | null>(null);
  const [error, setError] = useState<string>('');

  // ── Fetch connection status ─────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${SERVER_URL}/oauth/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // Backend offline — statuses remain as-is
    }
  }, []);

  useEffect(() => {
    if (isOpen) fetchStatus();
  }, [isOpen, fetchStatus]);

  // ── Socket events for real-time status updates ──────────────────────
  useEffect(() => {
    if (!socket) return;
    const onConnected = (data: { service: string }) => {
      setStatus(prev => ({ ...prev, [data.service]: true }));
      setPolling(null);
      setLoading(null);
    };
    const onDisconnected = (data: { service: string }) => {
      setStatus(prev => ({ ...prev, [data.service]: false }));
    };
    socket.on('oauth_connected', onConnected);
    socket.on('oauth_disconnected', onDisconnected);
    return () => {
      socket.off('oauth_connected', onConnected);
      socket.off('oauth_disconnected', onDisconnected);
    };
  }, [socket]);

  // ── Poll after connect click (fallback if WebSocket not available) ──
  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${SERVER_URL}/oauth/status`);
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
          if (data[polling]) {
            setPolling(null);
            setLoading(null);
            clearInterval(interval);
          }
        }
      } catch {
        // ignore
      }
    }, 2000);
    // Auto-stop polling after 2 minutes
    const timeout = setTimeout(() => {
      clearInterval(interval);
      setPolling(null);
      setLoading(null);
    }, 120_000);
    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [polling]);

  // ── Connect handler ─────────────────────────────────────────────────
  const handleConnect = async (serviceId: string) => {
    setError('');
    setLoading(serviceId);
    try {
      const res = await fetch(`${SERVER_URL}/oauth/start/${serviceId}`);
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Failed to start OAuth flow.');
        setLoading(null);
        return;
      }
      // Start polling for token completion
      setPolling(serviceId);
    } catch {
      setError('Could not reach THING backend. Make sure python main.py is running.');
      setLoading(null);
    }
  };

  // ── Disconnect handler ──────────────────────────────────────────────
  const handleDisconnect = async (serviceId: string) => {
    setLoading(serviceId);
    try {
      await fetch(`${SERVER_URL}/oauth/disconnect/${serviceId}`, { method: 'DELETE' });
      setStatus(prev => ({ ...prev, [serviceId]: false }));
    } catch {
      setError('Disconnect failed. Check backend connection.');
    } finally {
      setLoading(null);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(12px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 16 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-3xl"
            style={{
              background: 'rgba(10,10,18,0.98)',
              border: '1px solid rgba(0,229,255,0.12)',
              boxShadow: '0 24px 80px rgba(0,0,0,0.8), 0 0 0 1px rgba(0,229,255,0.05)',
            }}
          >
            {/* ── Header ───────────────────────────────────────────────── */}
            <div
              className="sticky top-0 flex items-center justify-between px-8 py-5 z-10"
              style={{
                background: 'rgba(10,10,18,0.95)',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
                backdropFilter: 'blur(20px)',
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center"
                  style={{
                    background: 'rgba(0,229,255,0.08)',
                    border: '1px solid rgba(0,229,255,0.15)',
                  }}
                >
                  <Plug size={16} style={{ color: '#00e5ff' }} />
                </div>
                <div>
                  <h2
                    className="text-lg font-black"
                    style={{ fontFamily: 'Syne, sans-serif', color: '#fff' }}
                  >
                    Integrations
                  </h2>
                  <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    Connect services to unlock voice-powered SDK control
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fetchStatus}
                  title="Refresh status"
                  className="w-8 h-8 flex items-center justify-center rounded-xl transition-all hover:bg-white/5"
                  style={{ color: 'rgba(255,255,255,0.3)', border: '1px solid rgba(255,255,255,0.06)' }}
                >
                  <RefreshCw size={14} />
                </button>
                <button
                  onClick={onClose}
                  className="w-8 h-8 flex items-center justify-center rounded-xl transition-all hover:bg-white/5"
                  style={{ color: 'rgba(255,255,255,0.3)', border: '1px solid rgba(255,255,255,0.06)' }}
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* ── Error Banner ─────────────────────────────────────────── */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mx-6 mt-4 px-4 py-3 rounded-xl text-sm flex items-center justify-between gap-3"
                  style={{
                    background: 'rgba(239,68,68,0.08)',
                    border: '1px solid rgba(239,68,68,0.2)',
                    color: '#f87171',
                  }}
                >
                  <span>{error}</span>
                  <button onClick={() => setError('')} className="shrink-0 opacity-60 hover:opacity-100">
                    <X size={13} />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Service Cards ─────────────────────────────────────────── */}
            <div className="grid grid-cols-1 gap-4 p-6">
              {SERVICES.map((svc) => {
                const connected = !!status[svc.id];
                const isLoading = loading === svc.id;
                const isWaiting = polling === svc.id;

                return (
                  <motion.div
                    key={svc.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: SERVICES.indexOf(svc) * 0.05 }}
                    className="relative overflow-hidden rounded-2xl p-5 flex gap-4"
                    style={{
                      background: connected
                        ? 'rgba(0,230,118,0.04)'
                        : 'rgba(255,255,255,0.02)',
                      border: `1px solid ${connected ? 'rgba(0,230,118,0.2)' : 'rgba(255,255,255,0.06)'}`,
                      transition: 'all 0.3s ease',
                    }}
                  >
                    {/* Accent strip */}
                    <div
                      className="absolute left-0 top-0 bottom-0 w-1 rounded-l-2xl"
                      style={{
                        background: connected ? svc.gradient : 'rgba(255,255,255,0.06)',
                        opacity: connected ? 1 : 0.4,
                        transition: 'all 0.3s ease',
                      }}
                    />

                    {/* Service icon */}
                    <div
                      className="shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                      style={{
                        background: connected
                          ? `${svc.color}18`
                          : 'rgba(255,255,255,0.04)',
                        border: `1px solid ${connected ? svc.color + '30' : 'rgba(255,255,255,0.06)'}`,
                        transition: 'all 0.3s ease',
                      }}
                    >
                      {svc.icon}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className="font-bold text-sm"
                          style={{ color: connected ? '#fff' : 'rgba(255,255,255,0.7)' }}
                        >
                          {svc.name}
                        </span>
                        {connected && (
                          <span
                            className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full"
                            style={{
                              background: 'rgba(0,230,118,0.12)',
                              color: '#00e676',
                              border: '1px solid rgba(0,230,118,0.2)',
                            }}
                          >
                            <CheckCircle2 size={9} /> Connected
                          </span>
                        )}
                        {isWaiting && (
                          <span
                            className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full animate-pulse"
                            style={{
                              background: 'rgba(251,191,36,0.12)',
                              color: '#fbbf24',
                              border: '1px solid rgba(251,191,36,0.2)',
                            }}
                          >
                            Waiting for auth…
                          </span>
                        )}
                      </div>

                      <p
                        className="text-xs mb-3 leading-relaxed"
                        style={{ color: 'rgba(255,255,255,0.35)' }}
                      >
                        {svc.description}
                      </p>

                      {/* Capabilities chips */}
                      <div className="flex flex-wrap gap-1.5">
                        {svc.capabilities.map((cap) => (
                          <span
                            key={cap}
                            className="text-[10px] px-2 py-0.5 rounded-lg font-mono"
                            style={{
                              background: 'rgba(255,255,255,0.04)',
                              border: '1px solid rgba(255,255,255,0.06)',
                              color: 'rgba(255,255,255,0.3)',
                            }}
                          >
                            "{cap}"
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Action button */}
                    <div className="shrink-0 flex items-center">
                      {connected ? (
                        <button
                          id={`oauth-disconnect-${svc.id}`}
                          onClick={() => handleDisconnect(svc.id)}
                          disabled={isLoading}
                          className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all hover:bg-red-500/10 active:scale-95 disabled:opacity-50"
                          style={{
                            color: '#f87171',
                            border: '1px solid rgba(239,68,68,0.2)',
                          }}
                        >
                          {isLoading ? (
                            <RefreshCw size={12} className="animate-spin" />
                          ) : (
                            <XCircle size={12} />
                          )}
                          Disconnect
                        </button>
                      ) : (
                        <button
                          id={`oauth-connect-${svc.id}`}
                          onClick={() => handleConnect(svc.id)}
                          disabled={isLoading || isWaiting}
                          className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
                          style={{
                            background: isWaiting
                              ? 'rgba(251,191,36,0.08)'
                              : `${svc.color}14`,
                            border: `1px solid ${isWaiting ? 'rgba(251,191,36,0.3)' : svc.color + '40'}`,
                            color: isWaiting ? '#fbbf24' : svc.color,
                          }}
                        >
                          {isLoading ? (
                            <RefreshCw size={12} className="animate-spin" />
                          ) : isWaiting ? (
                            <RefreshCw size={12} className="animate-spin" />
                          ) : (
                            <ExternalLink size={12} />
                          )}
                          {isWaiting ? 'Authorizing…' : 'Connect'}
                        </button>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* ── Footer hint ──────────────────────────────────────────── */}
            <div
              className="px-8 pb-6 text-center"
              style={{ color: 'rgba(255,255,255,0.15)', fontSize: 11 }}
            >
              Tokens are stored encrypted locally. THING never shares your credentials.
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
