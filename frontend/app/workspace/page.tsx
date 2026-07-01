"use client";

import { useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/design-system";
import { projects } from "@/lib/mock-data";

export default function WorkspaceListPage() {
  const [search, setSearch] = useState("");
  const [owner, setOwner] = useState("all");
  const [status, setStatus] = useState("all");

  const owners = Array.from(new Set(projects.map((p) => p.owner)));
  const statuses = Array.from(new Set(projects.map((p) => p.status)));

  const filtered = projects.filter((p) => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (owner !== "all" && p.owner !== owner) return false;
    if (status !== "all" && p.status !== status) return false;
    return true;
  });

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="page-title">案件</h1>
      </header>

      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="案件名で検索"
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="all">担当者: すべて</option>
          {owners.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="all">進行状況: すべて</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="grid grid-cols-6 gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-medium text-sub">
          <span>案件名</span>
          <span>顧客</span>
          <span>担当</span>
          <span>状態</span>
          <span>更新日</span>
          <span>次にやること</span>
        </div>
        {filtered.map((project) => (
          <Link
            key={project.id}
            href={`/workspace/${project.id}`}
            className="grid grid-cols-6 items-center gap-2 border-b border-slate-100 px-4 py-3 text-sm text-ink last:border-b-0 hover:bg-slate-50"
          >
            <span className="font-medium">{project.name}</span>
            <span className="text-sub">{project.customer}</span>
            <span className="text-sub">{project.owner}</span>
            <span>
              <StatusBadge status={project.status} />
            </span>
            <span className="text-sub">{project.updatedAt}</span>
            <span className="text-sub">{project.nextAction}</span>
          </Link>
        ))}
        {filtered.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-sub">該当する案件がありません</p>
        )}
      </div>
    </div>
  );
}
