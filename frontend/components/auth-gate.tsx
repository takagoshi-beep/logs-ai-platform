"use client";

import Script from "next/script";
import { useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth-context";
import { loginWithGoogle } from "@/lib/api-client";

declare global {
  interface Window {
    google?: any;
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

function GoogleSignInButton() {
  const buttonRef = useRef<HTMLDivElement>(null);
  const { refresh } = useAuth();

  async function handleCredential(response: { credential: string }) {
    const result = await loginWithGoogle(response.credential);
    if (result.success === false) {
      alert(result.error || "ログインできませんでした。社員として登録されたGoogleアカウントでログインしてください。");
      return;
    }
    await refresh();
  }

  function renderButton() {
    if (!window.google || !buttonRef.current || !GOOGLE_CLIENT_ID) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleCredential,
    });
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "outline",
      size: "large",
      text: "signin_with",
      locale: "ja",
    });
  }

  useEffect(() => {
    if (window.google) renderButton();
  }, []);

  return (
    <>
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onLoad={renderButton} />
      <div ref={buttonRef} />
    </>
  );
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-sub">読み込み中...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-ink">LOGS AI OS</h1>
          <p className="mt-2 mb-6 text-sm text-sub">
            社員として登録されたGoogleアカウントでログインしてください。
          </p>
          <div className="flex justify-center">
            {GOOGLE_CLIENT_ID ? (
              <GoogleSignInButton />
            ) : (
              <p className="text-xs text-red-600">
                GOOGLE_OAUTH_CLIENT_IDが設定されていません（NEXT_PUBLIC_GOOGLE_CLIENT_ID）。
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
