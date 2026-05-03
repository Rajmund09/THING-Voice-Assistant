/**
 * SettingsPanel.tsx — THING Jarvis Upgrade
 * Premium settings panel for Neural TTS and system status.
 */

import { motion } from 'framer-motion';
import { X, Zap, Wifi, Shield, Cpu, Volume2, Mic, Globe, User, Activity } from 'lucide-react';

interface VoiceSettings {
  gender: string;
  language: string;
  rate: number;
  pitch: number;
  volume: number;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  connected: boolean;
  voiceSettings: VoiceSettings;
  onSettingsChange: (settings: Partial<VoiceSettings>) => void;
}

export default function SettingsPanel({ isOpen, onClose, connected, voiceSettings, onSettingsChange }: Props) {
  if (!isOpen) return null;

  return (
    <>
      <motion.div
        className="absolute inset-0 z-40"
        style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />

      <motion.div
        className="absolute right-0 top-0 bottom-0 z-50 glass-strong flex flex-col overflow-hidden"
        style={{ width: 340, borderRadius: '0 24px 24px 0' }}
        initial={{ x: 340 }}
        animate={{ x: 0 }}
        exit={{ x: 340 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b"
          style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight" style={{ fontFamily: 'Syne, sans-serif' }}>System Settings</h2>
            <p className="text-[10px] text-zinc-500 mt-0.5">Configure your Jarvis experience</p>
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center transition-colors hover:bg-white/10"
            style={{ color: 'rgba(255,255,255,0.4)' }}>
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8 custom-scrollbar">
          
          {/* Voice Profile */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <User size={14} className="text-cyan-400" />
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)' }}>Voice Profile</p>
            </div>
            
            <div className="grid grid-cols-2 gap-2">
              {['male', 'female'].map(g => (
                <button
                  key={g}
                  onClick={() => onSettingsChange({ gender: g })}
                  className={`py-3 rounded-xl border text-xs font-medium transition-all ${
                    voiceSettings.gender === g 
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(0,242,255,0.1)]' 
                    : 'bg-white/5 border-white/5 text-zinc-500 hover:bg-white/10'
                  }`}
                >
                  {g.charAt(0).toUpperCase() + g.slice(1)}
                </button>
              ))}
            </div>

            <button
              onClick={() => onSettingsChange({ preview: true } as any)}
              className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white/5 border border-white/5 text-[10px] font-bold uppercase tracking-widest text-zinc-400 hover:bg-white/10 transition-all"
            >
              <Volume2 size={12} />
              Preview {voiceSettings.gender} Voice
            </button>
          </section>

          {/* Language Selection */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Globe size={14} className="text-violet-400" />
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)' }}>Neural Language</p>
            </div>
            
            <select
              value={voiceSettings.language}
              onChange={(e) => onSettingsChange({ language: e.target.value })}
              className="w-full bg-white/5 border border-white/5 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-all appearance-none cursor-pointer"
            >
              <option value="en-IN" className="bg-zinc-900">English (India) - Hinglish</option>
              <option value="en-US" className="bg-zinc-900">English (US) - Pro</option>
              <option value="en-GB" className="bg-zinc-900">English (UK) - British</option>
              <option value="hi-IN" className="bg-zinc-900">Hindi (India)</option>
            </select>
          </section>

          {/* Speech Tuning */}
          <section className="space-y-6">
            <div className="flex items-center gap-2 mb-1">
              <Activity size={14} className="text-green-400" />
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)' }}>Speech Tuning</p>
            </div>

            {[
              { label: 'Speed', key: 'rate', min: -5, max: 5, color: '#22d3ee' },
              { label: 'Pitch', key: 'pitch', min: -20, max: 20, color: '#a78bfa' },
              { label: 'Volume', key: 'volume', min: -5, max: 5, color: '#4ade80' },
            ].map((s) => (
              <div key={s.label} className="space-y-3">
                <div className="flex justify-between text-[11px]">
                  <span className="text-zinc-500">{s.label}</span>
                  <span className="font-mono text-white">{(voiceSettings as any)[s.key] > 0 ? '+' : ''}{(voiceSettings as any)[s.key]}</span>
                </div>
                <input
                  type="range"
                  min={s.min}
                  max={s.max}
                  step="1"
                  value={(voiceSettings as any)[s.key]}
                  onChange={(e) => onSettingsChange({ [s.key]: Number(e.target.value) })}
                  className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                  style={{ accentColor: s.color }}
                />
              </div>
            ))}
          </section>

          {/* System Info */}
          <section className="pt-4 border-t border-white/5">
            <div className="space-y-3">
              {[
                { icon: Wifi, label: 'Neural Link', value: connected ? 'Online' : 'Offline', color: connected ? '#10b981' : '#ef4444' },
                { icon: Zap, label: 'Engine', value: 'Edge Neural TTS', color: '#22d3ee' },
                { icon: Shield, label: 'Privacy', value: 'Local Cache', color: '#818cf8' },
              ].map(({ icon: Icon, label, value, color }) => (
                <div key={label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Icon size={13} className="text-zinc-600" />
                    <span className="text-[11px] text-zinc-500">{label}</span>
                  </div>
                  <span className="text-[11px] font-semibold" style={{ color }}>{value}</span>
                </div>
              ))}
            </div>
          </section>

        </div>
        
        {/* Footer */}
        <div className="px-6 py-4 bg-white/5 border-t border-white/5 flex flex-col gap-3">
          <button 
            onClick={() => onSettingsChange({})} // Trigger re-save
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-cyan-500/10 text-[10px] font-bold uppercase tracking-widest text-cyan-400 hover:bg-cyan-500/20 transition-all border border-cyan-500/20"
          >
            <Zap size={12} />
            Recalibrate System
          </button>
          
          <p className="text-[9px] text-center text-zinc-600">
            Premium Neural Voices powered by Microsoft Edge Engine
          </p>
        </div>
      </motion.div>
    </>
  );
}
