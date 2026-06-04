/**
 * MemoryDashboard.tsx — THING Jarvis Upgrade
 * Premium dashboard to view what THING knows about the user.
 */

import { motion } from 'framer-motion';
import { X, User, Briefcase, Target, Heart, ShieldCheck, Database } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  profile: any;
}

export default function MemoryDashboard({ isOpen, onClose, profile }: Props) {
  if (!isOpen) return null;

  return (
    <>
      <motion.div
        className="absolute inset-0 z-40"
        style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />

      <motion.div
        className="absolute inset-y-0 right-0 z-50 glass-strong flex flex-col"
        style={{ width: 400 }}
        initial={{ x: 400 }}
        animate={{ x: 0 }}
        exit={{ x: 400 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {/* Header */}
        <div className="px-8 py-6 border-b border-white/5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center text-violet-400">
                <Database size={20} />
              </div>
              <h2 className="text-lg font-bold text-white tracking-tight" style={{ fontFamily: 'Syne, sans-serif' }}>Neural Memory</h2>
            </div>
            <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/10 text-zinc-500 transition-colors">
              <X size={20} />
            </button>
          </div>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Everything THING knows about your persona and history.
          </p>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-8 py-8 space-y-8 custom-scrollbar">
          
          {/* Identity Section */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <User size={14} className="text-cyan-400" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Identity</span>
            </div>
            <div className="bg-white/5 rounded-2xl p-5 border border-white/5 space-y-4">
              <div className="flex justify-between">
                <span className="text-xs text-zinc-500">Full Name</span>
                <span className="text-xs font-bold text-white">{profile?.name || 'Raj'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-zinc-500">Education</span>
                <span className="text-xs font-bold text-white">{profile?.education || 'BCA'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-zinc-500">Birthday</span>
                <span className="text-xs font-bold text-white">{profile?.birthday || 'June 12'}</span>
              </div>
            </div>
          </section>

          {/* Skills & Expertise */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Target size={14} className="text-rose-400" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Expertise</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {(profile?.skills || []).map((skill: string) => (
                <div key={skill} className="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[10px] font-bold text-rose-400">
                  {skill}
                </div>
              ))}
            </div>
          </section>

          {/* Projects */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Briefcase size={14} className="text-amber-400" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Projects</span>
            </div>
            <div className="space-y-3">
              {(profile?.projects || []).map((project: any) => (
                <div key={project.name} className="p-4 rounded-xl bg-white/5 border border-white/5">
                  <h4 className="text-xs font-bold text-white mb-1">{project.name}</h4>
                  <p className="text-[10px] text-zinc-500 leading-normal">{project.description}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Interests */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Heart size={14} className="text-indigo-400" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Interests</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {(profile?.interests || []).map((int: string) => (
                <div key={int} className="px-3 py-1.5 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-[10px] font-medium text-zinc-400">
                  {int}
                </div>
              ))}
            </div>
          </section>

        </div>

        {/* Footer info */}
        <div className="p-8 border-t border-white/5">
          <div className="flex items-center gap-3 p-4 rounded-2xl bg-green-500/5 border border-green-500/10">
            <ShieldCheck size={16} className="text-green-500" />
            <div>
              <p className="text-[10px] font-bold text-white uppercase tracking-wider">Privacy Guard Active</p>
              <p className="text-[9px] text-zinc-500">Personal data is never shared without your intent.</p>
            </div>
          </div>
        </div>
      </motion.div>
    </>
  );
}
