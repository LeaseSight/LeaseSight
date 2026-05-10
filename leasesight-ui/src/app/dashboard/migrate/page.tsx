'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { BackNavigation } from '@/components/BackNavigation';
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
      <div className="border-b border-[var(--border-default)] bg-white px-4 py-3">
        <div className="enterprise-container">
          <BackNavigation breadcrumbs={[{ label: 'Dashboard' }, { label: 'Migrate' }]} useBackButton />
        </div>
      </div>
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
