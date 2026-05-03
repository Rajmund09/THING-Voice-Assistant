/**
 * Sidebar.tsx — THING v4.0
 * Collapsible sidebar with logo, new chat, history, settings.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquarePlus, ChevronLeft, ChevronRight, Settings, Clock, Zap, Database } from 'lucide-react';
import type { Message } from '../hooks/useSocket';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  messages: Message[];
  onNewChat: () => void;
  onOpenSettings: () => void;
  onOpenMemory: () => void;
}

export default function Sidebar({ isOpen, onToggle, messages, onNewChat, onOpenSettings, onOpenMemory }: SidebarProps) {
  // Build a session summary from messages
  const sessionCount = messages.filter(m => m.speaker === 'user').length;

  return (
    <>
      {/* Sidebar panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            key="sidebar"
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="glass-strong flex flex-col h-full rounded-2xl overflow-hidden shrink-0 relative"
            style={{ width: 240 }}
          >
            {/* Logo area */}
            <div className="px-5 pt-6 pb-4">
              <div className="flex items-center gap-3">
                {/* Logo orb */}
                <div className="w-9 h-9 rounded-xl flex items-center justify-center relative overflow-hidden"
                  style={{
                    background: 'linear-gradient(135deg, rgba(0,229,255,0.2), rgba(124,58,237,0.2))',
                    border: '1px solid rgba(0,229,255,0.25)',
                    boxShadow: '0 0 20px rgba(0,229,255,0.1)',
                  }}>
                  <span className="font-black text-sm gradient-text">TH</span>
                </div>
                <div>
                  <div className="text-sm font-bold text-white" style={{ fontFamily: 'Syne, sans-serif' }}>
                    THING<span style={{ color: '#00e5ff' }}>.AI</span>
                  </div>
                  <div className="text-[10px] font-medium" style={{ color: 'rgba(0,229,255,0.5)' }}>
                    v4.0 — Production
                  </div>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="mx-4 h-px" style={{ background: 'rgba(255,255,255,0.05)' }} />

            {/* New Chat button */}
            <div className="px-3 py-3">
              <button
                onClick={onNewChat}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium
                           transition-all duration-200 active:scale-95"
                style={{
                  background: 'rgba(0,229,255,0.06)',
                  border: '1px solid rgba(0,229,255,0.15)',
                  color: '#00e5ff',
                }}
              >
                <MessageSquarePlus size={16} />
                New Chat
              </button>
            </div>

            {/* Session info */}
            <div className="px-5 py-2">
              <p className="text-[10px] font-bold uppercase tracking-widest mb-2"
                style={{ color: 'rgba(255,255,255,0.2)' }}>
                Current Session
              </p>

              {sessionCount === 0 ? (
                <div className="flex items-center gap-2 py-2">
                  <Zap size={12} style={{ color: 'rgba(255,255,255,0.15)' }} />
                  <span className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>No commands yet</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg"
                  style={{ background: 'rgba(255,255,255,0.03)' }}>
                  <Clock size={12} style={{ color: 'rgba(255,255,255,0.3)' }} />
                  <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
                    {sessionCount} command{sessionCount !== 1 ? 's' : ''}
                  </span>
                </div>
              )}
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Divider */}
            <div className="mx-4 h-px" style={{ background: 'rgba(255,255,255,0.05)' }} />

            {/* Memory & Settings */}
            <div className="px-3 py-3 space-y-1">
              <button
                onClick={onOpenMemory}
                className="sidebar-item w-full"
              >
                <Database size={16} />
                <span>Memory</span>
              </button>
              <button
                onClick={onOpenSettings}
                className="sidebar-item w-full"
              >
                <Settings size={16} />
                <span>Settings</span>
              </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Toggle button */}
      <motion.button
        onClick={onToggle}
        className="absolute z-50 top-6 flex items-center justify-center w-7 h-7 rounded-lg
                   transition-all duration-200 hover:scale-110 active:scale-95"
        style={{
          left: isOpen ? 252 : 16,
          background: 'rgba(255,255,255,0.06)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: 'rgba(255,255,255,0.4)',
          transitionProperty: 'left',
          transitionDuration: '300ms',
        }}
        title={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        {isOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
      </motion.button>
    </>
  );
}
