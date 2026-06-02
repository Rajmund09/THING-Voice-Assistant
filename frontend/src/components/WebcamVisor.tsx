/**
 * WebcamVisor.tsx — THING v4.8 (Phase 2 — Live Camera Feeds)
 *
 * Futuristic HTML5 Live Video Visor Widget:
 *   - Glassmorphism bezel container.
 *   - Auto-releases hardware camera locks immediately when THING is processing queries.
 *   - Sweeping purple neon laser scanlines.
 *   - Glowing HUD coordinates, crosshairs, and sci-fi brackets.
 *   - Handles error cases cleanly (blocked permissions, occupied hardware).
 */

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, ShieldAlert, Cpu, Eye } from 'lucide-react';

interface Props {
  isProcessing: boolean;
}

export default function WebcamVisor({ isProcessing }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activeStream: MediaStream | null = null;

    async function startCamera() {
      if (isProcessing) return;

      try {
        setError(null);
        const s = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user',
          },
          audio: false, // Video only
        });
        activeStream = s;
        setStream(s);
      } catch (err: any) {
        console.warn('[WebcamVisor] Camera access occupied or blocked:', err);
        setError('Camera blocked or already in use by another app.');
      }
    }

    startCamera();

    return () => {
      if (activeStream) {
        activeStream.getTracks().forEach((track) => track.stop());
      }
      setStream(null);
    };
  }, [isProcessing]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  return (
    <div
      className="w-[280px] p-2 mt-4 select-none relative transition-all duration-300"
      style={{
        background: 'rgba(15, 23, 42, 0.45)',
        border: '1px solid rgba(0, 229, 255, 0.15)',
        borderRadius: '16px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.03)',
        backdropFilter: 'blur(12px)',
      }}
    >
      {/* HUD Header */}
      <div className="flex items-center justify-between px-2 py-1.5 mb-1.5 border-b border-[#00e5ff]/10">
        <div className="flex items-center gap-1.5">
          <Eye size={12} className="animate-pulse" style={{ color: '#00e5ff' }} />
          <span
            className="text-[9px] font-black uppercase tracking-widest"
            style={{ color: '#00e5ff', fontFamily: 'Outfit, sans-serif' }}
          >
            HUD Camera Visor
          </span>
        </div>

        {/* Live Indicator */}
        {!isProcessing && stream ? (
          <div className="flex items-center gap-1">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500"></span>
            </span>
            <span className="text-[7.5px] font-bold text-cyan-400 tracking-widest uppercase font-mono">
              Live
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 opacity-50" />
            <span className="text-[7.5px] font-bold text-amber-500 tracking-widest uppercase font-mono">
              Offline
            </span>
          </div>
        )}
      </div>

      {/* Visor Frame */}
      <div
        className="relative overflow-hidden rounded-lg bg-black/60 flex items-center justify-center"
        style={{ height: '150px' }}
      >
        {/* Sci-Fi Decorative Grid lines overlay */}
        <div className="absolute inset-0 pointer-events-none opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0,229,255,0.15) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0,229,255,0.15) 1px, transparent 1px)
            `,
            backgroundSize: '15px 15px',
            zIndex: 3,
          }}
        />

        {/* Corner Brackets */}
        <div className="absolute inset-1.5 pointer-events-none border border-white/5 z-0" />
        <div className="absolute top-1.5 left-1.5 w-2 h-2 border-t border-l border-cyan-400 pointer-events-none z-10" />
        <div className="absolute top-1.5 right-1.5 w-2 h-2 border-t border-r border-cyan-400 pointer-events-none z-10" />
        <div className="absolute bottom-1.5 left-1.5 w-2 h-2 border-b border-l border-cyan-400 pointer-events-none z-10" />
        <div className="absolute bottom-1.5 right-1.5 w-2 h-2 border-b border-r border-cyan-400 pointer-events-none z-10" />

        {/* Animated Laser Sweep Line */}
        {!isProcessing && stream && (
          <motion.div
            animate={{ top: ['0%', '100%', '0%'] }}
            transition={{ duration: 3.8, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute left-0 right-0 h-[1.5px] pointer-events-none"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.8), transparent)',
              boxShadow: '0 0 8px #00e5ff',
              zIndex: 4,
            }}
          />
        )}

        <AnimatePresence mode="wait">
          {isProcessing ? (
            /* Scanning Overlay */
            <motion.div
              key="scanning"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-4 text-center z-20"
              style={{ background: 'rgba(10, 15, 30, 0.85)' }}
            >
              <Cpu size={24} className="animate-spin text-violet-400" style={{ animationDuration: '3s' }} />
              <div>
                <p className="text-[9px] font-bold text-violet-300 uppercase tracking-widest font-mono">
                  HUD SYSTEM BUSY
                </p>
                <p className="text-[8px] text-white/40 mt-0.5 leading-normal">
                  Visor stream suspended. AI scanner taking snapshot capture...
                </p>
              </div>
            </motion.div>
          ) : error ? (
            /* Error Overlay */
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 p-3 text-center z-20"
              style={{ background: 'rgba(20, 10, 10, 0.8)' }}
            >
              <ShieldAlert size={20} className="text-red-400" />
              <p className="text-[9px] font-bold text-red-300 uppercase tracking-widest font-mono">
                Visor Blocked
              </p>
              <p className="text-[8px] text-white/50 leading-relaxed max-w-[200px]">
                Ensure your webcam is connected and not locked by another browser tab.
              </p>
            </motion.div>
          ) : stream ? (
            /* Active Live stream preview */
            <motion.video
              key="video"
              ref={videoRef}
              autoPlay
              playsInline
              muted
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full h-full object-cover scale-x-[-1]"
              style={{ zIndex: 1 }}
            />
          ) : (
            /* Standby State */
            <motion.div
              key="standby"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center gap-1"
            >
              <Camera size={20} className="text-white/20" />
              <span className="text-[9px] text-white/30 tracking-wider">VISOR STANDBY</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Decorative footer details */}
      <div className="flex items-center justify-between px-1.5 mt-1 text-[7px] font-mono text-white/20">
        <span>FPS: 30.0 / AUTO</span>
        <span>HUD_BEAM: ON</span>
      </div>
    </div>
  );
}
