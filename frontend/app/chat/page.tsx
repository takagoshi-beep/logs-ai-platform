"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Button, Card } from "@/components/design-system";
import { consultQuestion } from "@/lib/api-client";

interface ToolCall {
  tool: string;
  input: Record<string, unknown>;
}

// 2026-07-10（14.64、Noritsuguの指定）: 相談機能でClaudeが返すMarkdown
// テーブル（輸入経費推定等）が、これまで単純な<p>にプレーンテキストと
// して表示されていて「|」区切りのまま見づらかった。react-markdownで
// 実際に表・見出し・強調として描画するようにした。
const markdownComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mt-1 text-sm text-ink">{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-ink">{children}</strong>
  ),
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="mt-3 text-base font-bold text-ink">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="mt-3 text-sm font-bold text-ink">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="mt-2 text-sm font-semibold text-ink">{children}</h3>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-ink">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-sm text-ink">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => <li>{children}</li>,
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">{children}</code>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="mt-2 overflow-x-auto">
      <table className="min-w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => (
    <thead className="bg-slate-100">{children}</thead>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border border-slate-200 px-2 py-1 text-left font-semibold text-ink">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border border-slate-200 px-2 py-1 align-top text-ink">{children}</td>
  ),
};

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!input.trim() || isLoading) return;
    const question = input;
    setInput("");
    setIsLoading(true);
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);

    try {
      const response = await consultQuestion(question, sessionId);
      if (response.success === false) {
        throw new Error(response.error || "回答の取得に失敗しました");
      }
      setSessionId(response.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, toolCalls: response.tool_calls || [] },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "回答の取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  }

  function handleNewConversation() {
    setMessages([]);
    setSessionId(undefined);
    setError(null);
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">何でも相談してください</h1>
            <p className="page-subtitle">
              AIが実データ（Supabase）を自分で調べながら回答します。会話の続きとして質問できます。
            </p>
          </div>
          {messages.length > 0 && (
            <Button tone="ghost" size="sm" onClick={handleNewConversation}>
              新しい会話を始める
            </Button>
          )}
        </div>
      </header>

      <Card>
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-sm text-sub">
              <p className="font-medium text-ink">こんなことが調べられます:</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>売上・粗利(顧客別、商品分類別、事業分類別、期間別)</li>
                <li>仕入・原価(輸入コスト、諸掛の内訳)</li>
                <li>案件(PO)の状況・納期・担当者</li>
                <li>商品情報、商品ごとの発注・仕入・売上履歴</li>
                <li>予算・売上予定(担当者別、期間別)</li>
                <li>サンプル対応状況(担当者別、到着予定日)</li>
                <li>顧客担当者の連絡先</li>
                <li>Gmail・Slackの検索(連携している場合)</li>
              </ul>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={msg.role === "user" ? "ml-auto max-w-[80%] rounded-lg bg-accent/10 p-3" : "mr-auto max-w-[80%] rounded-lg bg-slate-50 p-3"}
            >
              <p className="text-xs font-semibold text-sub">{msg.role === "user" ? "あなた" : "AI"}</p>
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={markdownComponents}>
                {msg.content}
              </ReactMarkdown>
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <p className="mt-2 text-xs text-sub">
                  使用したツール: {msg.toolCalls.map((t) => t.tool).join("、")}
                </p>
              )}
            </div>
          ))}
          {isLoading && <p className="text-sm text-sub">回答を生成中...</p>}
        </div>

        <div className="mt-4 border-t border-slate-200 pt-4">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="質問を入力してください"
            rows={3}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="mt-3">
            <Button onClick={handleSubmit} className={isLoading ? "opacity-60" : ""}>
              {isLoading ? "回答を生成中..." : "送信"}
            </Button>
          </div>
        </div>
      </Card>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <p className="text-sm text-red-700">{error}</p>
        </Card>
      )}
    </div>
  );
}
