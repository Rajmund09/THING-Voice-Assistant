/**
 * MessageBubble.tsx — THING v4.0
 * Premium chat bubble with status indicators, timestamps, and copy button.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, Copy, Check } from 'lucide-react';
import type { Message } from '../hooks/useSocket';

interface Props {
  message: Message;
  isLatest?: boolean;
}

export default function MessageBubble({ message }: Props) {
  const [copied, setCopied] = useState(false);
  const isUser = message.speaker === 'user';
  const isSuccess = message.success !== false;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const timeStr = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.96 }}
      transition={{ duration: 0.28, ease: [0.2, 0, 0, 1] }}
      className={`group flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}
    >
      {/* Speaker label */}
      <span className="text-[10px] font-bold uppercase tracking-widest px-1"
        style={{ color: isUser ? 'rgba(0,229,255,0.5)' : 'rgba(255,255,255,0.2)' }}>
        {isUser ? 'You' : 'THING'}
      </span>

      {/* Bubble row */}
      <div className={`flex items-end gap-2 max-w-[88%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

        {/* THING avatar dot */}
        {!isUser && (
          <div className="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center mb-0.5"
            style={{ background: 'rgba(0,229,255,0.12)', border: '1px solid rgba(0,229,255,0.2)' }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: '#00e5ff' }}>T</span>
          </div>
        )}

        {/* Message bubble */}
        <div className="relative">
          <div
            className="relative px-4 py-3 msg-text"
            style={{
              borderRadius: isUser
                ? '18px 18px 4px 18px'
                : '18px 18px 18px 4px',
              background: isUser
                ? 'linear-gradient(135deg, rgba(0,180,220,0.9), rgba(0,140,180,0.85))'
                : message.success === false
                ? 'rgba(255,68,68,0.08)'
                : 'rgba(255,255,255,0.04)',
              border: isUser
                ? '1px solid rgba(0,229,255,0.3)'
                : message.success === false
                ? '1px solid rgba(255,68,68,0.2)'
                : '1px solid rgba(255,255,255,0.06)',
              backdropFilter: 'blur(8px)',
              boxShadow: isUser
                ? '0 4px 20px rgba(0,180,220,0.2)'
                : '0 2px 12px rgba(0,0,0,0.3)',
              color: isUser ? '#ffffff' : '#e2e8f0',
              maxWidth: '100%',
              wordBreak: 'break-word',
            }}
          >
            {message.text}
          </div>

          {/* Copy button — appears on hover */}
          <button
            onClick={handleCopy}
            className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200
                       -top-2 p-1 rounded-md"
            style={{
              [isUser ? 'left' : 'right']: '-28px',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
            }}
            title="Copy"
          >
            {copied
              ? <Check size={11} style={{ color: '#00e676' }} />
              : <Copy size={11} style={{ color: '#6b7280' }} />
            }
          </button>
        </div>

        {/* Success / failure indicator for THING messages */}
        {!isUser && message.success !== undefined && (
          <div className="mb-0.5 flex-shrink-0">
            {isSuccess
              ? <CheckCircle size={14} style={{ color: '#00e676', opacity: 0.6 }} />
              : <XCircle size={14} style={{ color: '#ef4444', opacity: 0.7 }} />
            }
          </div>
        )}
      </div>

      {/* Timestamp */}
      <span className="text-[10px] px-1 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ color: '#374151' }}>
        {timeStr}
      </span>
    </motion.div>
  );
}

// ── Typing indicator (3 dots while THING is processing) ──────────────────────
export function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className="flex items-start gap-2"
    >
      <div className="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center"
        style={{ background: 'rgba(0,229,255,0.12)', border: '1px solid rgba(0,229,255,0.2)' }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#00e5ff' }}>T</span>
      </div>
      <div
        className="px-4 py-3 flex items-center gap-1.5"
        style={{
          borderRadius: '18px 18px 18px 4px',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: 'rgba(0,229,255,0.6)',
              animation: 'think-dot 1.2s ease-in-out infinite',
              animationDelay: `${i * 200}ms`,
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}
