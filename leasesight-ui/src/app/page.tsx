'use client';

import { useState } from 'react';
import Link from 'next/link';
import { SignInButton, UserButton, useAuth } from '@clerk/nextjs';
import { ArrowRight, Binary, Brackets, FileSearch, Gauge, Layers3, Loader2, X } from 'lucide-react';
import { BrandLogo } from '@/components/BrandLogo';
import { showErrorToast, showSuccessToast } from '@/lib/errorMessages';

type ModalName = 'about' | 'contact' | null;

const features = [
  {
    icon: FileSearch,
    title: 'Surgical AI Extraction',
    copy: 'Real-time extraction of lessor, lease amount, tenure, and operational terms from dense commercial PDFs.',
  },
  {
    icon: Brackets,
    title: 'Verbatim Visual Grounding',
    copy: 'Direct PDF highlighting with quote-level evidence and coordinate normalization built for review workflows.',
  },
  {
    icon: Gauge,
    title: 'Intelligent Risk Scoring',
    copy: 'Automated detection of governing law conflicts, notice gaps, high-interest caps, and unusual commercial exposure.',
  },
  {
    icon: Layers3,
    title: 'Industrial MLOps',
    copy: 'Powered by Azure Document Intelligence and Pinecone Vector RAG for scalable archive ingestion.',
  },
];

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function Modal({ name, onClose }: { name: ModalName; onClose: () => void }) {
  if (!name) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/30 px-4 backdrop-blur-sm">
      <div className="w-full max-w-xl border border-slate-300 bg-[#F9FAFB] p-6 shadow-2xl">
        <div className="mb-5 flex items-start justify-between gap-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">LeaseSight</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#1A1A1A]">
              {name === 'about' ? 'About Us' : 'Contact Us'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="border border-slate-300 p-2 text-[#1A1A1A] transition hover:-translate-y-0.5 hover:bg-[#1A1A1A] hover:text-white"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {name === 'about' ? (
          <div className="space-y-4 text-sm leading-6 text-slate-600">
            <p>
              LeaseSight is a technical legal-auditing platform built for high-stakes commercial logistics,
              industrial leases, and enterprise document operations.
            </p>
            <p>
              The product combines document intelligence, vector retrieval, visual evidence grounding, and
              risk scoring so teams can review critical clauses with confidence.
            </p>
          </div>
        ) : (
          <ContactForm onSuccess={onClose} />
        )}
      </div>
    </div>
  );
}

function ContactForm({ onSuccess }: { onSuccess?: () => void }) {
  const [email, setEmail] = useState('');
  const [industry, setIndustry] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailRegex.test(email.trim())) return showErrorToast(new Error('Please enter a valid email address.'));
    if (!industry.trim()) return showErrorToast(new Error('Please enter your industry.'));
    if (!message.trim()) return showErrorToast(new Error('Please enter a message.'));
    if (submitting) return;

    setSubmitting(true);
    try {
      await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), industry: industry.trim(), company_size: companySize, message: message.trim() }),
      });
      showSuccessToast('Thank you. A LeaseSight consultant will reach out to you within 24 hours');
      setEmail('');
      setIndustry('');
      setCompanySize('');
      setMessage('');
      onSuccess?.();
    } catch (err) {
      showErrorToast(err, 'Submission failed');
    } finally {
      setTimeout(() => setSubmitting(false), 2000);
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-3">
      <input value={email} onChange={e => setEmail(e.target.value)} className="border border-slate-300 bg-white px-3 py-3 text-sm outline-none transition focus:border-[#1A1A1A]" placeholder="Work email" />
      <input value={industry} onChange={e => setIndustry(e.target.value)} className="border border-slate-300 bg-white px-3 py-3 text-sm outline-none transition focus:border-[#1A1A1A]" placeholder="Industry" />
      <select value={companySize} onChange={e => setCompanySize(e.target.value)} className="border border-slate-300 bg-white px-3 py-3 text-sm text-slate-500 outline-none transition focus:border-[#1A1A1A]">
        <option value="">Company Size</option>
        <option>1-50</option>
        <option>51-250</option>
        <option>251-1,000</option>
        <option>1,000+</option>
      </select>
      <textarea value={message} onChange={e => setMessage(e.target.value)} className="min-h-28 border border-slate-300 bg-white px-3 py-3 text-sm outline-none transition focus:border-[#1A1A1A]" placeholder="Tell us about your lease audit workflow" />
      <button disabled={submitting} type="submit" className="mt-2 bg-[#1A1A1A] px-5 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50">
        {submitting ? <span className="inline-flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Sending...</span> : 'Submit Inquiry'}
      </button>
    </form>
  );
}

