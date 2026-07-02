"use client";

import { useState } from "react";
import { Button, Card, SectionHeader } from "@/components/design-system";
import { runReasoning } from "@/lib/api-client";

const SAMPLE_QUESTIONS = [
  "今月のOEM事業の粗利を教えて",
  "Fanatics案件の状況を教えて",
  "今日優先すべき案件は？",
  "今月売上が一番大きい顧客は？",
];

interface ConfidentStatement {
  statement: string;
  confidence: number;
}

interface KnowledgeItem {
  conclusion: string;
  rule_id: string;
  insight: string;
  kr_id?: string | null;
  name?: string;
  source?: string | null;
}

interface RequiredDataItem {
  priority: number;
  item: string;
  provider?: string;
  dataset?: string;
}

interface EvidenceSource {
  priority: number | null;
  item: string | null;
  fetched_at: string | null;
}

interface EvidenceItem {
  priority: number | null;
  items: string[];
  provider: string;
  dataset: string;
  status: string;
  facts: string[];
  summary: string;
  record_count: number;
  display_records: Record<string, string | number | null>[];
  sample_note: string | null;
  duplicate_removed: number;
  note: string | null;
  sources: EvidenceSource[];
  integrated_at: string;
}

interface PlanStep {
  stage: string;
  action: string;
}

interface DecisionGate {
  verdict: string;
  reason: string;
  proceed_conditions: string[];
  confidence: number;
}

interface FactLayer {
  layer: string;
  timestamp: string;
  provider: string;
  source_table: string;
  query_conditions: Record<string, string>;
  rows_retrieved: number;
  data: Record<string, number | null>;
  data_quality: {
    completeness: string;
    null_count: number;
    estimated_accuracy: number;
  };
  error?: string;
}

interface InterpretationLayer {
  layer: string;
  observations: string[];
  status?: string;
  observation?: string;
}

interface HypothesisItem {
  layer: string;
  id: string;
  statement: string;
  confidence: number;
  reasoning: string[];
  affects_knowledge: boolean;
  knowledge_concept: string;
}

interface KnowledgeCandidateItem {
  layer: string;
  concept: string;
  ai_hypothesis: string;
  confidence: number;
  reasoning: string[];
  hypothesis_id: string;
  po_review_status: string;
  ready_for_knowledge_update: boolean;
  note: string;
}

interface Phase13Layer {
  facts: FactLayer;
  interpretation: InterpretationLayer;
  ai_hypotheses: HypothesisItem[];
  knowledge_candidates: KnowledgeCandidateItem[];
  compliance_note: string;
}

interface ReasoningResult {
  question: string;
  intent: { type: string; category: string; confidence: number };
  meaning: { confidence: number; items: Record<string, string | string[]> };
  hypothesis: ConfidentStatement[];
  knowledge_used: KnowledgeItem[];
  decision_gate: DecisionGate;
  required_data: RequiredDataItem[];
  unknown: string[];
  assumption: ConfidentStatement[];
  plan: PlanStep[];
  evidence: EvidenceItem[];
  phase_13?: Phase13Layer;
}

function formatValue(value: string | string[]): string {
  return Array.isArray(value) ? value.join(" / ") : value;
}

function ConfidenceBadge({ value }: { value: number }) {
  return (
    <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-sub">
      confidence {value}
    </span>
  );
}

const PROVIDER_LABELS: Record<string, string> = {
  logsys: "Logsys",
  gmail: "Gmail",
  project_sheet: "案件管理シート",
  slack: "Slack",
};

function providerLabel(provider?: string): string {
  return provider ? PROVIDER_LABELS[provider] || provider : "";
}

function verdictStyle(verdict: string): string {
  if (verdict.includes("注意事項")) return "bg-sky-50 text-sky-700 border-sky-200";
  if (verdict.includes("回答可能")) return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (verdict.includes("追加確認")) return "bg-amber-50 text-amber-700 border-amber-200";
  if (verdict.includes("判断保留")) return "bg-orange-50 text-orange-700 border-orange-200";
  return "bg-red-50 text-red-700 border-red-200";
}

