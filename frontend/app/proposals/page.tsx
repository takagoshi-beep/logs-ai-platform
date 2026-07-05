"use client";

import { useState } from "react";
import { Button, Card, SectionHeader } from "@/components/design-system";
import { pastProposals } from "@/lib/mock-data";
import { draftProposal, getProposalImageUrl } from "@/lib/api-client";

const suggestions = [
  "BEAMS向けOEM提案書を作りたい",
  "社内会議用の売上報告資料を作りたい",
  "GOLDWIN向け企画書を作りたい",
  "既存資料をもとに提案書を作り直したい",
];

interface ProposalResult {
  draft_text: string;
  internal_history_used: string;
  external_sources: string[];
  image_path: string | null;
  trace_id: string;
  governance_approval_id: string;
  status: string;
  note: string;
}

export default function ProposalBuilderPage() {
  const [customer, setCustomer] = useState("");
  const [input, setInput] = useState("");
  const [includeExternal, setIncludeExternal] = useState(false);
  const [includeImage, setIncludeImage] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ProposalResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!customer.trim() || !input.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await draftProposal(customer, input, includeExternal, includeImage);
      if (response.success === false) {
        throw new Error(response.error || "資料の生成に失敗しました");
      }
      setResult(response as ProposalResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "資料の生成に失敗しました");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">何を作りたいですか？</h1>
      </header>

      <Card>
        <label className="text-xs font-medium text-sub">顧客名</label>
        <input
          value={customer}
          onChange={(e) => setCustomer(e.target.value)}
          placeholder="例: US_LOGS Inc."
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />

        <label className="mt-4 block text-xs font-medium text-sub">提案の目的</label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="例: BEAMS向けOEM提案資料"
          rows={4}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => setInput(s)}
              className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-ink hover:bg-slate-50"
            >
              {s}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-4 text-sm text-ink">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={includeExternal}
              onChange={(e) => setIncludeExternal(e.target.checked)}
            />
            外部調査（Web検索）も行う
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={includeImage}
              onChange={(e) => setIncludeImage(e.target.checked)}
            />
            イメージ画像も生成する
          </label>
        </div>

        <div className="mt-4">
          <Button onClick={handleSubmit} className={isLoading ? "opacity-60" : ""}>
            {isLoading ? "作成中..." : "AIで資料作成"}
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
            <SectionHeader title="ドラフト" />
            <p className="mt-2 text-xs font-medium text-amber-700">
              状態: {result.status}（{result.note}）
            </p>
            <p className="mt-3 whitespace-pre-wrap text-sm text-ink">{result.draft_text}</p>
          </Card>

          {result.image_path && (
            <Card>
              <SectionHeader title="生成された画像" />
              <img
                src={getProposalImageUrl(result.trace_id)}
                alt="生成されたイメージ画像"
                className="mt-3 max-w-md rounded border border-slate-200"
              />
            </Card>
          )}

          {result.external_sources.length > 0 && (
            <Card>
              <SectionHeader title="外部調査の出典" />
              <ul className="mt-3 space-y-1">
                {result.external_sources.map((url, idx) => (
                  <li key={idx} className="text-xs text-sub">
                    <a href={url} target="_blank" rel="noreferrer" className="text-teal-700 underline">
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card>
            <SectionHeader title="参照した社内履歴" />
            <p className="mt-3 whitespace-pre-wrap text-sm text-ink">{result.internal_history_used}</p>
          </Card>
        </>
      )}

      <Card>
        <p className="text-sm font-semibold text-ink">過去に作成した資料</p>
        <ul className="mt-3 space-y-2">
          {pastProposals.map((doc) => (
            <li key={doc.id} className="surface-soft flex flex-wrap items-center justify-between gap-2 p-3">
              <div>
                <p className="text-sm font-medium text-ink">{doc.title}</p>
                <p className="text-xs text-sub">{doc.date}</p>
              </div>
              <div className="flex gap-2">
                <Button tone="ghost" size="sm">
                  ダウンロード
                </Button>
                <Button tone="ghost" size="sm">
                  複製して編集
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
