"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge, Card, SectionHeader } from "@/components/design-system";
import { getProduct } from "@/lib/api-client";

type Params = { params: { productId: string } };

interface PurchaseOrderGroup {
  PO_No: string;
  project_id: string;
  顧客名: string | null;
  営業担当者名: string | null;
  PO発行日: string | null;
  発注数量: number | null;
  発注金額: number | null;
  発注金額通貨: string | null;
  line_count: number;
}

interface SalesLine {
  ID: number | string | null;
  得意先名: string | null;
  営業担当者名: string | null;
  事務処理担当者名: string | null;
  経理担当者名: string | null;
  数量pcs: number | null;
  売上金額: number | null;
  売上入力日: string | null;
}

interface PurchaseLine {
  ID: number | string | null;
  仕入先名: string | null;
  営業担当者名: string | null;
  営業事務担当者名: string | null;
  生産管理担当者名: string | null;
  仕入数量pcs: number | null;
  仕入金額円: number | null;
  伝票日: string | null;
}

interface SampleLine {
  見積No: string | null;
  仕入先名: string | null;
  依頼内容: string | null;
  カラー: string | null;
  サイズ: string | null;
  数量: number | null;
  回答者: string | null;
  依頼元: string | null;
  回答日: string | null;
  通知状況: string | null;
}

interface RelatedMessage {
  status: string;
  summary: string;
  records: Array<Record<string, any>>;
}

interface RelatedCommunications {
  gmail: RelatedMessage;
  slack: RelatedMessage;
}

interface ProductDetail {
  master: Record<string, any>;
  purchase_orders: PurchaseOrderGroup[];
  sales: SalesLine[];
  purchases: PurchaseLine[];
  samples: SampleLine[];
  related_communications?: RelatedCommunications;
  status: {
    po_issued: boolean;
    sales_recorded: boolean;
    purchase_recorded: boolean;
    sample_requested: boolean;
  };
}

