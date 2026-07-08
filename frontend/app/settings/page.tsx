"use client";

import { Card, SectionHeader, Button, Badge } from "@/components/design-system";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const [connected, setConnected] = useState<boolean | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const gmailParam = searchParams.get("gmail");
    if (gmailParam === "connected") setMessage("Gmailを連携しました。");
    if (gmailParam === "error") setMessage("Gmail連携に失敗しました。もう一度お試しください。");
    if (gmailParam === "mismatch") setMessage("ログイン中のアカウントと異なるGoogleアカウントが選択されました。ログイン中のアカウントで連携してください。");
  }, [searchParams]);

  useEffect(() => {
    fetch(`${API_BASE}/api/integrations/gmail/status`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setConnected(!!data.connected))
      .catch(() => setConnected(false));
  }, [message]);

  async function handleDisconnect() {
    await fetch(`${API_BASE}/api/integrations/gmail`, {
      method: "DELETE",
      credentials: "include",
    });
    setConnected(false);
    setMessage("Gmail連携を解除しました。");
  }

  return (
    <div className="space-y-6">
      <SectionHeader title="設定" subtitle="外部サービス連携を管理します。" />

      {message && (
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-ink">
          {message}
        </div>
      )}

      <Card>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-ink">Gmail</h3>
              {connected === true && <Badge label="連携済み" tone="success" />}
              {connected === false && <Badge label="未連携" tone="default" />}
            </div>
            <p className="mt-1 text-xs text-sub">
              「相談」で自分宛のメールを検索・参照できるようになります（現時点では読み取りのみ、送信は未対応）。
            </p>
          </div>
          {connected ? (
            <Button tone="ghost" size="sm" onClick={handleDisconnect}>
              連携を解除
            </Button>
          ) : (
            <Button
              tone="primary"
              size="sm"
              onClick={() => {
                window.location.href = `${API_BASE}/api/integrations/gmail/connect`;
              }}
            >
              Gmailを連携する
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
