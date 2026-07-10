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

const PAGE_SIZE = 50;

export default function ProductsListPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [scopeChoice, setScopeChoice] = useState<"mine" | "all">("mine");
  const [products, setProducts] = useState<ApiProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // 2026-07-09（14.54、Noritsuguの指定）: scope=allはサーバー側の全件
  // 検索にするため、入力ごとに毎回リクエストしないよう300msデバウンス
  // する。scope=mineは元々取得済みの少数件をクライアント側で絞り込む
  // だけなので、デバウンス不要（下のfilteredで直接searchを使う）。
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setLoading(true);
    getProducts(PAGE_SIZE, scopeChoice, 0, scopeChoice === "all" ? debouncedSearch : "").then((data: any) => {
      setLoading(false);
      if (data?.success === false) {
        setError(data.error ?? "データの取得に失敗しました");
        return;
      }
      setError(null);
      setProducts(data?.products ?? []);
      setHasMore(data?.has_more ?? false);
      setNextOffset(data?.next_offset ?? 0);
    });
  }, [scopeChoice, debouncedSearch]);

  function loadMore() {
    setLoadingMore(true);
    getProducts(PAGE_SIZE, "all", nextOffset, debouncedSearch).then((data: any) => {
      setLoadingMore(false);
      if (data?.success === false) return;
      setProducts((prev) => [...prev, ...(data?.products ?? [])]);
      setHasMore(data?.has_more ?? false);
      setNextOffset(data?.next_offset ?? 0);
    });
  }

  // scope=mineは取得済みの少数件をその場で絞り込むだけ（サーバー検索
  // 不要な規模のため）。scope=allは既にサーバー側で絞り込み済み。
  const filtered = scopeChoice === "all" ? products : products.filter((p) => {
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
        {scopeChoice === "all" && (
          <span className="text-xs text-sub">「すべての商品」では商品名・Sample_CODE・型番・LOGS_CODEを全件から検索します</span>
        )}
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
        {!loading && filtered.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-sub">該当する商品がありません</p>
        )}
      </div>

      {!loading && scopeChoice === "all" && hasMore && (
        <div className="flex justify-center">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-ink hover:bg-slate-50 disabled:opacity-50"
          >
            {loadingMore ? "読み込み中..." : "もっと見る"}
          </button>
        </div>
      )}
    </div>
  );
}