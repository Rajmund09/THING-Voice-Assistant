/**
 * useSocket.ts — THING v4.0
 * Centralized socket management with message deduplication.
 * Handles both user_message and response events with UUID dedup.
 */

import { useEffect, useReducer, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export interface Message {
  id: string;
  speaker: 'user' | 'thing';
  text: string;
  success?: boolean;
  action?: string;
  data?: any;
  timestamp: number;
}

export interface StatusState {
  state: 'idle' | 'listening' | 'processing' | 'speaking' | 'disconnected';
  text: string;
}

export interface Suggestion {
  id: string;
  message: string;
  action: string;
  icon: string;
  dismissible: boolean;
}

// ── Message Deduplication Reducer ────────────────────────────────────────────
type MsgAction =
  | { type: 'ADD'; payload: Message }
  | { type: 'CLEAR' };

function msgReducer(state: Message[], action: MsgAction): Message[] {
  switch (action.type) {
    case 'ADD': {
      // Dedup by ID — prevents double-render from stale closures or duplicate events
      if (state.some(m => m.id === action.payload.id)) return state;
      return [...state, action.payload];
    }
    case 'CLEAR':
      return [];
    default:
      return state;
  }
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useSocket(serverUrl: string) {
  const [messages, dispatch] = useReducer(msgReducer, []);
  const [status, setStatus] = useState<StatusState>({ state: 'disconnected', text: 'Offline' });
  const [connected, setConnected] = useState(false);
  const [internetConnected, setInternetConnected] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socket = io(serverUrl, {
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      setConnected(true);
      setStatus({ state: 'idle', text: 'Systems Online' });
      socket.emit('get_profile');
    });

    socket.on('disconnect', () => {
      setConnected(false);
      setStatus({ state: 'disconnected', text: 'Offline' });
    });

    socket.on('status', (data: { state: string; text: string }) => {
      setStatus({ state: data.state as StatusState['state'], text: data.text });
    });

    socket.on('connectivity_status', (data: { online: boolean }) => {
      setInternetConnected(data.online);
    });

    socket.on('profile_data', (data: any) => {
      setProfile(data);
    });

    // User message (sent by server when text_command received)
    socket.on('user_message', (data: { id: string; text: string }) => {
      dispatch({
        type: 'ADD',
        payload: {
          id: data.id,
          speaker: 'user',
          text: data.text,
          timestamp: Date.now(),
        },
      });
    });

    // THING response packet — single source of truth
    socket.on('response', (packet: {
      id: string;
      action: string;
      final_response: string;
      speak_text: string;
      success: boolean;
      data?: any;
    }) => {
      if (!packet.final_response) return;
      dispatch({
        type: 'ADD',
        payload: {
          id: packet.id,
          speaker: 'thing',
          text: packet.final_response,
          success: packet.success,
          action: packet.action,
          data: packet.data,
          timestamp: Date.now(),
        },
      });
    });

    socket.on('proactive_suggestion', (suggestion: Suggestion) => {
      setSuggestions(prev => {
        // Prevent duplicates
        if (prev.some(s => s.id === suggestion.id)) return prev;
        // Keep only last 3
        return [...prev.slice(-2), suggestion];
      });
    });

    return () => {
      socket.removeAllListeners();
      socket.close();
    };
  }, [serverUrl]);

  const sendCommand = useCallback((command: string) => {
    if (!socketRef.current || !command.trim()) return;
    socketRef.current.emit('text_command', { command: command.trim() });
  }, []);

  const stopSpeaking = useCallback(() => {
    socketRef.current?.emit('stop_speaking');
  }, []);

  const updateVoiceSettings = useCallback((settings: any) => {
    socketRef.current?.emit('update_voice_settings', settings);
  }, []);

  const fetchProfile = useCallback(() => {
    socketRef.current?.emit('get_profile');
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR' });
  }, []);

  const dismissSuggestion = useCallback((id: string) => {
    setSuggestions(prev => prev.filter(s => s.id !== id));
  }, []);

  const emitEvent = useCallback((event: string, data: any) => {
    socketRef.current?.emit(event, data);
  }, []);

  return { messages, status, connected, internetConnected, profile, suggestions, sendCommand, stopSpeaking, updateVoiceSettings, fetchProfile, clearMessages, dismissSuggestion, emitEvent, socket: socketRef.current };
}
