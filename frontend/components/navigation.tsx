"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "ホーム" },
  { href: "/workspace", label: "案件" },
  { href: "/tasks", label: "今日のタスク" },
  { href: "/proposals", label: "資料作成" },
  { href: "/chat", label: "相談" },
];

// /history, /learning, /debug, /walking-skeleton are intentionally
// left out of the main menu but remain reachable by direct URL (Next.js routing).

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-4 h-fit rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-1 text-lg font-semibold tracking-tight text-accent">LOGS AI OS</div>
      <p className="mb-4 text-xs text-sub">業務エントリーコンソール</p>
      <ul className="space-y-2">
        {navItems.map((item) => {
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
    </nav>
  );
}
