"use client";

import { useState } from "react";
import { Button, Card } from "@/components/design-system";
import { pastProposals } from "@/lib/mock-data";

const suggestions = [
  "BEAMS向けOEM提案書を作りたい",
  "社内会議用の売上報告資料を作りたい",
  "GOLDWIN向け企画書を作りたい",
  "既存資料をもとに提案書を作り直したい",
];

export default function ProposalBuilderPage() {
  const [input, setInput] = useState("");

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">何を作りたいですか？</h1>
      </header>

      <Card>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="例: BEAMS向けOEM提案資料"
          rows={4}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
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
        <div className="mt-4">
          <Button>AIで資料作成</Button>
        </div>
      </Card>

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
