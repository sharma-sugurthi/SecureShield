import './globals.css';
import Sidebar from '@/components/Sidebar';
import AutoKeyProvider from '@/components/AutoKeyProvider';
import AuthProvider from '@/components/AuthProvider';
import FeedbackWidget from '@/components/FeedbackWidget';

const BASE_URL = 'https://www.policyeye.app';

export const metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    default: 'PolicyEye — AI Insurance Eligibility Engine',
    template: '%s | PolicyEye',
  },
  description: 'Check your health insurance claim eligibility instantly using AI. Upload your policy, enter your case details, and get a verdict backed by IRDAI 2024 regulations. Zero guesswork, zero rejected claims.',
  keywords: [
    'health insurance India',
    'claim eligibility checker',
    'IRDAI 2024 regulations',
    'AI insurance',
    'policy upload',
    'health claim verification',
    'insurance dispute',
    'agentic AI',
    'PolicyEye',
    'medical insurance',
  ],
  authors: [{ name: 'PolicyEye', url: BASE_URL }],
  creator: 'PolicyEye',
  publisher: 'PolicyEye',
  applicationName: 'PolicyEye',
  category: 'Health Insurance',
  
  // Canonical
  alternates: {
    canonical: BASE_URL,
  },

  // Open Graph (Facebook, LinkedIn, WhatsApp)
  openGraph: {
    type: 'website',
    locale: 'en_IN',
    url: BASE_URL,
    siteName: 'PolicyEye',
    title: 'PolicyEye — AI-Powered Insurance Claim Eligibility Checker',
    description: 'Upload your health insurance policy and instantly verify claim eligibility. AI-powered verdicts backed by IRDAI 2024 regulations. Built for Indian patients.',
    images: [
      {
        url: `${BASE_URL}/og-image.png`,
        width: 1200,
        height: 630,
        alt: 'PolicyEye — AI Insurance Eligibility Engine',
        type: 'image/png',
      },
    ],
  },

  // Twitter Card
  twitter: {
    card: 'summary_large_image',
    title: 'PolicyEye — AI Insurance Claim Eligibility Checker',
    description: 'Upload your policy, check eligibility instantly. AI-powered verdicts backed by IRDAI 2024 regulations.',
    images: [`${BASE_URL}/og-image.png`],
    creator: '@policyeye_app',
  },

  // App Manifest & Icons
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    apple: '/logo.png',
  },

  // Robots
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
};

// JSON-LD Structured Data for Google rich results
const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'PolicyEye',
  alternateName: 'PolicyEye AI Insurance Engine',
  url: BASE_URL,
  description: 'AI-powered health insurance claim eligibility checker for Indian patients. Verify claims instantly with IRDAI 2024 regulation backing.',
  applicationCategory: 'HealthApplication',
  operatingSystem: 'Web',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'INR',
  },
  creator: {
    '@type': 'Organization',
    name: 'PolicyEye',
    url: BASE_URL,
  },
  featureList: [
    'AI-powered claim eligibility verification',
    'Policy PDF upload and analysis',
    'IRDAI 2024 regulation cross-referencing',
    'Real-time chat assistant for insurance queries',
    'Dispute claim filing with AI-generated packages',
    'Full audit trail of every AI decision',
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
        
        {/* JSON-LD Structured Data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />

        {/* Dark mode init */}
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
          <FeedbackWidget />
        </AuthProvider>
      </body>
    </html>
  );
}
