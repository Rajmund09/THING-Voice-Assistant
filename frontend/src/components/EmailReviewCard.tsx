/**
 * EmailReviewCard.tsx — THING Jarvis Upgrade
 * A premium UI component for reviewing generated emails.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Send, X, Edit3, User, Hash } from 'lucide-react';

interface Props {
  recipient: string;
  subject: string;
  body: string;
  onSend: (updated: {recipient: string, subject: string, body: string}) => void;
  onCancel: () => void;
}

export default function EmailReviewCard({ recipient, subject, body, onSend, onCancel }: Props) {
  const [editedRecipient, setEditedRecipient] = useState(recipient);
  const [editedSubject, setEditedSubject] = useState(subject);
  const [editedBody, setEditedBody] = useState(body);

  const handleSend = () => {
    onSend({
      recipient: editedRecipient,
      subject: editedSubject,
      body: editedBody
    });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className="max-w-md w-full glass-strong rounded-2xl overflow-hidden border border-white/10 shadow-2xl"
    >
      {/* Header */}
      <div className="px-6 py-4 bg-white/5 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Mail size={16} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white tracking-wide uppercase" style={{ fontFamily: 'Syne, sans-serif' }}>Email Draft</h3>
            <p className="text-[10px] text-zinc-500">Review and edit before sending</p>
          </div>
        </div>
        <button onClick={onCancel} className="text-zinc-500 hover:text-white transition-colors">
          <X size={18} />
        </button>
      </div>

      {/* Fields */}
      <div className="p-6 space-y-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-bold uppercase tracking-widest">
            <User size={10} />
            Recipient
          </div>
          <input 
            type="text"
            value={editedRecipient}
            onChange={(e) => setEditedRecipient(e.target.value)}
            className="w-full text-sm text-white bg-white/5 rounded-lg px-3 py-2 border border-white/5 outline-none focus:border-cyan-500/50 transition-colors"
          />
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-bold uppercase tracking-widest">
            <Hash size={10} />
            Subject
          </div>
          <input 
            type="text"
            value={editedSubject}
            onChange={(e) => setEditedSubject(e.target.value)}
            className="w-full text-sm text-white font-medium bg-white/5 rounded-lg px-3 py-2 border border-white/5 outline-none focus:border-cyan-500/50 transition-colors"
          />
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-bold uppercase tracking-widest">
            <Edit3 size={10} />
            Message
          </div>
          <textarea 
            value={editedBody}
            onChange={(e) => setEditedBody(e.target.value)}
            rows={5}
            className="w-full text-xs text-zinc-300 leading-relaxed bg-white/5 rounded-lg px-3 py-3 border border-white/5 outline-none focus:border-cyan-500/50 transition-colors resize-none custom-scrollbar"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 py-4 bg-white/5 border-t border-white/5 flex gap-3">
        <button 
          onClick={onCancel}
          className="flex-1 py-3 rounded-xl bg-white/5 text-[11px] font-bold text-zinc-400 hover:bg-white/10 hover:text-white transition-all border border-white/5"
        >
          DISCARD
        </button>
        <button 
          onClick={handleSend}
          className="flex-1 py-3 rounded-xl bg-cyan-500 text-[11px] font-bold text-black hover:bg-cyan-400 transition-all flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(6,182,212,0.3)]"
        >
          <Send size={14} />
          SEND MAIL
        </button>
      </div>
    </motion.div>
  );
}
