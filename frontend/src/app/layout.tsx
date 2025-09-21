import type { Metadata, Viewport } from "next";
import { Crimson_Text, Crimson_Pro } from "next/font/google";
import "./globals.css";

// Configure the primary font (Crimson Text) for headings
const crimson = Crimson_Text({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-crimson", // CSS variable for Tailwind
});

// Configure the secondary font (Crimson Pro) for body text
const crimsonPro = Crimson_Pro({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-crimson-pro", // CSS variable for Tailwind
});

export const metadata: Metadata = {
  title: "Vero",
  description: "Proofread. Analyze. Simplified.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Vero",
  },
};

export const viewport: Viewport = {
  themeColor: "#91C8E4",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${crimson.variable} ${crimsonPro.variable} font-crimson-pro antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

