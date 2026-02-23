import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/layout/sidebar";

export const metadata: Metadata = {
  title: "RefLens",
  description: "AI-powered scientific paper database",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Sidebar />
          <main className="ml-56 min-h-screen p-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
