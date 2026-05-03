/**
 * VoiceOrb.tsx — THING v4.0
 * Animated voice orb with 4 distinct states.
 * Idle → Listening → Thinking → Speaking
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff } from 'lucide-react';

type OrbState = 'idle' | 'listening' | 'processing' | 'speaking' | 'disconnected';

interface VoiceOrbProps {
  state: OrbState;
  statusText: string;
}

// ── State configs ─────────────────────────────────────────────────────────────
const STATE_CONFIG = {
  idle: {
    orbColor: 'radial-gradient(circle at 35% 35%, #0f172a, #020617)',
    borderColor: 'rgba(0, 242, 255, 0.15)',
    glowColor: 'rgba(0, 242, 255, 0.08)',
    labelColor: '#94a3b8',
    labelBg: 'rgba(255, 255, 255, 0.03)',
  },
  listening: {
    orbColor: 'radial-gradient(circle at 35% 35%, #003d52, #00141d)',
    borderColor: 'rgba(0, 242, 255, 0.8)',
    glowColor: 'rgba(0, 242, 255, 0.4)',
    labelColor: '#00f2ff',
    labelBg: 'rgba(0, 242, 255, 0.1)',
  },
  processing: {
    orbColor: 'radial-gradient(circle at 35% 35%, #2e1065, #0c0a09)',
    borderColor: 'rgba(139, 92, 246, 0.6)',
    glowColor: 'rgba(139, 92, 246, 0.3)',
    labelColor: '#a78bfa',
    labelBg: 'rgba(139, 92, 246, 0.1)',
  },
  speaking: {
    orbColor: 'radial-gradient(circle at 35% 35%, #064e3b, #020617)',
    borderColor: 'rgba(16, 185, 129, 0.6)',
    glowColor: 'rgba(16, 185, 129, 0.3)',
    labelColor: '#10b981',
    labelBg: 'rgba(16, 185, 129, 0.1)',
  },
  disconnected: {
    orbColor: 'radial-gradient(circle at 35% 35%, #450a0a, #020617)',
    borderColor: 'rgba(239, 68, 68, 0.4)',
    glowColor: 'rgba(239, 68, 68, 0.15)',
    labelColor: '#ef4444',
    labelBg: 'rgba(239, 68, 68, 0.1)',
  },
};

export default function VoiceOrb({ state, statusText }: VoiceOrbProps) {
  const cfg = STATE_CONFIG[state] ?? STATE_CONFIG.idle;

  return (
    <div className="flex flex-col items-center justify-center gap-8 select-none">

      {/* ── Orb Container ───────────────────────────────────────── */}
      <div className="relative flex items-center justify-center" style={{ width: 240, height: 240 }}>

        {/* Listening rings */}
        <AnimatePresence>
          {state === 'listening' && (
            <>
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="absolute rounded-full border"
                  style={{ borderColor: 'rgba(0,229,255,0.4)' }}
                  initial={{ scale: 0.8, opacity: 0.8 }}
                  animate={{ scale: 1.6 + i * 0.2, opacity: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: i * 0.5,
                    ease: 'easeOut',
                  }}
                  style={{
                    width: 160,
                    height: 160,
                    borderColor: 'rgba(0,229,255,0.35)',
                  }}
                />
              ))}
            </>
          )}
        </AnimatePresence>

        {/* Outer decorative ring */}
        <motion.div
          className="absolute rounded-full border border-dashed"
          style={{
            width: 220, height: 220,
            borderColor: cfg.borderColor,
            opacity: 0.4,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        />

        {/* Inner ring */}
        <motion.div
          className="absolute rounded-full border"
          style={{
            width: 185, height: 185,
            borderColor: cfg.borderColor,
            opacity: 0.25,
          }}
          animate={{ rotate: -360 }}
          transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
        />

        {/* Core orb */}
        <motion.div
          className="relative rounded-full flex items-center justify-center overflow-hidden"
          style={{
            width: 150, height: 150,
            background: cfg.orbColor,
            border: `1px solid ${cfg.borderColor}`,
            boxShadow: `0 0 60px ${cfg.glowColor}, 0 0 120px ${cfg.glowColor}, inset 0 1px 0 rgba(255,255,255,0.08)`,
          }}
          animate={
            state === 'idle'
              ? { scale: [1, 1.03, 1], opacity: [0.85, 1, 0.85] }
              : state === 'listening'
              ? { scale: [1, 1.05, 1] }
              : {}
          }
          transition={
            state === 'idle'
              ? { duration: 3, repeat: Infinity, ease: 'easeInOut' }
              : state === 'listening'
              ? { duration: 0.8, repeat: Infinity, ease: 'easeInOut' }
              : {}
          }
        >
          {/* Scanline effect */}
          <div
            className="absolute inset-0 pointer-events-none overflow-hidden rounded-full"
            style={{ opacity: 0.4 }}
          >
            <div
              className="w-full h-8 animate-scan"
              style={{
                background: `linear-gradient(transparent, ${cfg.glowColor}, transparent)`,
              }}
            />
          </div>

          {/* State content */}
          <AnimatePresence mode="wait">
            {state === 'disconnected' && (
              <motion.div key="disconnected"
                initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                <MicOff size={36} style={{ color: '#ef4444', opacity: 0.6 }} />
              </motion.div>
            )}

            {state === 'idle' && (
              <motion.div key="idle"
                initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                <Mic size={42} style={{ color: 'rgba(0,229,255,0.5)', strokeWidth: 1.5 }} />
              </motion.div>
            )}

            {state === 'listening' && (
              <motion.div key="listening"
                className="flex items-center justify-center"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <Mic size={42} style={{ color: '#00e5ff', strokeWidth: 1.5 }} />
              </motion.div>
            )}

            {state === 'processing' && (
              <motion.div key="processing"
                className="flex items-end justify-center gap-1.5"
                style={{ height: 40 }}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                {[0, 1, 2, 3, 4].map(i => (
                  <div
                    key={i}
                    className="rounded-full"
                    style={{
                      width: 5, height: 5,
                      background: '#a78bfa',
                      animation: `think-dot 1.2s ease-in-out infinite`,
                      animationDelay: `${i * 150}ms`,
                    }}
                  />
                ))}
              </motion.div>
            )}

            {state === 'speaking' && (
              <motion.div key="speaking"
                className="flex items-end justify-center gap-1.5"
                style={{ height: 48 }}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                {[28, 44, 36, 48, 32].map((h, i) => (
                  <div
                    key={i}
                    className="rounded-full"
                    style={{
                      width: 5,
                      height: h,
                      background: 'linear-gradient(to top, #00e676, #00bcd4)',
                      transformOrigin: 'bottom',
                      animation: `eq-bar 0.6s ease-in-out infinite`,
                      animationDelay: `${[0, 120, 60, 180, 90][i]}ms`,
                    }}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* ── Status Label ─────────────────────────────────────────── */}
      <motion.div
        layout
        className="flex items-center gap-2.5 px-5 py-2 rounded-full border text-xs font-semibold uppercase tracking-widest"
        style={{
          color: cfg.labelColor,
          borderColor: `${cfg.labelColor}25`,
          background: cfg.labelBg,
          backdropFilter: 'blur(8px)',
        }}
        animate={{ opacity: 1 }}
      >
        {/* Pulsing dot */}
        <motion.span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: cfg.labelColor }}
          animate={
            state === 'listening' || state === 'processing' || state === 'speaking'
              ? { opacity: [1, 0.2, 1] }
              : { opacity: 1 }
          }
          transition={{ duration: 1, repeat: Infinity }}
        />
        <span>
          {state === 'idle' && 'Ready'}
          {state === 'listening' && 'Listening'}
          {state === 'processing' && 'Thinking'}
          {state === 'speaking' && (statusText || 'Speaking')}
          {state === 'disconnected' && 'Offline'}
        </span>
      </motion.div>
    </div>
  );
}