export default function ReasoningPage() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ReasoningResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(question: string) {
    if (!question.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await runReasoning(question);
      if (response.success === false) {
        throw new Error(response.error || "推論結果の取得に失敗しました");
      }
      setResult({
        question: response.question,
        intent: response.intent,
        meaning: response.meaning || { confidence: 0, items: {} },
        hypothesis: response.hypothesis || [],
        knowledge_used: response.knowledge_used || [],
        decision_gate: response.decision_gate,
        required_data: response.required_data || [],
        unknown: response.unknown || [],
        assumption: response.assumption || [],
        plan: response.plan || [],
        evidence: response.evidence || [],
        phase_13: response.phase_13,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "推論結果の取得に失敗しました");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">Reasoning Pipeline + Execution + Integration + Interpretation Layer v0.1</h1>
        <p className="mt-1 text-sm text-sub">
          LOGS社員の判断プロセスをAIの思考として再現し、Required DataをData Provider経由で実際に取得したうえで、
          Evidence Integration Layerが重複排除・時系列整理・優先度整理を行い、
          Evidence Interpretation Layerが事実(Facts)を抽出します。
          質問→Intent→Meaning→Hypothesis→Knowledge→Decision Gate→Required Data→Unknown→Assumption→Plan→Evidence Interpretation。
        </p>
      </header>

      <Card>
        <div className="mb-3 flex flex-wrap gap-2">
          {SAMPLE_QUESTIONS.map((q) => (
            <Button key={q} tone="ghost" size="sm" onClick={() => setInput(q)}>
              {q}
            </Button>
          ))}
        </div>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="例: 今月のOEM事業の粗利を教えて"
          rows={3}
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="mt-3">
          <Button onClick={() => submit(input)} className={isLoading ? "opacity-60" : ""}>
            {isLoading ? "推論中..." : "送信"}
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
            <SectionHeader title="1. Intent（質問の種類）" />
            <p className="mt-3 text-sm text-ink">
              {result.intent.type}
              <span className="ml-2 text-xs text-sub">({result.intent.category})</span>
              <ConfidenceBadge value={result.intent.confidence} />
            </p>
          </Card>

          <Card>
            <SectionHeader title="2. Meaning（質問の解釈）" />
            <div className="mt-2 text-xs text-sub">
              解釈全体の確信度
              <ConfidenceBadge value={result.meaning.confidence} />
            </div>
            <ul className="mt-3 space-y-2">
              {Object.keys(result.meaning.items).length === 0 && (
                <li className="text-sm text-sub">解釈できませんでした</li>
              )}
              {Object.entries(result.meaning.items).map(([key, value]) => (
                <li key={key} className="surface-soft flex items-center justify-between gap-4 p-3">
                  <span className="shrink-0 text-xs text-sub">{key}</span>
                  <span className="text-right text-sm text-ink">{formatValue(value)}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionHeader title="3. Hypothesis（もし○○なら、の条件付き仮説）" />
            <ol className="mt-3 list-decimal space-y-2 pl-5">
              {result.hypothesis.length === 0 && <li className="text-sm text-sub">仮説はありません</li>}
              {result.hypothesis.map((h, idx) => (
                <li key={idx} className="text-sm text-ink">
                  {h.statement}
                  <ConfidenceBadge value={h.confidence} />
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <SectionHeader title="4. Knowledge Used（推論から導いたこと ← 使った業務知識）" />
            <ul className="mt-3 space-y-3">
              {result.knowledge_used.length === 0 && (
                <li className="text-sm text-sub">適用したKnowledgeはありません</li>
              )}
              {result.knowledge_used.map((k, idx) => (
                <li key={idx} className="surface-soft p-3">
                  <p className="text-sm font-medium text-ink">{k.conclusion}</p>
                  <p className="mt-1 text-sm text-sub">↑ {k.insight}</p>
                  <p className="mt-1 text-xs text-sub">
                    参照ルール: {k.rule_id}
                    {k.kr_id ? ` ｜ Registry: ${k.kr_id}` : " ｜ Registry未登録"}
                    {k.source ? ` ｜ 出典: knowledge/${k.source}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          </Card>

          {result.decision_gate && (
            <Card>
              <SectionHeader title="5. Decision Gate（今の情報で進めてよいか — 5段階判定）" />
              <div className="mt-3 space-y-3">
                <div>
                  <span
                    className={`inline-block rounded border px-2 py-1 text-sm font-medium ${verdictStyle(result.decision_gate.verdict)}`}
                  >
                    判定: {result.decision_gate.verdict}
                  </span>
                  <ConfidenceBadge value={result.decision_gate.confidence} />
                </div>
                <div className="surface-soft p-3">
                  <p className="text-xs text-sub">理由</p>
                  <p className="mt-1 text-sm text-ink">{result.decision_gate.reason}</p>
                </div>
                <div className="surface-soft p-3">
                  <p className="text-xs text-sub">進行条件</p>
                  <ul className="mt-1 space-y-1">
                    {result.decision_gate.proceed_conditions.map((c, idx) => (
                      <li key={idx} className="text-sm text-ink">
                        ・{c}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>
          )}

          <Card>
            <SectionHeader title="6. Required Data（取得すれば分かる情報 — 取得優先度つき）" />
            <ul className="mt-3 space-y-2">
              {result.required_data.length === 0 && (
                <li className="text-sm text-sub">必要データはありません</li>
              )}
              {result.required_data.map((d) => (
                <li key={d.priority} className="surface-soft flex items-center gap-3 p-3">
                  <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-sub">
                    Priority {d.priority}
                  </span>
                  <span className="text-sm text-ink">{d.item}</span>
                  {d.provider && (
                    <span className="ml-auto shrink-0 rounded border border-slate-200 px-1.5 py-0.5 text-xs text-sub">
                      {providerLabel(d.provider)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionHeader title="7. Unknown（取得しても分からない、会社として未決定なこと）" />
            <ul className="mt-3 space-y-2">
              {result.unknown.length === 0 && <li className="text-sm text-sub">不明点なし</li>}
              {result.unknown.map((u, idx) => (
                <li key={idx} className="surface-soft p-3 text-sm text-ink">
                  ⚠ {u}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionHeader title="8. Assumption（今回は一旦こう仮定して進めること）" />
            <ul className="mt-3 space-y-2">
              {result.assumption.length === 0 && <li className="text-sm text-sub">仮置きはありません</li>}
              {result.assumption.map((a, idx) => (
                <li key={idx} className="surface-soft p-3 text-sm text-ink">
                  {a.statement}
                  <ConfidenceBadge value={a.confidence} />
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionHeader title="9. Plan（LOGS社員の業務フロー: 情報取得→判断→回答案生成→Decision Gate→回答）" />
            <ol className="mt-3 space-y-2">
              {result.plan.length === 0 && <li className="text-sm text-sub">次のアクションはありません</li>}
              {result.plan.map((p, idx) => (
                <li key={idx} className="surface-soft flex items-center gap-3 p-3">
                  <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-sub">
                    {idx + 1}. {p.stage}
                  </span>
                  <span className="text-sm text-ink">{p.action}</span>
                </li>
              ))}
            </ol>
          </Card>

          <Card>
            <SectionHeader title="10. Evidence Interpretation（AIが理解したこと）" />
            <ul className="mt-3 space-y-3">
              {result.evidence.length === 0 && (
                <li className="text-sm text-sub">解釈されたデータはありません</li>
              )}
              {result.evidence.map((e, idx) => (
                <li key={idx} className="surface-soft p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-sub">
                      Priority {e.priority}
                    </span>
                    <span className="text-sm font-medium text-ink">{e.items.join(" / ")}</span>
                    <span
                      className={`ml-auto rounded border px-1.5 py-0.5 text-xs ${
                        e.status === "ok"
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : "border-red-200 bg-red-50 text-red-700"
                      }`}
                    >
                      {e.status === "ok" ? "取得成功" : "取得不可"}
                    </span>
                    <span className="rounded border border-slate-200 px-1.5 py-0.5 text-xs text-sub">
                      {providerLabel(e.provider)}
                    </span>
                  </div>
                  <div className="mt-2">
                    <p className="text-xs font-medium text-sub">AIが理解したこと</p>
                    <ul className="mt-1 space-y-1">
                      {e.facts.map((fact, fIdx) => (
                        <li key={fIdx} className="text-sm text-ink">
                          ・{fact}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs text-sub">▼詳細データ（全{e.record_count}件）</summary>
                    <div className="mt-2 space-y-2">
                      <p className="text-xs text-sub">{e.summary}</p>
                      {e.display_records.length > 0 && (
                        <ul className="space-y-1">
                          {e.display_records.map((r, rIdx) => (
                            <li key={rIdx} className="rounded bg-white px-2 py-1 text-xs text-sub">
                              {Object.entries(r)
                                .map(([k, v]) => `${k}: ${v ?? "-"}`)
                                .join(" ／ ")}
                            </li>
                          ))}
                        </ul>
                      )}
                      {e.sample_note && <p className="text-xs italic text-sub">※ {e.sample_note}</p>}
                      <p className="text-xs text-sub">
                        統合元: {e.sources.length}件のRequired Data
                        {e.duplicate_removed > 0 ? ` ｜ 重複除去 ${e.duplicate_removed}件` : ""}
                      </p>
                      {e.note && <p className="text-xs text-sub">※ {e.note}</p>}
                    </div>
                  </details>
                </li>
              ))}
            </ul>
          </Card>

          {result.phase_13 && (
            <>
              <Card className="border-l-4 border-l-blue-500">
                <SectionHeader title="Phase 13: 4-Layer Fact Extraction (Real DB Integration)" />
                <p className="mt-2 text-xs text-sub">{result.phase_13.compliance_note}</p>
              </Card>

              {result.phase_13.facts && (
                <Card>
                  <SectionHeader title="Layer 1: FACT（DBから取得した客観事実）" />
                  <div className="mt-3 space-y-3">
                    <div className="rounded bg-blue-50 p-3">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <p className="font-medium text-blue-900">Provider</p>
                          <p className="text-blue-700">{result.phase_13.facts.provider}</p>
                        </div>
                        <div>
                          <p className="font-medium text-blue-900">Source Table</p>
                          <p className="text-blue-700">{result.phase_13.facts.source_table}</p>
                        </div>
                        <div>
                          <p className="font-medium text-blue-900">Rows Retrieved</p>
                          <p className="text-blue-700">{result.phase_13.facts.rows_retrieved}</p>
                        </div>
                        <div>
                          <p className="font-medium text-blue-900">Timestamp</p>
                          <p className="text-blue-700 text-xs">{new Date(result.phase_13.facts.timestamp).toLocaleString("ja-JP")}</p>
                        </div>
                      </div>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-sub">Query Conditions</p>
                      <div className="mt-2 rounded bg-slate-50 p-2 text-xs text-ink">
                        <pre className="overflow-auto whitespace-pre-wrap font-mono text-xs">
                          WHERE {Object.entries(result.phase_13.facts.query_conditions)
                            .map(([k, v]) => `${k} = ${v}`)
                            .join(" AND ")}
                        </pre>
                      </div>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-sub">Raw Data</p>
                      <div className="mt-2 space-y-1">
                        {Object.entries(result.phase_13.facts.data).map(([key, value]) => (
                          <div key={key} className="flex justify-between rounded bg-slate-50 px-2 py-1 text-xs">
                            <span className="font-medium text-sub">{key}</span>
                            <span className="text-ink">{value !== null ? value.toLocaleString("ja-JP") : "NULL"}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="text-xs font-medium text-sub">Data Quality</p>
                      <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                        <div className="rounded bg-slate-50 p-2">
                          <p className="text-sub">Completeness</p>
                          <p className="font-medium text-ink">{result.phase_13.facts.data_quality.completeness}</p>
                        </div>
                        <div className="rounded bg-slate-50 p-2">
                          <p className="text-sub">Null Count</p>
                          <p className="font-medium text-ink">{result.phase_13.facts.data_quality.null_count}</p>
                        </div>
                        <div className="rounded bg-slate-50 p-2">
                          <p className="text-sub">Accuracy</p>
                          <p className="font-medium text-ink">{(result.phase_13.facts.data_quality.estimated_accuracy * 100).toFixed(0)}%</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              )}

              {result.phase_13.interpretation && (
                <Card>
                  <SectionHeader title="Layer 2: INTERPRETATION（AIが読み取った意味）" />
                  <div className="mt-3 space-y-2">
                    {result.phase_13.interpretation.observations.map((obs, idx) => (
                      <div key={idx} className="rounded bg-amber-50 border border-amber-200 p-3">
                        <p className="text-sm text-ink">・{obs}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {result.phase_13.ai_hypotheses && result.phase_13.ai_hypotheses.length > 0 && (
                <Card>
                  <SectionHeader title="Layer 3: HYPOTHESIS（AI推定 — Interpretationから導いた仮説）" />
                  <div className="mt-3 space-y-3">
                    {result.phase_13.ai_hypotheses.map((hyp, idx) => (
                      <div key={idx} className="rounded bg-purple-50 border border-purple-200 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <p className="text-sm font-medium text-ink">{hyp.statement}</p>
                            <div className="mt-2 space-y-1">
                              <p className="text-xs font-medium text-sub">Reasoning:</p>
                              {hyp.reasoning.map((r, rIdx) => (
                                <p key={rIdx} className="text-xs text-sub">
                                  ・{r}
                                </p>
                              ))}
                            </div>
                            <p className="mt-2 text-xs text-sub">Affects Knowledge: <span className="font-medium">{hyp.knowledge_concept}</span></p>
                          </div>
                          <div className="shrink-0 rounded bg-purple-100 px-2 py-1 text-xs font-medium text-purple-900">
                            {hyp.id} {(hyp.confidence * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {result.phase_13.knowledge_candidates && result.phase_13.knowledge_candidates.length > 0 && (
                <Card>
                  <SectionHeader title="Layer 4: KNOWLEDGE CANDIDATE（PO確認待ち）" />
                  <div className="mt-3 space-y-3">
                    {result.phase_13.knowledge_candidates.map((cand, idx) => (
                      <div key={idx} className="rounded bg-red-50 border border-red-200 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <p className="text-sm font-medium text-ink">{cand.concept}</p>
                            <p className="mt-1 text-sm text-red-700">「{cand.ai_hypothesis}」</p>
                            <div className="mt-2 space-y-1">
                              <p className="text-xs font-medium text-sub">Reasoning:</p>
                              {cand.reasoning.map((r, rIdx) => (
                                <p key={rIdx} className="text-xs text-sub">
                                  ・{r}
                                </p>
                              ))}
                            </div>
                            <p className="mt-2 text-xs italic text-red-600">{cand.note}</p>
                          </div>
                          <div className="shrink-0 space-y-1">
                            <div className="rounded bg-red-100 px-2 py-1 text-xs font-medium text-red-900">
                              {(cand.confidence * 100).toFixed(0)}% Confidence
                            </div>
                            <div className="rounded bg-orange-100 px-2 py-1 text-xs font-medium text-orange-900">
                              {cand.po_review_status}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
