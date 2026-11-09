import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PactPal — AI-Refereed Escrow for Freelancers",
  description: "Hire. Build. Get paid. The AI referee makes sure everyone wins. Money held. Work verified. Everyone paid fairly.",
  keywords: "escrow, freelance, AI referee, PayPal, contracts, verification",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
