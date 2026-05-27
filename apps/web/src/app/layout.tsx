import type { Metadata, Viewport } from "next";
import { Mona_Sans } from "next/font/google";
import Script from "next/script";
import "./globals.css";

import { ThemeProvider } from "@/components/layout/theme-provider";
import { SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { Header } from "@/components/layout/header";
import { HealthBanner } from "@/components/layout/health-banner";
import { Toaster } from "@/components/ui/sonner";
import { QueryClientProvider } from "@/lib/query-client";
import { RefreshProvider } from "@/lib/refresh-context";

// Display face — used for page titles. Body copy uses the system stack
// defined in globals.css.
const monaSans = Mona_Sans({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Voice Memo AI Second Brain",
  description:
    "Capture voice memos from your browser, store them in Backblaze B2, and let an AI pipeline transcribe, tag, cross-reference, and summarize them into a searchable second brain.",
  manifest: "/manifest.webmanifest",
  applicationName: "Voice Memo AI Second Brain",
  appleWebApp: {
    capable: true,
    title: "Voice Memo",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${monaSans.variable} antialiased`}>
        <ThemeProvider>
          <QueryClientProvider>
            <RefreshProvider>
              <SidebarProvider>
                <TooltipProvider>
                  <AppSidebar />
                  <div className="flex flex-1 flex-col">
                    <Header />
                    <HealthBanner />
                    <main className="flex-1 overflow-auto p-6 lg:p-8">
                      {children}
                    </main>
                  </div>
                  <Toaster />
                </TooltipProvider>
              </SidebarProvider>
            </RefreshProvider>
          </QueryClientProvider>
        </ThemeProvider>
        {/* Register the (stub) service worker so the app installs as a PWA.
            The worker doesn't pre-cache anything yet — it's the minimal
            installable manifest. See docs/features/mobile-pwa.md. */}
        <Script id="register-sw" strategy="afterInteractive">
          {`if ('serviceWorker' in navigator) {
            window.addEventListener('load', function () {
              navigator.serviceWorker
                .register('/sw.js')
                .catch(function (err) {
                  console.warn('SW registration failed:', err);
                });
            });
          }`}
        </Script>
      </body>
    </html>
  );
}
