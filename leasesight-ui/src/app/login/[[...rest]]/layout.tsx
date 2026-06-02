/** Clerk path-routing segments required for `output: 'export'`. */
export function generateStaticParams() {
  const segments = [
    [],
    ['sign-in'],
    ['sign-up'],
    ['sso-callback'],
    ['factor-one'],
    ['factor-two'],
    ['reset-password'],
    ['continue'],
    ['verify'],
  ];
  return segments.map(rest => ({ rest }));
}

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
