import './globals.css';
import Sidebar from '@/components/Sidebar';

export const metadata = {
  title: 'SecureShield — AI Insurance Eligibility Engine',
  description: 'Agentic AI-powered health insurance claim eligibility checker for Indian patients. Uses ReAct pattern with 12 custom tools for deterministic, zero-hallucination verdicts.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
