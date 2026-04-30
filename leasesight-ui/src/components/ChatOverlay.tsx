'use client';

import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, MapPin } from 'lucide-react';
import { api } from '@/lib/api';
import { ChatMessage, Annotation } from '@/lib/types';

interface ChatOverlayProps {
  selectedDoc: string;
  onLocate: (annotation: Annotation) => void;
}

export function ChatOverlay({ selectedDoc, onLocate }: ChatOverlayProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Reset chat when document changes
  useEffect(() => {
    setMessages([]);
  }, [selectedDoc]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const query = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: query }]);
    setIsLoading(true);

    try {
      const res = await api.chat(query, selectedDoc);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        source_text: res.source_text,
        page: res.page,
        annotation: res.annotation,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'An error occurred. Please try again.',
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-12 h-12 rounded-full flex items-center justify-center z-40 glow-emerald transition-transform hover:scale-110"
        style={{ background: 'var(--accent-emerald)' }}
      >
        <MessageSquare className="w-5 h-5 text-black" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] rounded-xl flex flex-col z-40 glass overflow-hidden"
         style={{ border: '1px solid var(--border-default)' }}>
      {/* Header */}
      <div className="h-11 flex items-center justify-between px-4 border-b"
           style={{ borderColor: 'var(--border-default)', background: 'rgba(15, 23, 42, 0.9)' }}>
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4" style={{ color: 'var(--accent-emerald)' }} />
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Document Chat</span>
        </div>
        <button onClick={() => setIsOpen(false)}
                className="w-6 h-6 flex items-center justify-center rounded hover:opacity-70">
          <X className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-10">
            <MessageSquare className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--text-secondary)' }} />
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Ask a question about this document
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm"
                 style={{
                   background: msg.role === 'user' ? 'var(--accent-emerald)' : 'var(--bg-card)',
                   color: msg.role === 'user' ? '#000' : 'var(--text-primary)',
                 }}>
              <p className="leading-relaxed">{msg.content}</p>
              {msg.role === 'assistant' && msg.annotation && (
                <button
                  onClick={() => onLocate(msg.annotation!)}
                  className="flex items-center gap-1 mt-2 text-xs transition-colors hover:opacity-80"
                  style={{ color: 'var(--accent-orange)' }}
                >
                  <MapPin className="w-3 h-3" />
                  Locate on Page {msg.page}
                </button>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="rounded-lg px-3 py-2" style={{ background: 'var(--bg-card)' }}>
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full animate-bounce"
                     style={{ background: 'var(--text-secondary)', animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 rounded-full animate-bounce"
                     style={{ background: 'var(--text-secondary)', animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 rounded-full animate-bounce"
                     style={{ background: 'var(--text-secondary)', animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t" style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask about this document..."
            className="flex-1 rounded-lg px-3 py-2 text-sm outline-none"
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-default)',
            }}
          />
          <button onClick={handleSend} disabled={!input.trim() || isLoading}
                  className="w-9 h-9 flex items-center justify-center rounded-lg transition-all disabled:opacity-30"
                  style={{ background: 'var(--accent-emerald)' }}>
            <Send className="w-4 h-4 text-black" />
          </button>
        </div>
      </div>
    </div>
  );
}
