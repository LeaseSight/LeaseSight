'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { MigrationDashboard } from '@/components/MigrationDashboard';
import { api } from '@/lib/api';

export default function MigrationPage() {
  const [documents, setDocuments] = useState<string[]>([]);

  // Fetch documents on load (shared logic with header)
  useEffect(() => {
    api.documents().then(d => setDocuments(d.documents)).catch(() => {});
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-white">
      {/* Shared Header with Service Switcher */}
      <Header
        isAuditing={false}
        onToggleNetwork={() => {}}
        documents={documents}
        onSelectDoc={() => {}}
      />

      {/* Migration Workstation */}
      <MigrationDashboard />
    </div>
  );
}