function fmtYen(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${Math.round(v).toLocaleString()}円`;
}

// 2026-07-13（14.84、Noritsuguが実データで発見）: purchase_ordersの
// "発注金額"・"売上原価"由来の金額（発注単価と同じ行の"通貨"列に属し、
// 円固定ではない）はfmtYenで円と決め打ちしてはいけない。currencyLabel
// が無い場合（データ欠損等）だけ、従来通り円として扱う（後方互換）。
function fmtAmount(v: number | null | undefined, currencyLabel: string | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const currency = currencyLabel || "円";
  return currency === "円" ? fmtYen(v) : `${Math.round(v).toLocaleString()} ${currency}`;
}

export default function ProductDetailPage({ params }: Params) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProduct(params.productId).then((data: any) => {
      setLoading(false);
      if (data?.success === false) {
        setError(data.error ?? "商品データの取得に失敗しました");
        return;
      }
      setProduct(data?.product ?? null);
    });
  }, [params.productId]);

  if (loading) {
    return <p className="px-4 py-8 text-center text-sm text-sub">読み込み中...</p>;
  }

  if (error || !product) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error ?? "商品が見つかりませんでした"}
      </div>
    );
  }

  const m = product.master;

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">商品: {m.商品名 ?? `商品ID ${m.ID}`}</h1>
        <p className="page-subtitle">
          Sample_CODE: {m.Sample_CODE ?? "—"} ／ LOGS_CODE: {m.LOGS_CODE ?? "（未発注）"}
        </p>
      </header>

      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Badge label={product.status.po_issued ? "PO発行済み" : "PO未発行"} tone={product.status.po_issued ? "success" : "default"} />
          <Badge label={product.status.sales_recorded ? "売上入力済み" : "売上未入力"} tone={product.status.sales_recorded ? "success" : "default"} />
          <Badge label={product.status.purchase_recorded ? "仕入入力済み" : "仕入未入力"} tone={product.status.purchase_recorded ? "success" : "default"} />
          <Badge label={product.status.sample_requested ? "サンプル対応あり" : "サンプル対応なし"} tone={product.status.sample_requested ? "success" : "default"} />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-sub sm:grid-cols-3">
          <div>型番: {m.型番 ?? "—"}</div>
          <div>商品分類: {m.商品分類名 ?? "—"}</div>
          <div>仕入先: {m.仕入先名 ?? "—"}</div>
          <div>作成者: {m.作成者名 ?? "—"}</div>
          <div>仕入先の生産管理担当: {m.supplier_production_staff ?? "—"}</div>
          <div>営業事務担当: {m.営業事務担当者名 ?? "—"}</div>
          <div>通常売価: {fmtYen(m.通常売価)}</div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-sub sm:grid-cols-3 border-t border-slate-100 pt-3">
          <div>発注単価: {m.発注単価 != null ? `${m.発注単価.toLocaleString()} ${m.発注単価通貨 ?? ""}`.trim() : "—"}</div>
          <div>予定輸入経費率: {m.予定輸入経費率 != null ? Number(m.予定輸入経費率).toFixed(2) : "—"}</div>
          <div>予定原価単価: {fmtAmount(m.予定原価単価, m.予定原価単価通貨)}</div>
          <div>実績輸入経費率: {m.実績輸入経費率 != null ? Number(m.実績輸入経費率).toFixed(2) : "—"}</div>
          <div>実績原価単価: {fmtYen(m.実績原価単価)}</div>
        </div>
        <p className="mt-1 text-xs text-sub">
          いずれも最新のPO明細（PO発行日が最新の1件）、または全ての仕入明細（カラー/サイズ違いやリピートオーダーを含む全行）から取得。発注単価・予定輸入経費率・予定原価単価はPO入力時点（最新1件）、実績輸入経費率・実績原価単価は仕入確定後の値（全明細行の加重平均）です。発注単価・予定原価単価・PO履歴の金額は、いずれもPOに入力された通貨のままで、円ではない場合があります（実績原価単価は仕入確定後の円換算済みの値です）。
        </p>
      </Card>

      <Card>
        <SectionHeader title="PO(発注)履歴" subtitle="この商品が含まれるPurchase Orderの一覧です。PO単位でまとめて表示しています（クリックで案件詳細へ）。" />
        <div className="mt-3 space-y-2">
          {product.purchase_orders.length > 0 ? (
            product.purchase_orders.map((po) => (
              <Link
                key={po.PO_No}
                href={`/workspace/${po.project_id}`}
                className="block rounded-lg border border-slate-200 p-3 text-xs transition hover:border-slate-300 hover:bg-slate-50"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">{po.PO_No}</span>
                  <span className="text-sub">{po.PO発行日 ?? "—"}</span>
                </div>
                <p className="mt-1 text-sub">
                  顧客: {po.顧客名 ?? "—"} ・ 営業: {po.営業担当者名 ?? "—"} ・ 数量: {po.発注数量 ?? "—"} ・ 金額: {fmtAmount(po.発注金額, po.発注金額通貨)}
                  {po.line_count > 1 && ` （明細${po.line_count}件を合算）`}
                </p>
              </Link>
            ))
          ) : (
            <p className="text-sm text-sub">PO発行の記録はありません</p>
          )}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader title="売上履歴" subtitle="この商品の売上明細です（最新5件、同一売上IDは1件にまとめています）。" />
          <div className="mt-3 space-y-2">
            {product.sales.length > 0 ? (
              product.sales.map((s, idx) => (
                <div key={idx} className="rounded-lg border border-slate-200 p-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-ink">{s.得意先名 ?? "—"}</span>
                    <span className="text-sub">{s.売上入力日 ?? "—"}</span>
                  </div>
                  <p className="mt-1 text-sub">売上ID: {s.ID ?? "—"} ・ 営業: {s.営業担当者名 ?? "—"} ・ 数量: {s.数量pcs ?? "—"} ・ 金額: {fmtYen(s.売上金額)}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-sub">売上入力の記録はありません</p>
            )}
          </div>
        </Card>

        <Card>
          <SectionHeader title="仕入履歴" subtitle="この商品の仕入明細です（明細レベルの担当者を優先表示、同一仕入IDは1件にまとめています）。" />
          <div className="mt-3 space-y-2">
            {product.purchases.length > 0 ? (
              product.purchases.map((p, idx) => (
                <div key={idx} className="rounded-lg border border-slate-200 p-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-ink">{p.仕入先名 ?? "—"}</span>
                    <span className="text-sub">{p.伝票日 ?? "—"}</span>
                  </div>
                  <p className="mt-1 text-sub">
                    仕入ID: {p.ID ?? "—"} ・ 営業: {p.営業担当者名 ?? "—"} ・ 生産管理: {p.生産管理担当者名 ?? "—"} ・ 数量: {p.仕入数量pcs ?? "—"} ・ 金額: {fmtYen(p.仕入金額円)}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-sub">仕入入力の記録はありません</p>
            )}
          </div>
        </Card>
      </div>

      {product.samples.length > 0 && (
        <Card>
          <SectionHeader
            title="サンプル対応履歴"
            subtitle="生産管理チームのスプレッドシートから、Sample_CODEで突合したサンプル対応状況です。"
          />
          <div className="mt-3 space-y-2">
            {product.samples.map((s, idx) => (
              <div key={idx} className="rounded-lg border border-slate-200 p-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">{s.依頼内容 ?? "サンプル依頼"}</span>
                  {s.通知状況 && <Badge label={s.通知状況} />}
                </div>
                <p className="mt-1 text-sub">
                  回答者: {s.回答者 ?? "—"} ・ 依頼元: {s.依頼元 ?? "—"} ・ カラー: {s.カラー ?? "—"} ・ サイズ: {s.サイズ ?? "—"}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}
      {product.related_communications && (
        <Card>
          <SectionHeader
            title="関連するメール・Slack"
            subtitle="LOGS_CODE・Sample_CODEで、あなた自身のGmail/Slackから検索した結果です。"
          />
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <h4 className="mb-2 text-xs font-semibold text-ink">Gmail</h4>
              {product.related_communications.gmail.status === "ok" && product.related_communications.gmail.records.length > 0 ? (
                <div className="space-y-2">
                  {product.related_communications.gmail.records.map((r, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-200 p-3 text-xs">
                      <p className="font-medium text-ink">{r.subject}</p>
                      <p className="text-sub">{r.from} ・ {r.date}</p>
                      {r.snippet && <p className="mt-1 text-sub">{r.snippet}</p>}
                    </div>
                  ))}
                </div>
              ) : product.related_communications.gmail.status === "unavailable" ? (
                <p className="text-xs text-sub">
                  {product.related_communications.gmail.summary}{" "}
                  <a href="/settings" className="text-accent hover:underline">設定画面へ</a>
                </p>
              ) : (
                <p className="text-xs text-sub">{product.related_communications.gmail.summary || "関連するメールは見つかりませんでした。"}</p>
              )}
            </div>
            <div>
              <h4 className="mb-2 text-xs font-semibold text-ink">Slack</h4>
              {product.related_communications.slack.status === "ok" && product.related_communications.slack.records.length > 0 ? (
                <div className="space-y-2">
                  {product.related_communications.slack.records.map((r, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-200 p-3 text-xs">
                      <p className="font-medium text-ink">#{r.channel} ・ {r.username}</p>
                      <p className="mt-1 text-sub">{r.text}</p>
                    </div>
                  ))}
                </div>
              ) : product.related_communications.slack.status === "unavailable" ? (
                <p className="text-xs text-sub">
                  {product.related_communications.slack.summary}{" "}
                  <a href="/settings" className="text-accent hover:underline">設定画面へ</a>
                </p>
              ) : (
                <p className="text-xs text-sub">{product.related_communications.slack.summary || "関連するメッセージは見つかりませんでした。"}</p>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
