"use client";

import { useState } from "react";
import { Button, Card, SectionHeader } from "@/components/design-system";
import { pastConsultations } from "@/lib/mock-data";
import { consultQuestion } from "@/lib/api-client";

interface DataSource {
  table: string;
  record: string;
}

interface JudgmentReason {
  reason: string;
  confidence: number;
  business_rule: string;
}

interface RelatedProject {
  project_id: string;
  name: string;
  customer: string;
  status: string;
}

interface ConsultResult {
  ai_response: string;
  data_sources: DataSource[];
  judgment_reasoning: JudgmentReason[];
  related_projects: RelatedProject[];
  open_questions: string[];
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ConsultResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!input.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await consultQuestion(input);
      if (response.success === false) {
        throw new Error(response.error || "回答の取得に失敗しました");
      }
      setResult({
        ai_response: response.ai_response,
        data_sources: response.data_sources || [],
        judgment_reasoning: response.judgment_reasoning || [],
        related_projects: response.related_projects || [],
        open_questions: response.open_questions || [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "回答の取得に失敗しました");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">何でも相談してください</h1>
      </header>

      <Card>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="例: Fanaticsの納期リスクについて次の対応を相談したい"
          rows={4}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="mt-3">
          <Button onClick={handleSubmit} className={isLoading ? "opacity-60" : ""}>
            {isLoading ? "回答を生成中..." : "送信"}
          </Button>
        </div>
      </Card>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <p className="text-sm text-red-700">{error}</p>
        </Card>
      )}

      {result && (
        <>
          <Card>
            <SectionHeader title="AI回答" />
            <p className="mt-3 text-sm text-ink">{result.ai_response}</p>
          </Card>

          <Card>
            <SectionHeader title="参照した情報" />
            <ul className="mt-3 space-y-2">
              {result.data_sources.length === 0 && <li className="text-sm text-sub">参照した情報はありません</li>}
              {result.data_sources.map((ds, idx) => (
                <li key={idx} className="surface-soft flex items-center justify-between p-3">
                  <span className="text-xs text-sub">{ds.table}</span>
                  <span className="text-sm text-ink">{ds.record}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionHeader title="判断理由" />
            <ul className="mt-3 space-y-2">
              {result.judgment_reasoning.length === 0 && <li className="text-sm text-sub">判断理由はありません</li>}
              {result.judgment_reasoning.map((jr, idx) => (
                <li key={idx} className="surface-soft p-3">
                  <p className="text-sm text-ink">{jr.reason}</p>
                  <p className="mt-1 text-xs text-sub">
                    ルール: {jr.business_rule} / 確信度: {Math.round(jr.confidence * 100)}%
                  </p>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionHeader title="関連案件" />
            <ul className="mt-3 space-y-2">
              {result.related_projects.map((p) => (
                <li key={p.project_id} className="surface-soft flex items-center justify-between p-3">
                  <div>
                    <p className="text-sm font-medium text-ink">{p.name}</p>
                    <p className="text-xs text-sub">
                      {p.customer} / {p.status}
                    </p>
                  </div>
                  <Button href={`/workspace/${p.project_id}`} tone="ghost" size="sm">
                    案件を開く
                  </Button>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionHeader title="不明点・追加確認事項" />
            <ul className="mt-3 space-y-2">
              {result.open_questions.map((q, idx) => (
                <li key={idx} className="surface-soft p-3 text-sm text-ink">
                  {q}
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}

      <Card>
        <p className="text-sm font-semibold text-ink">過去の相談履歴</p>
        <ul className="mt-3 space-y-2">
          {pastConsultations.map((chat) => (
            <li key={chat.id} className="surface-soft flex items-center justify-between p-3">
              <span className="text-sm text-ink">{chat.title}</span>
              <Button tone="ghost" size="sm">
                続きを開く
              </Button>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
