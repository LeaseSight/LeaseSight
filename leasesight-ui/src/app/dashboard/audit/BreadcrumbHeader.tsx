'use client';

import { BackNavigation } from '@/components/BackNavigation';

export function BreadcrumbHeader() {
  return <BackNavigation breadcrumbs={[{ label: 'Dashboard' }, { label: 'Audit' }]} useBackButton />;
}
