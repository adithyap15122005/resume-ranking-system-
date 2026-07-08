import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Toaster } from "react-hot-toast";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: {
    default: "HireIQ — AI Hiring Intelligence Platform",
    template: "%s | HireIQ",
  },
  description:
    "Production-grade AI recruiting platform with SBERT semantic ranking, SHAP explainability, FAISS vector search, and intelligent recruiter workflows.",
  keywords: ["AI recruiting", "resume ranking", "hiring intelligence", "SBERT", "ATS"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "hsl(var(--card))",
                color: "hsl(var(--card-foreground))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.75rem",
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
