'use client';

import { Toaster } from 'sonner';

export function ToastProvider({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster
        position="bottom-right"
        theme="dark"
        richColors
        closeButton
        expand={false}
        duration={3500}
        toastOptions={{
          classNames: {
            toast: 'bg-[#1A1A1A] text-white border border-white/10 shadow-xl',
            description: 'text-slate-200',
            actionButton: 'bg-white text-[#1A1A1A] hover:bg-slate-100',
            cancelButton: 'bg-slate-800 text-white hover:bg-slate-700',
            closeButton: 'bg-slate-800 text-white hover:bg-slate-700',
          },
        }}
      />
    </>
  );
}
