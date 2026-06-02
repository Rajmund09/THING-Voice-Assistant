import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, Cpu, HardDrive, Clock, Moon, Check } from 'lucide-react';
import type { Suggestion } from '../hooks/useSocket';

interface ProactiveBannerProps {
  suggestions: Suggestion[];
  onAccept: (id: string, action: string) => void;
  onDismiss: (id: string) => void;
}

const ICON_MAP: Record<string, any> = {
  calendar: Calendar,
  cpu: Cpu,
  ram: HardDrive,
  clock: Clock,
  moon: Moon,
};

export default function ProactiveBanner({ suggestions, onAccept, onDismiss }: ProactiveBannerProps) {
  return (
    <div className="absolute top-4 right-4 z-[100] flex flex-col gap-3 pointer-events-none">
      <AnimatePresence mode="popLayout">
        {suggestions.map((s) => (
          <SuggestionItem 
            key={s.id} 
            suggestion={s} 
            onAccept={onAccept} 
            onDismiss={onDismiss} 
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

function SuggestionItem({ suggestion: s, onAccept, onDismiss }: { 
  suggestion: Suggestion, 
  onAccept: (id: string, action: string) => void, 
  onDismiss: (id: string) => void 
}) {
  const Icon = ICON_MAP[s.icon] || Clock;

  // Auto-dismiss after 30s
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(s.id), 30000);
    return () => clearTimeout(timer);
  }, [s.id, onDismiss]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 50, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.95 }}
      className="pointer-events-auto glass-dark w-80 p-4 rounded-2xl border flex gap-4 relative overflow-hidden group shadow-2xl"
      style={{ 
        background: 'rgba(25, 25, 30, 0.9)',
        borderColor: 'rgba(0, 229, 255, 0.15)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 15px rgba(0, 229, 255, 0.05)'
      }}
    >
      {/* Accent glow */}
      <div className="absolute -right-4 -top-4 w-16 h-16 rounded-full opacity-20 blur-2xl"
           style={{ background: 'var(--clr-primary)' }} />

      <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
        <Icon size={20} className="text-[#00e5ff]" />
      </div>

      <div className="flex-1">
        <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-1">
          Smart Suggestion
        </h4>
        <p className="text-sm text-white/80 leading-relaxed font-medium">
          {s.message}
        </p>

        <div className="flex gap-2 mt-4">
          <button
            onClick={() => onAccept(s.id, s.action)}
            className="flex-1 py-1.5 rounded-lg bg-[#00e5ff] text-black text-xs font-bold flex items-center justify-center gap-1.5 transition-all hover:brightness-110 active:scale-95"
          >
            <Check size={14} /> Accept
          </button>
          <button
            onClick={() => onDismiss(s.id)}
            className="px-3 py-1.5 rounded-lg bg-white/5 text-white/40 text-xs font-bold transition-all hover:bg-white/10 hover:text-white/60 active:scale-95"
          >
            Dismiss
          </button>
        </div>
      </div>

      {/* Progress bar for auto-dismiss */}
      <motion.div 
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: 30, ease: 'linear' }}
        className="absolute bottom-0 left-0 h-[2px] bg-[#00e5ff]/30"
      />
    </motion.div>
  );
}
