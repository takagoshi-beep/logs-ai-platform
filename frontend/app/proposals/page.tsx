"use client";

import { useEffect, useState } from "react";
import { Button, Card, SectionHeader } from "@/components/design-system";
import { pastProposals } from "@/lib/mock-data";
import {
  draftProposal,
  uploadDocumentFormat,
  listDocumentFormats,
  generateDocument,
  getGeneratedDocumentUrl,
} from "@/lib/api-client";

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
  trace_id: string;
  governance_approval_id: string;
  status: string;
  note: string;
}

interface FieldMapping {
  field_name: string;
  input_cell: string;
  confidence: number;
}

interface DocumentFormat {
  format_id: string;
  name: string;
  status: string;
  approver_id: string | null;
  approval_reason: string | null;
  field_mappings: FieldMapping[];
}

interface GenerateResult {
  output_id: string;
  filled_fields: string[];
  missing_fields: string[];
}

function statusLabel(status: string) {
  if (status === "APPROVED") return "承認済み（利用可能）";
  if (status === "QUEUED_FOR_REVIEW") return "承認待ち";
  if (status === "REJECTED") return "却下";
  return status;
}

export default function ProposalBuilderPage() {
  // --- 提案書ドラフト（既存） ---
  const [customer, setCustomer] = useState("");
  const [input, setInput] = useState("");
  const [includeExternal, setIncludeExternal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ProposalResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!customer.trim() || !input.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await draftProposal(customer, input, includeExternal, false);
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

  // --- 帳票フォーマット（新規） ---
  const [formats, setFormats] = useState<DocumentFormat[]>([]);
  const [formatsLoading, setFormatsLoading] = useState(false);

  const [formatName, setFormatName] = useState("");
  const [formatFile, setFormatFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const [selectedFormatId, setSelectedFormatId] = useState<string | null>(null);
  const [genProjectId, setGenProjectId] = useState("");
  const [genUserDataText, setGenUserDataText] = useState("{}");
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [genResult, setGenResult] = useState<GenerateResult | null>(null);

  async function refreshFormats() {
    setFormatsLoading(true);
    try {
      const response = await listDocumentFormats();
      if (response.success !== false) {
        setFormats(response.items || []);
      }
    } finally {
      setFormatsLoading(false);
    }
  }

  useEffect(() => {
    refreshFormats();
  }, []);

  async function handleUploadFormat() {
    if (!formatName.trim() || !formatFile || uploadLoading) return;
    setUploadLoading(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      const response = await uploadDocumentFormat(formatName, formatFile);
      if (response.success === false) {
        throw new Error(response.error || "アップロードに失敗しました");
      }
      setUploadSuccess(
        `アップロードが完了しました。${response.field_mappings?.length ?? 0}個のフィールドを検出しました。下の「登録済みフォーマット一覧」に追加されています。Governanceでの承認をお待ちください。`
      );
      setFormatName("");
      setFormatFile(null);
      setFileInputKey((k) => k + 1);
      await refreshFormats();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "アップロードに失敗しました");
    } finally {
      setUploadLoading(false);
    }
  }

  async function handleGenerate(formatId: string) {
    if (genLoading) return;
    setGenLoading(true);
    setGenError(null);
    setGenResult(null);
    try {
      let userData: Record<string, any> = {};
      try {
        userData = JSON.parse(genUserDataText || "{}");
      } catch {
        throw new Error('追加データはJSON形式で入力してください（例: {"担当者": "高越"}）');
      }
      const response = await generateDocument(formatId, genProjectId, userData);
      if (response.success === false) {
        throw new Error(response.error || "生成に失敗しました");
      }
      setGenResult(response as GenerateResult);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "生成に失敗しました");
    } finally {
      setGenLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">何を作りたいですか？</h1>
      </header>

      <Card>
        <SectionHeader title="提案書ドラフト（AI生成）" />
        <label className="mt-3 block text-xs font-medium text-sub">顧客名</label>
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
        </div>
        <p className="mt-2 text-xs text-sub">
          ※ 画像生成機能は現在提供していません。画像が必要な場合は、各自の生成AIツールをご利用ください。
        </p>

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
        <SectionHeader title="帳票フォーマット" />
        <p className="mt-2 text-xs text-sub">
          納品書などのテンプレートファイルをアップロードすると、AIが構造を推測します。
          内容を確認・承認（Governance）した後、実データを流し込んで帳票を自動生成できます。
          現在対応しているのはExcel（.xlsx / .xlsm）のみです。
        </p>

        <label className="mt-4 block text-xs font-medium text-sub">フォーマット名</label>
        <input
          value={formatName}
          onChange={(e) => setFormatName(e.target.value)}
          placeholder="例: フォーマットA（納品書）"
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />

        <label className="mt-4 block text-xs font-medium text-sub">テンプレートファイル</label>
        <input
          key={fileInputKey}
          type="file"
          onChange={(e) => setFormatFile(e.target.files?.[0] || null)}
          className="mt-1 w-full text-sm"
        />

        <div className="mt-4">
          <Button onClick={handleUploadFormat} className={uploadLoading ? "opacity-60" : ""}>
            {uploadLoading ? "アップロード中..." : "アップロードして構造を解析"}
          </Button>
        </div>

        {uploadError && <p className="mt-3 text-sm text-red-700">{uploadError}</p>}
        {uploadSuccess && (
          <p className="mt-3 rounded bg-teal-50 p-2 text-sm text-teal-800">{uploadSuccess}</p>
        )}
      </Card>

      <Card>
        <SectionHeader title="登録済みフォーマット一覧" />
        {formatsLoading && <p className="mt-3 text-sm text-sub">読み込み中...</p>}
        {!formatsLoading && formats.length === 0 && (
          <p className="mt-3 text-sm text-sub">まだフォーマットが登録されていません。</p>
        )}
        <ul className="mt-3 space-y-2">
          {formats.map((fmt) => (
            <li key={fmt.format_id} className="surface-soft p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-ink">{fmt.name}</p>
                  <p className="text-xs text-sub">
                    {statusLabel(fmt.status)} / 検出フィールド数: {fmt.field_mappings?.length ?? 0}
                    {fmt.approver_id ? ` / 承認者: ${fmt.approver_id}` : ""}
                  </p>
                </div>
                {fmt.status === "APPROVED" && (
                  <Button
                    tone="ghost"
                    size="sm"
                    onClick={() =>
                      setSelectedFormatId(selectedFormatId === fmt.format_id ? null : fmt.format_id)
                    }
                  >
                    {selectedFormatId === fmt.format_id ? "閉じる" : "このフォーマットで生成"}
                  </Button>
                )}
                {fmt.status === "QUEUED_FOR_REVIEW" && (
                  <span className="text-xs text-amber-700">
                    Governanceでの承認待ちです（/governance/queue から承認してください）
                  </span>
                )}
              </div>

              {selectedFormatId === fmt.format_id && (
                <div className="mt-3 border-t border-slate-200 pt-3">
                  <label className="block text-xs font-medium text-sub">
                    案件ID（任意・実案件データを自動反映します）
                  </label>
                  <input
                    value={genProjectId}
                    onChange={(e) => setGenProjectId(e.target.value)}
                    placeholder="例: 7722"
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />

                  <label className="mt-3 block text-xs font-medium text-sub">
                    追加データ（JSON形式。案件データより優先されます）
                  </label>
                  <textarea
                    value={genUserDataText}
                    onChange={(e) => setGenUserDataText(e.target.value)}
                    rows={3}
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-xs"
                  />

                  <div className="mt-3">
                    <Button
                      onClick={() => handleGenerate(fmt.format_id)}
                      className={genLoading ? "opacity-60" : ""}
                    >
                      {genLoading ? "生成中..." : "生成する"}
                    </Button>
                  </div>

                  {genError && <p className="mt-3 text-sm text-red-700">{genError}</p>}

                  {genResult && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs text-ink">
                        埋めたフィールド: {genResult.filled_fields.join("、") || "なし"}
                      </p>
                      <p className="text-xs text-amber-700">
                        情報が不足しているフィールド: {genResult.missing_fields.join("、") || "なし"}
                      </p>
                      <a
                        href={getGeneratedDocumentUrl(genResult.output_id)}
                        className="inline-block rounded bg-teal-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-800"
                      >
                        生成された帳票をダウンロード
                      </a>
                    </div>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
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
