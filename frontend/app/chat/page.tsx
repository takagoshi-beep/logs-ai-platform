"use client";

import { useState } from "react";
import { Button, Card } from "@/components/design-system";
import { consultQuestion } from "@/lib/api-client";

interface ToolCall {
  tool: string;
  input: Record<string, unknown>;
}

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
            <p className="text-sm text-sub">
              例: 「今月のOEM事業の粗利を教えて」「林さんが対応中のサンプルは？」
            </p>
          )}
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={msg.role === "user" ? "ml-auto max-w-[80%] rounded-lg bg-accent/10 p-3" : "mr-auto max-w-[80%] rounded-lg bg-slate-50 p-3"}
            >
              <p className="text-xs font-semibold text-sub">{msg.role === "user" ? "あなた" : "AI"}</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{msg.content}</p>
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
            placeholder="例: Fanaticsの納期リスクについて次の対応を相談したい"
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
