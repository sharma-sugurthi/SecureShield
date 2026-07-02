'use client';

/**
 * About PolicyEye — Animated explainer page for non-technical users.
 * Explains the problem, solution, step-by-step flow, and FAQ.
 */

import { useState, useEffect, useRef } from 'react';
import {
    UploadIcon, EditIcon, LayersIcon, CheckCircleIcon, ScaleIcon,
    FileTextIcon, XCircleIcon, DollarSignIcon, ShieldIcon,
    ArrowRightIcon, ZapIcon, LockIcon, HelpCircleIcon,
    AlertTriangleIcon, TargetIcon, RocketIcon
} from '@/components/icons';

/* ── Scroll-triggered fade-in hook ── */
function useReveal() {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return [ref, visible];
}

function RevealSection({ children, delay = 0, className = '' }) {
  const [ref, visible] = useReveal();
  return (
    <div
      ref={ref}
      className={`about-reveal ${visible ? 'about-visible' : ''} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

/* ── FAQ Accordion ── */
function FAQItem({ question, answer }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`about-faq-item ${open ? 'open' : ''}`} onClick={() => setOpen(!open)}>
      <div className="about-faq-q">
        <span>{question}</span>
        <span className="about-faq-chevron">{open ? '−' : '+'}</span>
      </div>
      <div className="about-faq-a">{answer}</div>
    </div>
  );
}

/* ── Main Page ── */
export default function AboutPage() {
  const [activeStep, setActiveStep] = useState(0);

  /* Auto-cycle through the flow steps */
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep(prev => (prev + 1) % 5);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const FLOW_STEPS = [
    {
      icon: <UploadIcon size={24} />,
      title: 'Upload Your Policy',
      desc: 'Simply upload the PDF of your health insurance policy. Our AI reads every clause, sub-limit, and exclusion automatically.',
      color: 'var(--primary-500)',
    },
    {
      icon: <EditIcon size={24} />,
      title: 'Enter Case Details',
      desc: 'Tell us about the hospitalization — patient name, procedure, hospital, costs. Just fill a simple form.',
      color: 'var(--blue-500)',
    },
    {
      icon: <LayersIcon size={24} />,
      title: 'AI Pipeline Analyzes',
      desc: '5 specialized AI agents work together — normalizing medical terms, checking regulations, computing coverage, and explaining the result.',
      color: 'var(--amber-500)',
    },
    {
      icon: <CheckCircleIcon size={24} />,
      title: 'Get Your Verdict',
      desc: 'Instant verdict: APPROVED, PARTIAL, or DENIED — with the exact cost breakdown and rule-by-rule explanation.',
      color: 'var(--green-500)',
    },
    {
      icon: <ScaleIcon size={24} />,
      title: 'Dispute If Unfair',
      desc: 'If your claim was unfairly denied, generate a formal grievance package citing insurance regulations — ready to send to your insurer.',
      color: 'var(--red-500)',
    },
  ];

  const STATS = [
    { number: '68%', label: 'of policyholders don\'t read their policy documents', icon: <FileTextIcon size={24} /> },
    { number: '23%', label: 'of health claims face partial/full rejection', icon: <XCircleIcon size={24} /> },
    { number: '$1.2K', label: 'average out-of-pocket loss per rejected claim', icon: <DollarSignIcon size={24} /> },
    { number: '49', label: 'regulation clauses indexed', icon: <ScaleIcon size={24} /> },
  ];

  const FAQS = [
    {
      question: 'What is health insurance claim eligibility?',
      answer: 'When you get hospitalized and file a claim, your insurance company checks if the treatment is covered under your policy. Eligibility means whether (and how much) the insurer will pay. PolicyEye does this check before you even get admitted — so there are no surprises.',
    },
    {
      question: 'Why do insurance claims get rejected?',
      answer: 'Common reasons include: pre-existing disease waiting periods not met, room rent exceeding the sub-limit, procedures listed under exclusions, or the policy\'s moratorium period. These rules are buried in complex documents that most people never read.',
    },
    {
      question: 'What is IRDAI and why does it matter?',
      answer: 'IRDAI (Insurance Regulatory and Development Authority of India) sets the rules that every insurance company must follow. PolicyEye checks your claim against the latest IRDAI 2024 regulations — the same rules your insurer is legally bound by.',
    },
    {
      question: 'Is my data safe?',
      answer: 'Yes. Your policy documents and medical details are processed securely. We use JWT authentication, encrypted connections, and never share your data with third parties. Your information is only used for eligibility analysis.',
    },
    {
      question: 'Does the AI make the final decision?',
      answer: 'No! This is a key design principle. The AI extracts information and explains results, but the actual APPROVED/DENIED decision is made by a deterministic rules engine — like a calculator. Zero AI hallucinations in decisions.',
    },
    {
      question: 'Can I dispute an unfair rejection?',
      answer: 'Absolutely. PolicyEye\'s Grievance Agent generates a professional grievance letter citing specific IRDAI regulations that support your case. You can send this directly to your insurer\'s Grievance Redressal Officer.',
    },
  ];

  return (
    <>
      {/* ── Hero Section ── */}
      <RevealSection>
        <div className="about-hero">
          <div className="about-hero-badge">Understanding PolicyEye</div>
          <h1 className="about-hero-title">
            Your Insurance Policy is <span className="about-gradient-text">47 Pages</span> Long.<br />
            Did You Read It?
          </h1>
          <p className="about-hero-subtitle">
            PolicyEye reads your entire policy in seconds and tells you — before hospitalization —
            exactly how much your insurer will pay. No legal jargon. No surprises.
          </p>
        </div>
      </RevealSection>

      {/* ── Problem Stats ── */}
      <RevealSection delay={100}>
        <div className="about-stats-grid">
          {STATS.map((stat, i) => (
            <div key={i} className="about-stat-card">
              <div className="about-stat-icon">{stat.icon}</div>
              <div className="about-stat-number">{stat.number}</div>
              <div className="about-stat-label">{stat.label}</div>
            </div>
          ))}
        </div>
      </RevealSection>

      {/* ── The Problem ── */}
      <RevealSection delay={100}>
        <div className="card about-section">
          <div className="about-section-badge">The Problem</div>
          <h2 className="about-section-title">Insurance Shouldn't Be a Guessing Game</h2>
          <div className="about-problem-grid">
            <div className="about-problem-card">
              <div className="about-problem-icon" style={{ color: 'var(--primary-500)' }}><FileTextIcon size={32} /></div>
              <h3>Complex Policies</h3>
              <p>Insurance policies are 30-50 page legal documents with terms like "sub-limits", "co-pay clauses", and "moratorium periods" that most people never understand.</p>
            </div>
            <div className="about-problem-card">
              <div className="about-problem-icon" style={{ color: 'var(--amber-500)' }}><AlertTriangleIcon size={32} /></div>
              <h3>Surprise Rejections</h3>
              <p>Families discover their claim is rejected after the surgery — when it's too late. They end up paying lakhs out of pocket for something they thought was covered.</p>
            </div>
            <div className="about-problem-card">
              <div className="about-problem-icon" style={{ color: 'var(--red-500)' }}><HelpCircleIcon size={32} /></div>
              <h3>No Way to Check</h3>
              <p>Before PolicyEye, there was no tool that could read your specific policy and tell you: "Yes, this procedure is covered for ₹X" — before you get admitted.</p>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ── How It Works — Animated Flow ── */}
      <RevealSection delay={100}>
        <div className="card about-section">
          <div className="about-section-badge">How It Works</div>
          <h2 className="about-section-title">5 Simple Steps to Know Your Coverage</h2>

          <div className="about-flow-container">
            {/* Step indicators */}
            <div className="about-flow-steps">
              {FLOW_STEPS.map((step, i) => (
                <div
                  key={i}
                  className={`about-flow-step ${i === activeStep ? 'active' : ''} ${i < activeStep ? 'done' : ''}`}
                  onClick={() => setActiveStep(i)}
                >
                  <div
                    className="about-flow-step-circle"
                    style={{ '--step-color': step.color }}
                  >
                    <span className="about-flow-step-icon">{step.icon}</span>
                  </div>
                  <div className="about-flow-step-label">{step.title}</div>
                  {i < FLOW_STEPS.length - 1 && (
                    <div className={`about-flow-connector ${i < activeStep ? 'filled' : ''}`} />
                  )}
                </div>
              ))}
            </div>

            {/* Active step detail */}
            <div className="about-flow-detail" key={activeStep}>
              <div className="about-flow-detail-icon" style={{ background: FLOW_STEPS[activeStep].color }}>
                {FLOW_STEPS[activeStep].icon}
              </div>
              <div>
                <h3 className="about-flow-detail-title">
                  Step {activeStep + 1}: {FLOW_STEPS[activeStep].title}
                </h3>
                <p className="about-flow-detail-desc">{FLOW_STEPS[activeStep].desc}</p>
              </div>
            </div>

            {/* Progress bar */}
            <div className="about-flow-progress">
              <div
                className="about-flow-progress-fill"
                style={{ width: `${((activeStep + 1) / FLOW_STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ── What Makes Us Different ── */}
      <RevealSection delay={100}>
        <div className="card about-section">
          <div className="about-section-badge">Why PolicyEye</div>
          <h2 className="about-section-title">Built Different — By Design</h2>
          <div className="about-diff-grid">
            {[
              {
                icon: <TargetIcon size={24} />,
                title: 'Zero AI Hallucinations',
                desc: 'The verdict (APPROVED/DENIED) is computed by a deterministic rules engine — like a calculator. AI only explains the result in plain language.',
                highlight: true,
              },
              {
                icon: <ShieldIcon size={24} />,
                title: 'Regulatory Compliant',
                desc: 'Every decision references the actual regulation clause. Same rules your insurer is legally required to follow.',
                highlight: false,
              },
              {
                icon: <ZapIcon size={24} />,
                title: 'Results in Seconds',
                desc: 'What would take an insurance expert hours to verify, PolicyEye does in under 15 seconds using 5 specialized AI agents.',
                highlight: false,
              },
              {
                icon: <LockIcon size={24} />,
                title: 'Your Data, Your Control',
                desc: 'JWT-secured, encrypted, and private. We never share your medical or policy data with anyone.',
                highlight: false,
              },
            ].map((item, i) => (
              <div key={i} className={`about-diff-card ${item.highlight ? 'highlighted' : ''}`}>
                <div className="about-diff-icon">{item.icon}</div>
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* ── FAQ Section ── */}
      <RevealSection delay={100}>
        <div className="card about-section">
          <div className="about-section-badge">Common Questions</div>
          <h2 className="about-section-title">Frequently Asked Questions</h2>
          <div className="about-faq-list">
            {FAQS.map((faq, i) => (
              <FAQItem key={i} question={faq.question} answer={faq.answer} />
            ))}
          </div>
        </div>
      </RevealSection>

      {/* ── CTA ── */}
      <RevealSection delay={100}>
        <div className="about-cta">
          <h2>Ready to Check Your Coverage?</h2>
          <p>Upload your policy and get your first eligibility verdict — completely free.</p>
          <a href="/upload" className="about-cta-btn">
            Upload Your Policy Now
          </a>
        </div>
      </RevealSection>
    </>
  );
}
