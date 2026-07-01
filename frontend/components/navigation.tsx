"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/tasks", label: "Task Center" },
  { href: "/workspace/fanatics-oem", label: "Workspace" },
  { href: "/chat", label: "Chat" },
  { href: "/proposals", label: "Proposal Builder" },
  { href: "/history", label: "History" },
  { href: "/learning", label: "Learning Center" },
  { href: "/debug", label: "Debug Trace" },
  { href: "/walking-skeleton", label: "Walking Skeleton" },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-4 h-fit rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-1 text-lg font-semibold tracking-tight text-accent">LOGS AI OS</div>
      <p className="mb-4 text-xs text-sub">Work Entry Console</p>
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
