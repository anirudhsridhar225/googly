import { Geist, Geist_Mono } from "next/font/google";
import { Playfair_Display } from 'next/font/google';
import "./globals.css";

const playfair = Playfair_Display({
  subsets: ['latin'],
  weight: ['400', '700'],
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Legal Document Analyzer",
  description: "Analyze legal documents for clause severity, predatory nature, and exposure levels",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Legal Document Analyzer",
  },
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: "website",
    siteName: "Legal Document Analyzer",
    title: "Legal Document Analyzer",
    description: "Analyze legal documents for clause severity, predatory nature, and exposure levels",
  },
  twitter: {
    card: "summary",
    title: "Legal Document Analyzer",
    description: "Analyze legal documents for clause severity, predatory nature, and exposure levels",
  },
};

export const viewport: Viewport = {
  themeColor: "#4F46E5",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="description" content="Analyze legal documents for clause severity, predatory nature, and exposure levels" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content="Legal Document Analyzer" />
        <meta name="theme-color" content="#4F46E5" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icon-512x512.png" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${playfair.className} antialiased`}
      >
        {/* Global loader overlay */}
        <Loader />
        {children}
      </body>
    </html>
  );
}