export default function LandingPage() {
  const { userId } = useAuth();
  const [modal, setModal] = useState<ModalName>(null);

  return (
    <main className="min-h-screen bg-[#F9FAFB] text-[#1A1A1A]">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/80 bg-[#F9FAFB]/82 backdrop-blur-xl">
        <nav className="enterprise-container flex h-[72px] items-center justify-between py-4">
          <BrandLogo />
          <div className="hidden items-center gap-8 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 md:flex">
            <a href="#offer" className="transition hover:text-[#1A1A1A]">What We Offer</a>
            <button onClick={() => setModal('about')} className="transition hover:text-[#1A1A1A]">About Us</button>
            <button onClick={() => setModal('contact')} className="transition hover:text-[#1A1A1A]">Contact Us</button>
          </div>
          <div className="flex items-center gap-3">
            {!userId && (
              <>
              <SignInButton mode="modal">
                <button className="hidden border border-slate-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#1A1A1A] transition hover:-translate-y-0.5 hover:border-[#1A1A1A] sm:block">
                  Login
                </button>
              </SignInButton>
              <Link href="/dashboard/audit" className="bg-[#1A1A1A] px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-white transition hover:-translate-y-0.5 hover:bg-slate-700">
                Get Started
              </Link>
              </>
            )}

            {userId && (
              <>
                <Link href="/dashboard/audit" className="bg-[#1A1A1A] px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-white transition hover:-translate-y-0.5 hover:bg-slate-700">
                  Dashboard
                </Link>
                <UserButton />
              </>
            )}
          </div>
        </nav>
      </header>

      <section className="enterprise-container flex min-h-[84vh] flex-col items-center justify-center pt-20 text-center">
        <div className="mb-7 inline-flex items-center gap-2 border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
          <Binary className="h-4 w-4 text-[#1A1A1A]" />
          Industrial legal intelligence
        </div>
        <h1 className="max-w-5xl text-5xl font-semibold tracking-tight text-[#1A1A1A] sm:text-6xl lg:text-7xl">
          Intelligence in Every Clause.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-500">
          AI-Powered Lease Auditing for Industrial Excellence.
        </p>
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row">
          <Link href="/dashboard/audit" className="group inline-flex items-center gap-3 bg-[#1A1A1A] px-6 py-3 text-sm font-semibold uppercase tracking-[0.16em] text-white transition hover:-translate-y-0.5 hover:bg-slate-700">
            Get Started
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
          </Link>
          <a href="#offer" className="border border-slate-300 px-6 py-3 text-sm font-semibold uppercase tracking-[0.16em] text-[#1A1A1A] transition hover:-translate-y-0.5 hover:border-[#1A1A1A] hover:bg-white">
            What We Offer
          </a>
        </div>
      </section>

      <section id="offer" className="border-y border-slate-200 bg-white py-14">
        <div className="enterprise-container">
          <div className="mb-8 max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">What We Offer</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-tight text-[#1A1A1A]">A disciplined audit layer for lease-heavy operations.</h2>
          </div>
          <div className="grid gap-px overflow-hidden border border-slate-200 bg-slate-200 md:grid-cols-2 lg:grid-cols-4">
            {features.map(feature => {
              const Icon = feature.icon;
              return (
                <article key={feature.title} className="bg-[#F9FAFB] p-6 transition hover:bg-white">
                  <Icon className="mb-8 h-7 w-7 text-[#1A1A1A]" />
                  <h3 className="text-lg font-semibold text-[#1A1A1A]">{feature.title}</h3>
                  <p className="mt-4 text-sm leading-6 text-slate-500">{feature.copy}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <footer className="bg-[#1A1A1A] py-10 text-white">
        <div className="enterprise-container grid gap-10 md:grid-cols-[1.2fr_1fr_0.8fr]">
          <div>
            <BrandLogo className="text-white [&_span:last-child]:text-white" />
            <p className="mt-6 max-w-md text-sm leading-6 text-slate-300">
              LeaseSight is a technical legal-auditing platform built for high-stakes commercial logistics,
              industrial real estate, and document-heavy operating teams.
            </p>
          </div>
          <form className="grid gap-3">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Contact Us</p>
            <input className="border border-white/15 bg-white/5 px-3 py-3 text-sm outline-none transition placeholder:text-slate-500 focus:border-white" placeholder="Industry" />
            <select className="border border-white/15 bg-white/5 px-3 py-3 text-sm text-slate-400 outline-none transition focus:border-white">
              <option>Company Size</option>
              <option>1-50</option>
              <option>51-250</option>
              <option>251-1,000</option>
              <option>1,000+</option>
            </select>
            <button type="button" className="border border-white bg-white px-4 py-3 text-sm font-semibold text-[#1A1A1A] transition hover:-translate-y-0.5 hover:bg-slate-200">
              Request Briefing
            </button>
          </form>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Quick Links</p>
            <div className="mt-5 grid gap-3 text-sm text-slate-300">
              <a className="transition hover:text-white" href="#">Terms of Service</a>
              <a className="transition hover:text-white" href="#">Privacy Policy</a>
              <a className="transition hover:text-white" href="#">Documentation</a>
            </div>
          </div>
        </div>
      </footer>

      <Modal name={modal} onClose={() => setModal(null)} />
    </main>
  );
}
