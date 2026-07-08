"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getProducts } from "@/lib/api-client";

interface ApiProduct {
  product_id: string;
  logs_code: string | null;
  product_name: string | null;
  model_no: string | null;
  supplier_name: string | null;
  sample_code: string | null;
}

export default function ProductsListPage() {
  const [search, setSearch] = useState("");
  const [scopeChoice, setScopeChoice] = useState<"mine" | "all">("mine");
  const [products, setProducts] = useState<ApiProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getProducts(50, scopeChoice).then((data: any) => {
      setLoading(false);
      if (data?.success === false) {
        setError(data.error ?? "データの取得に失敗しました");
        return;
      }
      setError(null);
      setProducts(data?.products ?? []);
    });
  }, [scopeChoice]);

  const filtered = products.filter((p) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (p.product_name ?? "").toLowerCase().includes(q) ||
      (p.logs_code ?? "").toLowerCase().includes(q) ||
      (p.supplier_name ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">商品</h1>
        <p className="page-subtitle">
          商品（LOGS_CODE単位）を表示しています。PO・売上・仕入・サンプル対応を横断できます。
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {error}
        </div>
      )}

      {!loading && !error && scopeChoice === "mine" && products.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-sub">
          関連する商品が見つかりませんでした（社員マスタの氏名と、PO・売上・仕入・商品マスタ上の担当者名が一致しない可能性があります）。「すべての商品」に切り替えてご覧いただけます。
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        {/* 2026-07-08: トグルの選択肢・他の検索オプションは今後検討予定 */}
        <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5 text-sm">
          <button
            onClick={() => setScopeChoice("mine")}
            className={`rounded-md px-3 py-1.5 font-medium transition ${
              scopeChoice === "mine" ? "bg-accent text-white" : "text-ink hover:bg-slate-100"
            }`}
          >
            自分の商品
          </button>
          <button
            onClick={() => setScopeChoice("all")}
            className={`rounded-md px-3 py-1.5 font-medium transition ${
              scopeChoice === "all" ? "bg-accent text-white" : "text-ink hover:bg-slate-100"
            }`}
          >
            すべての商品
          </button>
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="商品名・LOGS_CODE・仕入先名で検索"
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="grid grid-cols-4 gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-medium text-sub">
          <span>Sample_CODE / 商品名</span>
          <span>LOGS_CODE</span>
          <span>型番</span>
          <span>仕入先</span>
        </div>
        {loading && (
          <p className="px-4 py-8 text-center text-sm text-sub">読み込み中...</p>
        )}
        {!loading && filtered.map((p) => (
          <Link
            key={p.product_id}
            href={`/products/${p.product_id}`}
            className="grid grid-cols-4 items-center gap-2 border-b border-slate-100 px-4 py-3 text-sm text-ink last:border-b-0 hover:bg-slate-50"
          >
            <span>
              <span className="font-medium">{p.product_name ?? "(商品名なし)"}</span>
              <span className="ml-2 text-xs text-sub">{p.sample_code ?? "—"}</span>
            </span>
            <span className="text-sub">{p.logs_code ?? "（未発注）"}</span>
            <span className="text-sub">{p.model_no ?? "—"}</span>
            <span className="text-sub">{p.supplier_name ?? "—"}</span>
          </Link>
        ))}
        {!loading && filtered.length === 0 && products.length > 0 && (
          <p className="px-4 py-8 text-center text-sm text-sub">該当する商品がありません</p>
        )}
      </div>
    </div>
  );
}

