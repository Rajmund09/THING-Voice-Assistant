/**
 * InputBar.tsx — THING v4.0
 * Premium input bar with mic, stop, and send buttons.
 */

import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Mic, Square } from 'lucide-react';

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  isSpeaking: boolean;
  disabled: boolean;
}

export default function InputBar({ onSend, onStop, isSpeaking, disabled }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="px-4 pb-4 pt-2">
      <div
        className="relative flex items-end gap-2 rounded-2xl p-2 transition-all duration-300"
        style={{
          background: 'rgba(255,255,255,0.03)',
          border: `1px solid ${canSend ? 'rgba(0,229,255,0.25)' : 'rgba(255,255,255,0.07)'}`,
          boxShadow: canSend ? '0 0 0 3px rgba(0,229,255,0.06)' : 'none',
        }}
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder={disabled ? 'Reconnecting...' : 'Ask THING anything…'}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-white placeholder:text-zinc-600
                     py-2 px-3 focus:outline-none leading-relaxed input-ring min-h-[40px]"
          style={{
            maxHeight: 120,
            borderRadius: 12,
            border: 'none',
            opacity: disabled ? 0.4 : 1,
          }}
        />

        {/* Action buttons */}
        <div className="flex items-end gap-1.5 pb-1 pr-1 flex-shrink-0">
          {/* Stop button — shown when THING is speaking */}
          <AnimatePresence>
            {isSpeaking && (
              <motion.button
                key="stop"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.7 }}
                onClick={onStop}
                className="flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-200
                           hover:scale-105 active:scale-95"
                style={{
                  background: 'rgba(255,68,68,0.15)',
                  border: '1px solid rgba(255,68,68,0.3)',
                  color: '#ff4444',
                }}
                title="Stop speaking"
              >
                <Square size={15} fill="currentColor" />
              </motion.button>
            )}
          </AnimatePresence>

          {/* Mic indicator */}
          <div
            className="flex items-center justify-center w-9 h-9 rounded-xl"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              color: 'rgba(255,255,255,0.2)',
            }}
            title="Voice input active via backend"
          >
            <Mic size={15} />
          </div>

          {/* Send button */}
          <motion.button
            whileHover={canSend ? { scale: 1.05 } : {}}
            whileTap={canSend ? { scale: 0.92 } : {}}
            onClick={handleSend}
            disabled={!canSend}
            className="flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-200"
            style={{
              background: canSend
                ? 'linear-gradient(135deg, rgba(0,180,220,0.9), rgba(0,100,180,0.8))'
                : 'rgba(255,255,255,0.04)',
              border: canSend
                ? '1px solid rgba(0,229,255,0.3)'
                : '1px solid rgba(255,255,255,0.06)',
              color: canSend ? '#fff' : 'rgba(255,255,255,0.2)',
              boxShadow: canSend ? '0 4px 16px rgba(0,180,220,0.3)' : 'none',
              cursor: canSend ? 'pointer' : 'default',
            }}
            title="Send"
          >
            <Send size={15} />
          </motion.button>
        </div>
      </div>

      {/* Hint text */}
      <p className="text-center text-[10px] mt-2" style={{ color: 'rgba(255,255,255,0.12)' }}>
        Press Enter to send · Shift+Enter for new line · Voice active via backend
      </p>
    </div>
  );
}
