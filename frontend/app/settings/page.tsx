"use client";

import { Card, SectionHeader, Button, Badge } from "@/components/design-system";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type Provider = "gmail" | "slack";

const PROVIDER_LABEL: Record<Provider, string> = {
  gmail: "Gmail",
  slack: "Slack",
};

const PROVIDER_DESCRIPTION: Record<Provider, string> = {
  gmail: "「相談」で自分宛のメールを検索・参照できるようになります（現時点では読み取りのみ、送信は未対応）。",
  slack: "「相談」で自分が参加しているチャンネル・DMのメッセージを検索できるようになります。",
};

function IntegrationCard({
  provider,
  connected,
  onConnect,
  onDisconnect,
}: {
  provider: Provider;
  connected: boolean | null;
  onConnect: () => void;
  onDisconnect: () => void;
}) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-ink">{PROVIDER_LABEL[provider]}</h3>
            {connected === true && <Badge label="連携済み" tone="success" />}
            {connected === false && <Badge label="未連携" tone="default" />}
          </div>
          <p className="mt-1 text-xs text-sub">{PROVIDER_DESCRIPTION[provider]}</p>
        </div>
        {connected ? (
          <Button tone="ghost" size="sm" onClick={onDisconnect}>
            連携を解除
          </Button>
        ) : (
          <Button tone="primary" size="sm" onClick={onConnect}>
            {PROVIDER_LABEL[provider]}を連携する
          </Button>
        )}
      </div>
    </Card>
  );
}

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const [gmailConnected, setGmailConnected] = useState<boolean | null>(null);
  const [slackConnected, setSlackConnected] = useState<boolean | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const gmailParam = searchParams.get("gmail");
    if (gmailParam === "connected") setMessage("Gmailを連携しました。");
    if (gmailParam === "error") setMessage("Gmail連携に失敗しました。もう一度お試しください。");
    if (gmailParam === "mismatch") setMessage("ログイン中のアカウントと異なるGoogleアカウントが選択されました。ログイン中のアカウントで連携してください。");

    const slackParam = searchParams.get("slack");
    if (slackParam === "connected") setMessage("Slackを連携しました。");
    if (slackParam === "error") setMessage("Slack連携に失敗しました。もう一度お試しください。");
    if (slackParam === "mismatch") setMessage("ログイン中のアカウントと異なるSlackアカウントが選択されました。ログイン中のアカウントで連携してください。");
  }, [searchParams]);

  useEffect(() => {
    fetch(`${API_BASE}/api/integrations/gmail/status`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setGmailConnected(!!data.connected))
      .catch(() => setGmailConnected(false));

    fetch(`${API_BASE}/api/integrations/slack/status`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setSlackConnected(!!data.connected))
      .catch(() => setSlackConnected(false));
  }, [message]);

  async function handleDisconnect(provider: Provider) {
    await fetch(`${API_BASE}/api/integrations/${provider}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (provider === "gmail") setGmailConnected(false);
    if (provider === "slack") setSlackConnected(false);
    setMessage(`${PROVIDER_LABEL[provider]}連携を解除しました。`);
  }

  return (
    <div className="space-y-6">
      <SectionHeader title="設定" subtitle="外部サービス連携を管理します。" />

      {message && (
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-ink">
          {message}
        </div>
      )}

      <IntegrationCard
        provider="gmail"
        connected={gmailConnected}
        onConnect={() => {
          window.location.href = `${API_BASE}/api/integrations/gmail/connect`;
        }}
        onDisconnect={() => handleDisconnect("gmail")}
      />

      <IntegrationCard
        provider="slack"
        connected={slackConnected}
        onConnect={() => {
          window.location.href = `${API_BASE}/api/integrations/slack/connect`;
        }}
        onDisconnect={() => handleDisconnect("slack")}
      />
    </div>
  );
}
