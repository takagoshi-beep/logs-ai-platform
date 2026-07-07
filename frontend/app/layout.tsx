import "./globals.css";
import { ReactNode } from "react";
import { Navigation } from "@/components/navigation";
import { AuthProvider } from "@/lib/auth-context";
import { AuthGate } from "@/components/auth-gate";

export const metadata = {
  title: "LOGS AI OS V0.1",
  description: "Work-first product skeleton",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AuthGate>
            <div className="mx-auto grid min-h-screen max-w-[1320px] grid-cols-1 gap-5 p-5 lg:grid-cols-[250px_1fr]">
              <Navigation />
              <main className="space-y-5">{children}</main>
            </div>
          </AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}
