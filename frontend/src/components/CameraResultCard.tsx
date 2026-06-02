/**
 * CameraResultCard.tsx — THING v4.8 (Phase 2 — Production Perfect)
 *
 * Displays a premium visual response of webcam face and environmental scans:
 *   - Glassmorphism dark-mode container
 *   - Blinking green/red "SCANNING SYSTEM" status badge
 *   - Webcam image with active scanning laser overlay
 *   - Neon-glowing, interactive bounding box overlays around detected faces
 *   - Dynamic cards details for identified people, their activities, and the background environment.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, ZoomIn, X, Zap, User, Compass, Info } from 'lucide-react';

interface Person {
  name: string;
  box_2d?: [number, number, number, number] | null; // [ymin, xmin, ymax, xmax] normalized to 1000
  activity?: string;
}

interface Props {
  description: string;
  screenshotB64?: string | null;
  elapsedMs?: number | null;
  model?: string | null;
  people?: Person[];
  environment?: string;
}

export default function CameraResultCard({
  description,
  screenshotB64,
  elapsedMs,
  model,
  people = [],
  environment,
}: Props) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [hoveredPerson, setHoveredPerson] = useState<number | null>(null);

  const latencyLabel =
    elapsedMs != null
      ? elapsedMs < 1000
        ? `${elapsedMs}ms`
        : `${(elapsedMs / 1000).toFixed(1)}s`
      : null;

  const modelShort = model
    ? model.replace('gemini-', '').replace('-latest', '')
    : null;

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 15, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.38, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-sm"
        style={{
          background: 'rgba(15, 23, 42, 0.65)',
          border: '1px solid rgba(139, 92, 246, 0.25)',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(139, 92, 246, 0.1)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div
          className="flex items-center gap-2 px-4 py-3"
          style={{
            borderBottom: '1px solid rgba(139, 92, 246, 0.15)',
            background: 'rgba(139, 92, 246, 0.08)',
          }}
        >
          <Camera size={14} className="animate-pulse" style={{ color: '#a78bfa' }} />
          <span
            className="text-[11px] font-black uppercase tracking-widest"
            style={{ color: '#a78bfa', fontFamily: 'Outfit, sans-serif' }}
          >
            Live Camera Scan
          </span>

          {/* Glowing Status Dot */}
          <div className="flex items-center gap-1.5 ml-3">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[9px] font-bold text-emerald-400 tracking-wider uppercase font-mono">
              Active
            </span>
          </div>

          {/* Model info */}
          {modelShort ? (
            <span
              className="ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded-md"
              style={{
                color: 'rgba(167, 139, 250, 0.7)',
                background: 'rgba(139, 92, 246, 0.12)',
                border: '1px solid rgba(139, 92, 246, 0.2)',
              }}
            >
              {modelShort}
            </span>
          ) : (
            <span className="ml-auto text-[10px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Vision System
            </span>
          )}
        </div>

        {/* ── Webcam Image Frame with HUD & Scanline ────────────────── */}
        {screenshotB64 && (
          <div
            className="relative cursor-pointer group overflow-hidden"
            style={{ height: '180px' }}
            onClick={() => setLightboxOpen(true)}
          >
            <img
              src={`data:image/jpeg;base64,${screenshotB64}`}
              alt="Webcam scan capture"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: 'block',
              }}
            />

            {/* Glowing Scan Laser Line */}
            <motion.div
              animate={{ top: ['0%', '100%', '0%'] }}
              transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
              className="absolute left-0 right-0 h-0.5 pointer-events-none"
              style={{
                background: 'linear-gradient(90deg, transparent, rgba(167, 139, 250, 0.8), transparent)',
                boxShadow: '0 0 10px #a78bfa, 0 0 20px #8b5cf6',
                zIndex: 4,
              }}
            />

            {/* Crosshair grids corners in HUD */}
            <div className="absolute inset-2 pointer-events-none border border-white/5 z-0" />
            <div className="absolute top-2 left-2 w-3 h-3 border-t-2 border-l-2 border-violet-400 pointer-events-none z-10" />
            <div className="absolute top-2 right-2 w-3 h-3 border-t-2 border-r-2 border-violet-400 pointer-events-none z-10" />
            <div className="absolute bottom-2 left-2 w-3 h-3 border-b-2 border-l-2 border-violet-400 pointer-events-none z-10" />
            <div className="absolute bottom-2 right-2 w-3 h-3 border-b-2 border-r-2 border-violet-400 pointer-events-none z-10" />

            {/* Dynamic Face Bounding Box Overlays */}
            {people.map((person, idx) => {
              if (!person.box_2d || person.box_2d.length < 4) return null;
              
              const [ymin, xmin, ymax, xmax] = person.box_2d;
              const top = `${ymin / 10}%`;
              const left = `${xmin / 10}%`;
              const height = `${(ymax - ymin) / 10}%`;
              const width = `${(xmax - xmin) / 10}%`;

              const isNew = person.name.toLowerCase() === 'new person';
              const isHovered = hoveredPerson === idx;

              return (
                <div
                  key={idx}
                  className="absolute z-20 pointer-events-auto transition-all duration-300"
                  style={{
                    top,
                    left,
                    width,
                    height,
                  }}
                  onMouseEnter={() => setHoveredPerson(idx)}
                  onMouseLeave={() => setHoveredPerson(null)}
                >
                  {/* Glowing Box Border */}
                  <div
                    className="w-full h-full rounded-md border-2 border-dashed transition-all duration-300"
                    style={{
                      borderColor: isHovered 
                        ? (isNew ? '#f43f5e' : '#10b981') 
                        : '#a78bfa',
                      boxShadow: isHovered
                        ? `0 0 16px ${isNew ? 'rgba(244,63,94,0.8)' : 'rgba(16,185,129,0.8)'}`
                        : '0 0 8px rgba(167,139,250,0.4)',
                    }}
                  />

                  {/* Bounding Box Label Tag */}
                  <div
                    className="absolute -top-6 left-0 px-2 py-0.5 rounded text-[9px] font-bold text-white uppercase tracking-wider whitespace-nowrap shadow-md transition-all duration-300"
                    style={{
                      background: isNew ? 'rgba(244, 63, 94, 0.85)' : 'rgba(16, 185, 129, 0.85)',
                      border: `1px solid ${isNew ? 'rgba(244, 63, 94, 0.4)' : 'rgba(16, 185, 129, 0.4)'}`,
                      backdropFilter: 'blur(4px)',
                      opacity: isHovered ? 1 : 0.8,
                      transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                    }}
                  >
                    {person.name}
                  </div>
                </div>
              );
            })}

            {/* Magnify hover overlay */}
            <div
              className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none"
              style={{ background: 'rgba(0,0,0,0.3)', zIndex: 1 }}
            >
              <ZoomIn size={22} style={{ color: '#a78bfa' }} />
            </div>
          </div>
        )}

        {/* ── Info Cards & Summary Details ────────────────────────────── */}
        <div className="px-4 py-3 space-y-3">
          {/* Natural Verbal Description */}
          <p
            className="text-xs leading-relaxed"
            style={{ color: 'rgba(255,255,255,0.8)' }}
          >
            {description}
          </p>

          {/* People & Activities Details list */}
          {people.length > 0 && (
            <div className="space-y-1.5 pt-1 border-t border-white/5">
              <div className="flex items-center gap-1.5 text-[9px] uppercase tracking-widest text-violet-400 font-bold">
                <User size={10} />
                <span>Detected Targets</span>
              </div>
              <div className="grid gap-1.5">
                {people.map((person, idx) => {
                  const isNew = person.name.toLowerCase() === 'new person';
                  return (
                    <div
                      key={idx}
                      className="flex items-start gap-2 p-1.5 rounded-lg transition-all duration-200"
                      style={{
                        background: hoveredPerson === idx ? 'rgba(167,139,250,0.06)' : 'rgba(255,255,255,0.02)',
                        border: hoveredPerson === idx ? '1px solid rgba(167,139,250,0.15)' : '1px solid rgba(255,255,255,0.04)'
                      }}
                      onMouseEnter={() => setHoveredPerson(idx)}
                      onMouseLeave={() => setHoveredPerson(null)}
                    >
                      <div
                        className="w-1.5 h-1.5 rounded-full mt-1.5"
                        style={{ background: isNew ? '#f43f5e' : '#10b981' }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-bold text-white leading-tight">
                          {person.name}
                        </p>
                        {person.activity && (
                          <p className="text-[10px] text-white/50 truncate leading-snug">
                            {person.activity}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Environmental Conditions */}
          {environment && (
            <div className="flex items-start gap-2 p-2 rounded-lg border border-white/5 bg-white/[0.01]">
              <Compass size={11} className="mt-0.5 text-violet-400" />
              <div className="flex-1">
                <span className="text-[9px] font-bold text-violet-400 uppercase tracking-widest block mb-0.5">
                  Surrounding Environment
                </span>
                <p className="text-[10px] text-white/60 leading-normal">
                  {environment}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer: Latency analysis timing ──────────────────────────── */}
        {latencyLabel && (
          <div
            className="flex items-center gap-1.5 px-4 pb-3"
            style={{ marginTop: -2 }}
          >
            <Zap size={10} style={{ color: 'rgba(255,255,255,0.2)' }} />
            <span
              className="text-[10px]"
              style={{ color: 'rgba(255,255,255,0.2)' }}
            >
              Scanned in {latencyLabel}
            </span>
          </div>
        )}
      </motion.div>

      {/* ── Lightbox View ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {lightboxOpen && screenshotB64 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-6"
            style={{ background: 'rgba(3, 7, 18, 0.93)', backdropFilter: 'blur(8px)' }}
            onClick={() => setLightboxOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.93 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              className="relative"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close Button */}
              <button
                onClick={() => setLightboxOpen(false)}
                className="absolute -top-3 -right-3 z-30 p-2 rounded-full shadow-lg transition-transform hover:scale-105"
                style={{
                  background: 'rgba(139, 92, 246, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                }}
              >
                <X size={14} style={{ color: '#fff' }} />
              </button>

              {/* Large Image Frame */}
              <div className="relative overflow-hidden rounded-xl border border-violet-500/30 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)]">
                <img
                  src={`data:image/jpeg;base64,${screenshotB64}`}
                  alt="Full camera capture"
                  style={{
                    maxWidth: '90vw',
                    maxHeight: '80vh',
                    display: 'block',
                  }}
                />

                {/* Laser scan line inside lightbox */}
                <motion.div
                  animate={{ top: ['0%', '100%', '0%'] }}
                  transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
                  className="absolute left-0 right-0 h-0.5 pointer-events-none"
                  style={{
                    background: 'linear-gradient(90deg, transparent, rgba(167,139,250,0.9), transparent)',
                    boxShadow: '0 0 12px #a78bfa',
                    zIndex: 4,
                  }}
                />

                {/* Full Overlay boxes inside Lightbox */}
                {people.map((person, idx) => {
                  if (!person.box_2d || person.box_2d.length < 4) return null;
                  
                  const [ymin, xmin, ymax, xmax] = person.box_2d;
                  const top = `${ymin / 10}%`;
                  const left = `${xmin / 10}%`;
                  const height = `${(ymax - ymin) / 10}%`;
                  const width = `${(xmax - xmin) / 10}%`;

                  const isNew = person.name.toLowerCase() === 'new person';

                  return (
                    <div
                      key={idx}
                      className="absolute z-20 pointer-events-none"
                      style={{
                        top,
                        left,
                        width,
                        height,
                      }}
                    >
                      {/* Bounding box border */}
                      <div
                        className="w-full h-full rounded-md border-2 border-dashed"
                        style={{
                          borderColor: isNew ? '#f43f5e' : '#10b981',
                          boxShadow: isNew 
                            ? '0 0 20px rgba(244,63,94,0.6)' 
                            : '0 0 20px rgba(16,185,129,0.6)',
                        }}
                      />

                      {/* Name tags labels */}
                      <div
                        className="absolute -top-7 left-0 px-2.5 py-1 rounded text-[10px] font-black text-white uppercase tracking-widest shadow-lg"
                        style={{
                          background: isNew ? 'rgba(244, 63, 94, 0.9)' : 'rgba(16, 185, 129, 0.9)',
                          border: `1px solid ${isNew ? 'rgba(244, 63, 94, 0.5)' : 'rgba(16, 185, 129, 0.5)'}`,
                          backdropFilter: 'blur(4px)',
                        }}
                      >
                        {person.name}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Lightbox details info footer */}
              <div className="flex items-center justify-center gap-3 mt-4 text-white/40 text-[10px] font-mono">
                <Info size={11} />
                {latencyLabel && <span>Processed: {latencyLabel}</span>}
                {modelShort && <span>· Engine: {modelShort}</span>}
                {environment && <span className="max-w-[300px] truncate">· Loc: {environment}</span>}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
