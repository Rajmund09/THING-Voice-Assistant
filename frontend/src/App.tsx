/**
 * App.tsx — THING v4.0
 * Root component. Orchestrates layout, socket state, and component tree.
 * Single source of truth: all display state flows from useSocket hook.
 */

import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useSocket } from './hooks/useSocket';
import VoiceOrb from './components/VoiceOrb';
import ChatWindow from './components/ChatWindow';
import InputBar from './components/InputBar';
import Sidebar from './components/Sidebar';
import SettingsPanel from './components/SettingsPanel';
import MemoryDashboard from './components/MemoryDashboard';
import { Settings } from 'lucide-react';

const SERVER_URL = 'http://localhost:5000';

export default function App() {
  const { messages, status, connected, profile, sendCommand, stopSpeaking, updateVoiceSettings, fetchProfile, clearMessages, emitEvent } =
    useSocket(SERVER_URL);

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [voiceSettings, setVoiceSettings] = useState({
    gender: 'male',
    language: 'en-IN',
    rate: 0,
    pitch: 0,
    volume: 0
  });

  const handleVoiceSettingsChange = (newSettings: any) => {
    const updated = { ...voiceSettings, ...newSettings };
    setVoiceSettings(updated);
    
    // Map numerical values to string percentages for edge-tts
    const payload = {
      ...updated,
      rate: `${updated.rate >= 0 ? '+' : ''}${updated.rate * 10}%`,
      pitch: `${updated.pitch >= 0 ? '+' : ''}${updated.pitch}Hz`,
      volume: `${updated.volume >= 0 ? '+' : ''}${updated.volume * 10}%`
    };
    updateVoiceSettings(payload);
  };

  const isProcessing = status.state === 'processing';
  const isSpeaking = status.state === 'speaking';

  return (
    <div
      className="h-screen w-screen overflow-hidden flex flex-col"
      style={{
        background: 'radial-gradient(ellipse 80% 60% at 50% -10%, rgba(0,229,255,0.05) 0%, transparent 60%), var(--clr-bg)',
      }}
    >
      {/* ── Grid noise overlay ─────────────────────────────────── */}
      <div className="absolute inset-0 pointer-events-none opacity-30"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />

      {/* ── Main layout ────────────────────────────────────────── */}
      <div className="relative flex h-full gap-3 p-3 overflow-hidden">

        {/* ── Sidebar ─────────────────────────────────────────── */}
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(o => !o)}
          messages={messages}
          onNewChat={clearMessages}
          onOpenSettings={() => setSettingsOpen(true)}
          onOpenMemory={() => {
            fetchProfile();
            setMemoryOpen(true);
          }}
        />

        {/* ── Dashboard Overlay ────────────────────────────────── */}
        <AnimatePresence>
          {memoryOpen && (
            <MemoryDashboard 
              isOpen={memoryOpen} 
              onClose={() => setMemoryOpen(false)} 
              profile={profile} 
            />
          )}
        </AnimatePresence>

        {/* ── Center: Voice Orb ───────────────────────────────── */}
        <div
          className="glass flex flex-col items-center justify-center rounded-2xl shrink-0 relative overflow-hidden"
          style={{
            width: 320,
            minWidth: 280,
            transition: 'width 0.3s ease',
          }}
        >
          {/* Ambient glow top */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 rounded-full pointer-events-none"
            style={{
              background: 'radial-gradient(circle, rgba(0,229,255,0.06) 0%, transparent 70%)',
              filter: 'blur(20px)',
            }}
          />

          {/* Header */}
          <div className="absolute top-0 left-0 right-0 px-5 py-4 flex items-center justify-between">
            <div>
              <h1 className="text-lg font-black gradient-text" style={{ fontFamily: 'Syne, sans-serif' }}>
                THING.AI
              </h1>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full"
                  style={{ background: connected ? '#00e676' : '#ff4444',
                           boxShadow: connected ? '0 0 6px #00e676' : 'none' }} />
                <span className="text-[10px] font-medium uppercase tracking-widest"
                  style={{ color: 'rgba(255,255,255,0.3)' }}>
                  {connected ? 'Online' : 'Offline'}
                </span>
              </div>
            </div>
            <button onClick={() => setSettingsOpen(true)}
              className="w-8 h-8 rounded-xl flex items-center justify-center transition-all hover:bg-white/10 active:scale-95"
              style={{ color: 'rgba(255,255,255,0.3)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Settings size={15} />
            </button>
          </div>

          {/* Voice Orb */}
          <VoiceOrb state={status.state} statusText={status.text} />

          {/* Connection warning */}
          {!connected && (
            <div className="absolute bottom-6 left-4 right-4 px-4 py-2.5 rounded-xl text-center text-xs"
              style={{
                background: 'rgba(255,68,68,0.08)',
                border: '1px solid rgba(255,68,68,0.2)',
                color: '#f87171',
              }}>
              Backend offline — start <code className="font-mono">python main.py</code>
            </div>
          )}
        </div>

        {/* ── Right: Chat panel ──────────────────────────────── */}
        <div className="glass flex flex-col flex-1 rounded-2xl overflow-hidden relative">

          {/* Chat header */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b shrink-0"
            style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
            <div className="flex items-center gap-2.5">
              <div className="w-2 h-2 rounded-full"
                style={{
                  background: isProcessing ? '#a78bfa' : isSpeaking ? '#00e676' : 'rgba(0,229,255,0.4)',
                  boxShadow: isProcessing ? '0 0 8px #a78bfa' : isSpeaking ? '0 0 8px #00e676' : 'none',
                }} />
              <span className="text-xs font-semibold uppercase tracking-widest"
                style={{ color: 'rgba(255,255,255,0.4)' }}>
                {isProcessing ? 'Processing…' : isSpeaking ? 'Speaking…' : 'Conversation Log'}
              </span>
            </div>
            {messages.length > 0 && (
              <button onClick={clearMessages}
                className="text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-lg transition-all hover:bg-white/5"
                style={{ color: 'rgba(255,255,255,0.2)' }}>
                Clear
              </button>
            )}
          </div>

          {/* Messages */}
          <ChatWindow 
            messages={messages} 
            isProcessing={isProcessing} 
            onAction={sendCommand}
            onEmit={emitEvent}
          />

          {/* Input bar */}
          <div className="border-t shrink-0" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
            <InputBar
              onSend={sendCommand}
              onStop={stopSpeaking}
              isSpeaking={isSpeaking}
              disabled={!connected}
            />
          </div>
        </div>

        {/* ── Settings panel (absolute overlay) ──────────────── */}
        <AnimatePresence>
          {settingsOpen && (
            <div className="absolute inset-0 z-40 rounded-2xl overflow-hidden">
              <SettingsPanel
                isOpen={settingsOpen}
                onClose={() => setSettingsOpen(false)}
                connected={connected}
                voiceSettings={voiceSettings}
                onSettingsChange={handleVoiceSettingsChange}
              />
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
