import './globals.css';
import Sidebar from '@/components/Sidebar';
import AutoKeyProvider from '@/components/AutoKeyProvider';
import AuthProvider from '@/components/AuthProvider';

export const metadata = {
  title: 'SecureShield — AI Insurance Eligibility Engine',
  description: 'Agentic AI-powered health insurance claim eligibility checker for Indian patients. 5 specialized agents, 18 custom tools, deterministic decision engine for zero-hallucination verdicts. IRDAI 2024 compliant.',
  keywords: 'health insurance, AI, IRDAI, claim eligibility, agentic AI, LangGraph, India',
  authors: [{ name: 'SecureShield' }],
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                if (localStorage.getItem('theme') === 'dark') {
                  document.documentElement.classList.add('dark');
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body>
        <AutoKeyProvider />
        <AuthProvider>
          <div className="app-layout">
            <Sidebar />
            <main className="main-content">
              {children}
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
