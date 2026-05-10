import Link from 'next/link';

interface BrandLogoProps {
  compact?: boolean;
  className?: string;
}

export function BrandLogo({ compact = false, className = '' }: BrandLogoProps) {
  return (
    <Link href="/" className={`inline-flex items-center justify-center gap-3 ${className}`} aria-label="LeaseSight home">
      {compact ? (
        <span className="relative flex h-9 w-9 items-center justify-center overflow-hidden border border-[var(--border-default)] bg-[var(--bg-secondary)]">
          <span className="absolute h-7 w-4 border-r-[7px] border-t-[7px] border-[var(--text-primary)]" style={{ transform: 'skewY(-28deg) translateX(1px)' }} />
          <span className="absolute bottom-1.5 h-5 w-2 border-r-[5px] border-[var(--text-secondary)]" />
        </span>
      ) : (
        <img
          src="/leasesight-logo-cropped.png"
          alt="LeaseSight"
          className="block h-8 w-auto object-contain"
        />
      )}
      <span className="sr-only">
        LeaseSight
      </span>
    </Link>
  );
}
