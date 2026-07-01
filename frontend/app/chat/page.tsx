"use client";

import { useState } from "react";
import { Button, Card } from "@/components/design-system";
import { pastConsultations } from "@/lib/mock-data";

export default function ChatPage() {
  const [input, setInput] = useState("");

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
          <Button>送信</Button>
        </div>
      </Card>

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
