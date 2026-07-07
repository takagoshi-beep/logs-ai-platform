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
  decideGovernance,
  updateFieldMappings,
  parseInstruction,
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
  label_cell: string;
  input_cell: string;
  direction: string;
  confidence: number;
  table_id?: string;
}

interface TableColumn {
  field_name: string;
  label_cell: string;
  column_letter: string;
}

interface TableRegion {
  table_id: string;
  header_row: number;
  columns: TableColumn[];
}

interface DocumentFormat {
  format_id: string;
  name: string;
  status: string;
  approver_id: string | null;
  approval_reason: string | null;
  governance_approval_id: string;
  field_mappings: FieldMapping[];
  table_regions: TableRegion[];
}

interface GenerateResult {
  output_id: string;
  filled_fields: string[];
  missing_fields: string[];
  tables_written: Record<string, number>;
  write_errors: string[];
}

function statusLabel(status: string) {
  if (status === "APPROVED") return "承認済み（利用可能）";
  if (status === "QUEUED_FOR_REVIEW") return "承認待ち";
  if (status === "REJECTED") return "却下";
  return status;
}

function emptyTableRow(region: TableRegion): Record<string, string> {
  const row: Record<string, string> = {};
  for (const col of region.columns) {
    row[col.field_name] = "";
  }
  return row;
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

  // --- 帳票フォーマット ---
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
  const [genFieldValues, setGenFieldValues] = useState<Record<string, string>>({});
  const [genTableRows, setGenTableRows] = useState<Record<string, Array<Record<string, string>>>>({});
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [genResult, setGenResult] = useState<GenerateResult | null>(null);

  const [chatInstruction, setChatInstruction] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  // 承認待ちフォーマットの、人間による編集内容（項目名・入力先セルの修正、行の削除）
  const [editedMappings, setEditedMappings] = useState<Record<string, FieldMapping[]>>({});
  const [reviewReasons, setReviewReasons] = useState<Record<string, string>>({});
  const [reviewLoadingId, setReviewLoadingId] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  function getEditableMappings(fmt: DocumentFormat): FieldMapping[] {
    return editedMappings[fmt.format_id] ?? fmt.field_mappings ?? [];
  }

  function updateMappingField(
    fmt: DocumentFormat,
    labelCell: string,
    key: "field_name" | "input_cell",
    value: string
  ) {
    const current = getEditableMappings(fmt);
    const next = current.map((m) => (m.label_cell === labelCell ? { ...m, [key]: value } : m));
    setEditedMappings((prev) => ({ ...prev, [fmt.format_id]: next }));
  }

  function deleteMappingRow(fmt: DocumentFormat, labelCell: string) {
    const current = getEditableMappings(fmt);
    const next = current.filter((m) => m.label_cell !== labelCell);
    setEditedMappings((prev) => ({ ...prev, [fmt.format_id]: next }));
  }

  async function handleReview(fmt: DocumentFormat, decision: "APPROVED" | "REJECTED") {
    const governanceApprovalId = fmt.governance_approval_id;
    setReviewLoadingId(governanceApprovalId);
    setReviewError(null);
    try {
      if (decision === "APPROVED") {
        // 承認する前に、ユーザーが編集した項目定義（削除・名称変更・セル修正）を確定させる。
        // これが「ユーザーとAIが一緒に構造を規定する」ステップ。
        const finalMappings = getEditableMappings(fmt);
        const updateResp = await updateFieldMappings(fmt.format_id, finalMappings);
        if (updateResp.success === false) {
          throw new Error(updateResp.error || "項目定義の保存に失敗しました");
        }
      }
      const reason =
        reviewReasons[governanceApprovalId] ||
        (decision === "APPROVED" ? "内容を確認し、問題なし" : "内容を確認し、却下");
      const response = await decideGovernance(governanceApprovalId, decision, reason);
      if (response.success === false) {
        throw new Error(response.error || "承認処理に失敗しました");
      }
      await refreshFormats();
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "承認処理に失敗しました");
    } finally {
      setReviewLoadingId(null);
    }
  }

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
      const tableCount = response.table_regions?.length ?? 0;
      setUploadSuccess(
        `アップロードが完了しました。${response.field_mappings?.length ?? 0}個のフィールド` +
          (tableCount > 0 ? `（うちテーブル領域${tableCount}件）` : "") +
          "を検出しました。下の「登録済みフォーマット一覧」に追加されています。Governanceでの承認をお待ちください。"
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

  async function handleGenerate(fmt: DocumentFormat) {
    if (genLoading) return;
    setGenLoading(true);
    setGenError(null);
    setGenResult(null);
    try {
      // 空欄のフィールドはuserDataに含めない（案件IDからの自動反映が優先されるように）
      const userData: Record<string, any> = {};
      for (const [fieldName, value] of Object.entries(genFieldValues)) {
        if (value.trim() !== "") {
          userData[fieldName] = value;
        }
      }
      // テーブル行のうち、全項目が空欄の行は送らない
      const tableRows: Record<string, Array<Record<string, any>>> = {};
      for (const region of fmt.table_regions || []) {
        const rows = (genTableRows[region.table_id] || []).filter((row) =>
          Object.values(row).some((v) => v.trim() !== "")
        );
        if (rows.length > 0) {
          tableRows[region.table_id] = rows;
        }
      }
      const response = await generateDocument(fmt.format_id, genProjectId, userData, tableRows);
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

  function openGeneratePanel(fmt: DocumentFormat) {
    if (selectedFormatId === fmt.format_id) {
      setSelectedFormatId(null);
      return;
    }
    setSelectedFormatId(fmt.format_id);
    setGenProjectId("");
    setGenResult(null);
    setGenError(null);
    setChatInstruction("");
    setChatError(null);

    // 単一項目ごとに空の入力欄を用意する（テーブル列は除く）
    const initialValues: Record<string, string> = {};
    for (const mapping of fmt.field_mappings || []) {
      if (!mapping.table_id) {
        initialValues[mapping.field_name] = "";
      }
    }
    setGenFieldValues(initialValues);

    // テーブル領域ごとに、まず1行分の空欄を用意する
    const initialTableRows: Record<string, Array<Record<string, string>>> = {};
    for (const region of fmt.table_regions || []) {
      initialTableRows[region.table_id] = [emptyTableRow(region)];
    }
    setGenTableRows(initialTableRows);
  }

  async function handleParseInstruction(formatId: string) {
    if (!chatInstruction.trim() || chatLoading) return;
    setChatLoading(true);
    setChatError(null);
    try {
      const response = await parseInstruction(formatId, chatInstruction);
      if (response.success === false) {
        throw new Error(response.error || "指示の解析に失敗しました");
      }
      const fieldValues: Record<string, string> = response.field_values || {};
      const filledCount = Object.keys(fieldValues).length;
      if (filledCount === 0) {
        setChatError("指示から項目を読み取れませんでした。表現を変えて試してください。");
      } else {
        setGenFieldValues((prev) => ({ ...prev, ...fieldValues }));
      }
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "指示の解析に失敗しました");
    } finally {
      setChatLoading(false);
    }
  }

  function addTableRow(region: TableRegion) {
    setGenTableRows((prev) => ({
      ...prev,
      [region.table_id]: [...(prev[region.table_id] || []), emptyTableRow(region)],
    }));
  }

  function removeTableRow(tableId: string, rowIndex: number) {
    setGenTableRows((prev) => ({
      ...prev,
      [tableId]: (prev[tableId] || []).filter((_, i) => i !== rowIndex),
    }));
  }

  function updateTableCell(tableId: string, rowIndex: number, fieldName: string, value: string) {
    setGenTableRows((prev) => ({
      ...prev,
      [tableId]: (prev[tableId] || []).map((row, i) =>
        i === rowIndex ? { ...row, [fieldName]: value } : row
      ),
    }));
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

      {/* --- 帳票フォーマット --- */}
      <Card>
        <SectionHeader title="帳票フォーマット" />
        <p className="mt-2 text-xs text-sub">
          納品書などのテンプレートファイルをアップロードすると、AIが構造（単一項目と、明細のようなテーブル領域）を
          推測します。内容を確認・修正・承認（Governance）した後、実データを流し込んで帳票を自動生成できます。
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
        {reviewError && <p className="mt-2 text-sm text-red-700">{reviewError}</p>}
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
                    {statusLabel(fmt.status)} / 検出フィールド数:{" "}
                    {fmt.status === "QUEUED_FOR_REVIEW"
                      ? getEditableMappings(fmt).length
                      : fmt.field_mappings?.length ?? 0}
                    {fmt.table_regions?.length ? ` / テーブル領域: ${fmt.table_regions.length}件` : ""}
                    {fmt.approver_id ? ` / 承認者: ${fmt.approver_id}` : ""}
                  </p>
                </div>
                {fmt.status === "APPROVED" && (
                  <Button tone="ghost" size="sm" onClick={() => openGeneratePanel(fmt)}>
                    {selectedFormatId === fmt.format_id ? "閉じる" : "このフォーマットで生成"}
                  </Button>
                )}
                {fmt.status === "QUEUED_FOR_REVIEW" && (
                  <span className="text-xs text-amber-700">承認待ち</span>
                )}
              </div>

              {fmt.status === "QUEUED_FOR_REVIEW" && (
                <div className="mt-3 border-t border-slate-200 pt-3">
                  <p className="text-xs font-medium text-sub">
                    検出内容（確信度の低い順に表示）。項目名・入力先セルは直接修正でき、不要な行は削除できます。
                    「テーブル」と表示された行は、明細のように複数行繰り返される領域として扱われます。
                    ここで確定した内容が、承認後に実際に使われます。
                  </p>
                  <div className="mt-2 max-h-80 overflow-y-auto rounded border border-slate-200">
                    <table className="w-full text-left text-xs">
                      <thead className="sticky top-0 bg-slate-50">
                        <tr>
                          <th className="px-2 py-1 font-medium text-sub">項目名</th>
                          <th className="px-2 py-1 font-medium text-sub">見出しセル</th>
                          <th className="px-2 py-1 font-medium text-sub">入力先セル</th>
                          <th className="px-2 py-1 font-medium text-sub">種別</th>
                          <th className="px-2 py-1 font-medium text-sub">確信度</th>
                          <th className="px-2 py-1 font-medium text-sub"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...getEditableMappings(fmt)]
                          .sort((a, b) => a.confidence - b.confidence)
                          .map((mapping, idx) => (
                            <tr
                              key={mapping.label_cell}
                              className={
                                mapping.confidence < 0.6
                                  ? "bg-amber-50"
                                  : idx % 2 === 0
                                  ? "bg-white"
                                  : "bg-slate-50/50"
                              }
                            >
                              <td className="px-2 py-1">
                                <input
                                  value={mapping.field_name}
                                  onChange={(e) =>
                                    updateMappingField(fmt, mapping.label_cell, "field_name", e.target.value)
                                  }
                                  className="w-full rounded border border-slate-300 px-1 py-0.5 text-xs"
                                />
                              </td>
                              <td className="px-2 py-1 text-sub">{mapping.label_cell}</td>
                              <td className="px-2 py-1">
                                <input
                                  value={mapping.input_cell}
                                  onChange={(e) =>
                                    updateMappingField(fmt, mapping.label_cell, "input_cell", e.target.value)
                                  }
                                  className="w-20 rounded border border-slate-300 px-1 py-0.5 text-xs"
                                />
                                （{mapping.direction === "right" ? "右" : "下"}）
                              </td>
                              <td className="px-2 py-1 text-sub">
                                {mapping.table_id ? (
                                  <span className="rounded bg-teal-100 px-1.5 py-0.5 text-teal-800">
                                    テーブル
                                  </span>
                                ) : (
                                  "単一項目"
                                )}
                              </td>
                              <td className="px-2 py-1 text-sub">
                                {Math.round(mapping.confidence * 100)}%
                              </td>
                              <td className="px-2 py-1">
                                <button
                                  onClick={() => deleteMappingRow(fmt, mapping.label_cell)}
                                  className="text-xs text-red-600 hover:underline"
                                >
                                  削除
                                </button>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-1 text-xs text-sub">
                    黄色でハイライトされている行は確信度が低く（60%未満）、誤検出の可能性があります。
                  </p>

                  <label className="mt-3 block text-xs font-medium text-sub">
                    承認・却下の理由（任意）
                  </label>
                  <input
                    value={reviewReasons[fmt.governance_approval_id] || ""}
                    onChange={(e) =>
                      setReviewReasons((prev) => ({
                        ...prev,
                        [fmt.governance_approval_id]: e.target.value,
                      }))
                    }
                    placeholder="例: フォーマットの内容を確認し、問題ありません"
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                  <div className="mt-3 flex gap-2">
                    <Button
                      onClick={() => handleReview(fmt, "APPROVED")}
                      className={reviewLoadingId === fmt.governance_approval_id ? "opacity-60" : ""}
                    >
                      承認する
                    </Button>
                    <Button
                      tone="ghost"
                      onClick={() => handleReview(fmt, "REJECTED")}
                      className={reviewLoadingId === fmt.governance_approval_id ? "opacity-60" : ""}
                    >
                      却下する
                    </Button>
                  </div>
                </div>
              )}

              {selectedFormatId === fmt.format_id && (
                <div className="mt-3 border-t border-slate-200 pt-3">
                  <label className="block text-xs font-medium text-sub">
                    案件ID（任意・実案件データを自動反映します。下で個別に入力した項目が優先されます）
                  </label>
                  <input
                    value={genProjectId}
                    onChange={(e) => setGenProjectId(e.target.value)}
                    placeholder="例: 7722"
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />

                  <p className="mt-4 text-xs font-medium text-sub">
                    チャットで指示して自動反映（任意・単一項目のみ対応）
                  </p>
                  <textarea
                    value={chatInstruction}
                    onChange={(e) => setChatInstruction(e.target.value)}
                    placeholder="例: 顧客名はUS_LOGS Inc.、担当者は高越"
                    rows={2}
                    className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                  <div className="mt-2">
                    <Button
                      tone="ghost"
                      size="sm"
                      onClick={() => handleParseInstruction(fmt.format_id)}
                      className={chatLoading ? "opacity-60" : ""}
                    >
                      {chatLoading ? "解析中..." : "解析して反映"}
                    </Button>
                  </div>
                  {chatError && <p className="mt-2 text-xs text-red-700">{chatError}</p>}

                  <p className="mt-4 text-xs font-medium text-sub">検出された項目（空欄でも構いません）</p>
                  <div className="mt-2 space-y-2">
                    {(fmt.field_mappings || [])
                      .filter((m) => !m.table_id)
                      .map((mapping) => (
                        <div key={mapping.field_name}>
                          <label className="block text-xs text-sub">{mapping.field_name}</label>
                          <input
                            value={genFieldValues[mapping.field_name] ?? ""}
                            onChange={(e) =>
                              setGenFieldValues((prev) => ({
                                ...prev,
                                [mapping.field_name]: e.target.value,
                              }))
                            }
                            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                          />
                        </div>
                      ))}
                  </div>

                  {(fmt.table_regions || []).map((region) => (
                    <div key={region.table_id} className="mt-5">
                      <p className="text-xs font-medium text-sub">
                        明細テーブル（{region.columns.map((c) => c.field_name).join(" / ")}）
                      </p>
                      <div className="mt-2 overflow-x-auto rounded border border-slate-200">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-50">
                            <tr>
                              {region.columns.map((col) => (
                                <th key={col.field_name} className="px-2 py-1 font-medium text-sub">
                                  {col.field_name}
                                </th>
                              ))}
                              <th className="px-2 py-1"></th>
                            </tr>
                          </thead>
                          <tbody>
                            {(genTableRows[region.table_id] || []).map((row, rowIndex) => (
                              <tr key={rowIndex}>
                                {region.columns.map((col) => (
                                  <td key={col.field_name} className="px-2 py-1">
                                    <input
                                      value={row[col.field_name] ?? ""}
                                      onChange={(e) =>
                                        updateTableCell(
                                          region.table_id,
                                          rowIndex,
                                          col.field_name,
                                          e.target.value
                                        )
                                      }
                                      className="w-full min-w-[6rem] rounded border border-slate-300 px-1 py-0.5 text-xs"
                                    />
                                  </td>
                                ))}
                                <td className="px-2 py-1">
                                  <button
                                    onClick={() => removeTableRow(region.table_id, rowIndex)}
                                    className="text-xs text-red-600 hover:underline"
                                  >
                                    削除
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <button
                        onClick={() => addTableRow(region)}
                        className="mt-2 rounded border border-slate-300 bg-white px-3 py-1 text-xs text-ink hover:bg-slate-50"
                      >
                        + 行を追加
                      </button>
                    </div>
                  ))}

                  <div className="mt-4">
                    <Button
                      onClick={() => handleGenerate(fmt)}
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
                      {Object.entries(genResult.tables_written || {}).map(([tableId, count]) => (
                        <p key={tableId} className="text-xs text-sub">
                          テーブル {tableId}: {count}行を書き込みました
                        </p>
                      ))}
                      {genResult.write_errors?.length > 0 && (
                        <div className="rounded bg-red-50 p-2">
                          <p className="text-xs font-medium text-red-700">
                            書き込めなかった項目（テンプレートの結合セルなどが原因の可能性があります。
                            承認待ち画面の「入力先セル」を修正してください）
                          </p>
                          <ul className="mt-1 list-disc pl-4 text-xs text-red-700">
                            {genResult.write_errors.map((err, i) => (
                              <li key={i}>{err}</li>
                            ))}
                          </ul>
                        </div>
                      )}
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
