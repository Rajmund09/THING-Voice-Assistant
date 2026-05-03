/**
 * ChatWindow.tsx — THING v4.0
 * Chat message list with auto-scroll, empty state, and animated entry.
 */

import { useEffect, useRef } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Activity } from 'lucide-react';
import MessageBubble, { TypingIndicator } from './MessageBubble';
import EmailReviewCard from './EmailReviewCard';
import type { Message } from '../hooks/useSocket';

interface Props {
  messages: Message[];
  isProcessing: boolean;
  onAction: (text: string) => void;
  onEmit?: (event: string, data: any) => void;
}

export default function ChatWindow({ messages, isProcessing, onAction, onEmit }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isProcessing]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
      {messages.length === 0 && !isProcessing ? (
        /* ── Empty state ─────────────────────────────────────── */
        <div className="h-full flex flex-col items-center justify-center gap-4 text-center px-8 py-16">
          {/* Subtle logo */}
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, rgba(0,229,255,0.08), rgba(124,58,237,0.08))',
              border: '1px solid rgba(0,229,255,0.12)',
            }}>
            <span className="text-2xl font-black gradient-text" style={{ fontFamily: 'Syne, sans-serif' }}>T</span>
          </div>

          <div>
            <p className="text-sm font-semibold mb-1.5" style={{ color: 'rgba(255,255,255,0.7)' }}>
              Ask THING anything
            </p>
            <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.25)' }}>
              Type a command below or speak to get started.
            </p>
          </div>

          {/* Suggestion chips */}
          <div className="flex flex-wrap gap-2 justify-center mt-2">
            {[
              'What\'s the time?',
              'Open YouTube',
              'Take a screenshot',
              'Play punjabi songs',
            ].map(s => (
              <div key={s}
                className="px-3 py-1.5 rounded-full text-xs"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: 'rgba(255,255,255,0.35)',
                }}>
                {s}
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2 mt-4"
            style={{ color: 'rgba(255,255,255,0.12)' }}>
            <Activity size={12} />
            <span className="text-[10px] uppercase tracking-widest">Awaiting command</span>
          </div>
        </div>
      ) : (
        /* ── Message list ────────────────────────────────────── */
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <div key={msg.id} className="space-y-4">
              <MessageBubble
                message={msg}
                isLatest={i === messages.length - 1}
              />
              
              {msg.data?.type === 'email_review' && (
                <div className="flex justify-start ml-12">
                  <EmailReviewCard
                    recipient={msg.data.recipient}
                    subject={msg.data.subject}
                    body={msg.data.body}
                    onSend={(updated) => {
                      if (onEmit) onEmit('send_edited_email', updated);
                      else onAction("yes");
                    }}
                    onCancel={() => onAction("no")}
                  />
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator while processing */}
          {isProcessing && <TypingIndicator key="typing" />}
        </AnimatePresence>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
