"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { href: "/", label: "ホーム" },
  { href: "/products", label: "商品" },
  { href: "/workspace", label: "案件" },
  { href: "/tasks", label: "今日のタスク" },
  { href: "/proposals", label: "資料作成" },
  { href: "/chat", label: "相談" },
  { href: "/reasoning", label: "推論エンジン" },
];

// 2026-07-15（14.102、Noritsuguの指定）: Learningは管理者のみメニューに
// 表示する（一般ユーザーには従来通り非表示のまま）。/history・/debug・
// /walking-skeletonは引き続き意図的にメニュー外（直接URLでのみ到達可）。
const adminNavItems = [
  { href: "/learning", label: "Learning" },
];

export function Navigation() {
  const pathname = usePathname();
  const { user, isAdmin, logout } = useAuth();
  const items = isAdmin ? [...navItems, ...adminNavItems] : navItems;

  return (
    <nav className="sticky top-4 flex h-fit flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-1 text-lg font-semibold tracking-tight text-accent">LOGS AI OS</div>
      <p className="mb-4 text-xs text-sub">業務エントリーコンソール</p>
      <ul className="space-y-2">
        {items.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`block rounded-lg px-3 py-2 text-sm font-medium transition ${
                  active ? "bg-accent text-white" : "text-ink hover:bg-slate-100"
                }`}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
      {user && (
        <div className="mt-6 border-t border-slate-200 pt-4">
          <p className="truncate text-xs font-medium text-ink">{user.name}</p>
          <p className="truncate text-xs text-sub">{user.email}</p>
          <p className="mt-1 text-xs text-sub">{isAdmin ? "管理者" : "一般"}</p>
          <Link href="/settings" className="mt-2 block text-xs text-accent hover:underline">
            設定
          </Link>
          <button
            onClick={logout}
            className="mt-2 text-xs text-accent hover:underline"
          >
            ログアウト
          </button>
        </div>
      )}
    </nav>
  );
}
