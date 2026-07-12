"use client";

import { Card, SectionHeader, Button, Badge } from "@/components/design-system";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getEvaluationSummary } from "@/lib/api-client";

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

interface CapabilityMetric {
  capability_id: string;
  total_executions: number;
  successful_executions?: number;
  success_rate: number;
  avg_execution_time_seconds: number;
  confidence?: number;
  last_used_at?: string | null;
}

interface EvaluationSummary {
  overall_success_rate: number | null;
  total_executions: number;
  capabilities: CapabilityMetric[];
}

function fmtPercent(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(0)}%`;
}

// 2026-07-14（14.101、Noritsuguの指定）: GET /api/evaluation/summaryは
// 実装済みで実際の実行成功率を集計しているが、これまでどのページからも
// 呼ばれておらず未接続だった。設定ページに「AIパフォーマンス」として
// 追加し、ログズ社内で継続的に相談・推論エンジンの挙動をチェックする
// 際の簡易的な健康診断として使えるようにする。
function AiPerformanceSection() {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEvaluationSummary()
      .then((data: any) => setSummary(data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Card>
      <SectionHeader
        title="AIパフォーマンス"
        subtitle="登録済みの各AI機能（Capability）の実行成功率です。ハードコードではなく実際の実行履歴から集計しています。"
      />
      {loading && <p className="py-4 text-center text-sm text-sub">読み込み中...</p>}
      {!loading && summary && summary.total_executions === 0 && (
        <p className="py-4 text-center text-sm text-sub">まだ実行記録がありません</p>
      )}
      {!loading && summary && summary.total_executions > 0 && (
        <>
          <div className="mt-2 flex gap-6 text-sm">
            <div>
              <div className="text-xs text-sub">全体の成功率</div>
              <div className="text-lg font-semibold text-ink">{fmtPercent(summary.overall_success_rate)}</div>
            </div>
            <div>
              <div className="text-xs text-sub">総実行回数</div>
              <div className="text-lg font-semibold text-ink">{summary.total_executions.toLocaleString()}</div>
            </div>
          </div>
          <div className="mt-3 space-y-2">
            {summary.capabilities.map((cap) => (
              <div key={cap.capability_id} className="surface-soft flex items-center justify-between p-2 text-xs">
                <span className="font-medium text-ink">{cap.capability_id}</span>
                <span className="text-sub">
                  成功率 {fmtPercent(cap.success_rate)} ・ {cap.total_executions}回実行 ・ 平均{cap.avg_execution_time_seconds.toFixed(1)}秒
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}

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

      <AiPerformanceSection />
    </div>
  );
}
