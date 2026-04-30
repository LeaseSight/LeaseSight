'use client';

interface CommitModalProps {
  onConfirm: () => void;
  onCancel: () => void;
  isCommitting: boolean;
}

export function CommitModal({ onConfirm, onCancel, isCommitting }: CommitModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center"
         style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div className="rounded-xl p-6 w-96 glass animate-fade-in">
        <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
          Commit to Knowledge Base
        </h3>
        <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
          This will mark the document as a verified legal precedent. All vectors will be tagged
          as <code className="px-1 py-0.5 rounded text-xs"
                    style={{ background: 'var(--bg-card)', color: 'var(--accent-emerald)' }}>
            status: verified
          </code>.
        </p>
        <div className="flex gap-3">
          <button onClick={onCancel} disabled={isCommitting}
                  className="flex-1 py-2 rounded-lg text-sm font-medium transition-colors"
                  style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border-default)' }}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={isCommitting}
                  className="flex-1 py-2 rounded-lg text-sm font-semibold glow-emerald transition-all"
                  style={{ background: 'var(--accent-emerald)', color: '#000' }}>
            {isCommitting ? 'Committing...' : 'Yes, Commit'}
          </button>
        </div>
      </div>
    </div>
  );
}
