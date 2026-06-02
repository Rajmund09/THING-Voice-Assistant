/**
 * VisionResultCard.tsx — THING v4.8 (Phase 2 — Production Perfect)
 *
 * Displays a vision analysis result: a screenshot thumbnail + Gemini description.
 * Rendered in the chat when THING responds to a "what's on my screen?" type command,
 * or after a "click X" ui_click action.
 *
 * New in v4.8:
 *   - Latency badge ("Analyzed in 1.2s")
 *   - Model name chip ("gemini-2.5-flash")
 *   - Crosshair overlay on screenshot when click coordinates are present
 *   - elapsedMs, model, coordinates props
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, ZoomIn, X, Crosshair, Zap } from 'lucide-react';

interface Coordinates {
  x: number;
  y: number;
}

interface Props {
  description: string;
  screenshotB64?: string | null;
  /** Analysis latency in milliseconds (from backend elapsed_ms) */
  elapsedMs?: number | null;
  /** Gemini model name used for this analysis */
  model?: string | null;
  /** Pixel coordinates of the click target (for ui_click results) */
  coordinates?: Coordinates | null;
  /** Screen dimensions needed to compute crosshair position as percentage */
  screenWidth?: number;
  screenHeight?: number;
}

export default function VisionResultCard({
  description,
  screenshotB64,
  elapsedMs,
  model,
  coordinates,
  screenWidth = 1920,
  screenHeight = 1080,
}: Props) {
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const isClickResult = coordinates != null;

  // Crosshair position as CSS percentage within the thumbnail
  const crosshairLeft = coordinates ? `${(coordinates.x / screenWidth) * 100}%` : '50%';
  const crosshairTop  = coordinates ? `${(coordinates.y / screenHeight) * 100}%` : '50%';

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
        initial={{ opacity: 0, y: 12, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.32, ease: [0.2, 0, 0, 1] }}
        className="w-full max-w-sm"
        style={{
          background: isClickResult
            ? 'rgba(124, 58, 237, 0.04)'
            : 'rgba(0, 229, 255, 0.04)',
          border: isClickResult
            ? '1px solid rgba(124, 58, 237, 0.18)'
            : '1px solid rgba(0, 229, 255, 0.16)',
          borderRadius: '14px',
          overflow: 'hidden',
          boxShadow: isClickResult
            ? '0 4px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(124,58,237,0.06)'
            : '0 4px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(0,229,255,0.06)',
          backdropFilter: 'blur(12px)',
        }}
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div
          className="flex items-center gap-2 px-4 py-2.5"
          style={{
            borderBottom: isClickResult
              ? '1px solid rgba(124, 58, 237, 0.1)'
              : '1px solid rgba(0, 229, 255, 0.08)',
            background: isClickResult
              ? 'rgba(124, 58, 237, 0.06)'
              : 'rgba(0, 229, 255, 0.06)',
          }}
        >
          {isClickResult
            ? <Crosshair size={13} style={{ color: '#a78bfa' }} />
            : <Eye size={13} style={{ color: '#00e5ff' }} />
          }
          <span
            className="text-[11px] font-bold uppercase tracking-widest"
            style={{ color: isClickResult ? '#a78bfa' : '#00e5ff' }}
          >
            {isClickResult ? 'Click Target' : 'Vision Analysis'}
          </span>

          {/* Model chip */}
          {modelShort && (
            <span
              className="ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded-md"
              style={{
                color: isClickResult ? 'rgba(167,139,250,0.6)' : 'rgba(0,229,255,0.45)',
                background: isClickResult ? 'rgba(124,58,237,0.1)' : 'rgba(0,229,255,0.06)',
                border: isClickResult ? '1px solid rgba(124,58,237,0.15)' : '1px solid rgba(0,229,255,0.1)',
              }}
            >
              {modelShort}
            </span>
          )}
          {!modelShort && (
            <span className="ml-auto text-[10px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Gemini Vision
            </span>
          )}
        </div>

        {/* ── Screenshot thumbnail + crosshair overlay ────────────────── */}
        {screenshotB64 && (
          <div
            className="relative cursor-pointer group"
            style={{ maxHeight: '160px', overflow: 'hidden' }}
            onClick={() => setLightboxOpen(true)}
          >
            <img
              src={`data:image/jpeg;base64,${screenshotB64}`}
              alt="Screen capture analyzed by THING"
              style={{
                width: '100%',
                height: '160px',
                objectFit: 'cover',
                objectPosition: 'top',
                display: 'block',
              }}
            />

            {/* Click crosshair overlay */}
            {isClickResult && (
              <div
                className="absolute pointer-events-none"
                style={{
                  left: crosshairLeft,
                  top: crosshairTop,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                {/* Pulse ring */}
                <motion.div
                  animate={{ scale: [1, 1.6, 1], opacity: [0.8, 0, 0.8] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
                  style={{
                    position: 'absolute',
                    inset: '-8px',
                    borderRadius: '50%',
                    border: '2px solid rgba(167,139,250,0.7)',
                  }}
                />
                {/* Center dot */}
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: '#a78bfa',
                  border: '2px solid white',
                  boxShadow: '0 0 8px rgba(167,139,250,0.8)',
                }} />
              </div>
            )}

            {/* Zoom hover overlay */}
            <div
              className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200"
              style={{ background: 'rgba(0,0,0,0.45)' }}
            >
              <ZoomIn size={22} style={{ color: isClickResult ? '#a78bfa' : '#00e5ff' }} />
            </div>
          </div>
        )}

        {/* ── Description ──────────────────────────────────────────────── */}
        <div className="px-4 py-3">
          <p
            className="text-xs leading-relaxed"
            style={{ color: 'rgba(255,255,255,0.75)' }}
          >
            {description}
          </p>
        </div>

        {/* ── Footer: latency badge ────────────────────────────────────── */}
        {latencyLabel && (
          <div
            className="flex items-center gap-1.5 px-4 pb-3"
            style={{ marginTop: -4 }}
          >
            <Zap size={10} style={{ color: 'rgba(255,255,255,0.2)' }} />
            <span
              className="text-[10px]"
              style={{ color: 'rgba(255,255,255,0.2)' }}
            >
              Analyzed in {latencyLabel}
            </span>
          </div>
        )}
      </motion.div>

      {/* ── Lightbox ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {lightboxOpen && screenshotB64 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-6"
            style={{ background: 'rgba(0,0,0,0.88)', backdropFilter: 'blur(8px)' }}
            onClick={() => setLightboxOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.92 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.94 }}
              className="relative"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setLightboxOpen(false)}
                className="absolute -top-3 -right-3 z-10 p-1.5 rounded-full"
                style={{
                  background: 'rgba(255,255,255,0.1)',
                  border: '1px solid rgba(255,255,255,0.15)',
                }}
              >
                <X size={14} style={{ color: '#fff' }} />
              </button>

              {/* Lightbox image */}
              <div className="relative">
                <img
                  src={`data:image/jpeg;base64,${screenshotB64}`}
                  alt="Full screen capture"
                  style={{
                    maxWidth: '90vw',
                    maxHeight: '80vh',
                    borderRadius: '10px',
                    border: isClickResult
                      ? '1px solid rgba(124,58,237,0.3)'
                      : '1px solid rgba(0,229,255,0.2)',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
                    display: 'block',
                  }}
                />

                {/* Crosshair on full lightbox image */}
                {isClickResult && (
                  <div
                    className="absolute pointer-events-none"
                    style={{
                      left: crosshairLeft,
                      top: crosshairTop,
                      transform: 'translate(-50%, -50%)',
                    }}
                  >
                    {/* Crosshair lines */}
                    <div style={{
                      position: 'absolute',
                      left: '50%',
                      top: -20,
                      bottom: -20,
                      width: 1,
                      background: 'rgba(167,139,250,0.5)',
                      transform: 'translateX(-50%)',
                    }} />
                    <div style={{
                      position: 'absolute',
                      top: '50%',
                      left: -20,
                      right: -20,
                      height: 1,
                      background: 'rgba(167,139,250,0.5)',
                      transform: 'translateY(-50%)',
                    }} />
                    <div style={{
                      width: 14,
                      height: 14,
                      borderRadius: '50%',
                      background: '#a78bfa',
                      border: '2px solid white',
                      boxShadow: '0 0 12px rgba(167,139,250,0.9)',
                    }} />
                  </div>
                )}
              </div>

              {/* Lightbox footer */}
              {latencyLabel && (
                <div
                  className="flex items-center justify-center gap-1.5 mt-3"
                  style={{ color: 'rgba(255,255,255,0.3)' }}
                >
                  <Zap size={11} />
                  <span className="text-[11px]">Analyzed in {latencyLabel}</span>
                  {modelShort && (
                    <span className="text-[11px] opacity-60">· {modelShort}</span>
                  )}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
