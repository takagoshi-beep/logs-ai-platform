import Link from "next/link";
import { ReactNode } from "react";

type Tone = "primary" | "neutral" | "danger" | "ghost";
type Size = "sm" | "md";

type ButtonProps = {
  children: ReactNode;
  tone?: Tone;
  size?: Size;
  href?: string;
  onClick?: () => void;
  type?: "button" | "submit" | "reset";
  className?: string;
};

const toneClass: Record<Tone, string> = {
  primary: "bg-accent text-white hover:bg-teal-700",
  neutral: "bg-slate-800 text-white hover:bg-slate-700",
  danger: "bg-danger text-white hover:bg-red-700",
  ghost: "border border-slate-300 bg-white text-ink hover:bg-slate-50",
};

const sizeClass: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
};

export function Button({ children, tone = "primary", size = "md", href, onClick, type = "button", className = "" }: ButtonProps) {
  const classes = `inline-flex items-center justify-center rounded-lg font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-accent ${toneClass[tone]} ${sizeClass[size]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} onClick={onClick} className={classes}>
      {children}
    </button>
  );
}

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = "" }: CardProps) {
  return <section className={`rounded-xl border border-slate-200 bg-panel p-4 shadow-sm ${className}`}>{children}</section>;
}

type BadgeTone = "default" | "high" | "medium" | "low" | "success";

const badgeToneClass: Record<BadgeTone, string> = {
  default: "bg-slate-100 text-slate-700 border-slate-200",
  high: "bg-red-50 text-red-700 border-red-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  success: "bg-teal-50 text-teal-700 border-teal-200",
};

export function Badge({ label, tone = "default" }: { label: string; tone?: BadgeTone }) {
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${badgeToneClass[tone]}`}>{label}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  let tone: BadgeTone = "default";
  if (normalized.includes("open") || status.includes("未着手") || status.includes("未対応")) tone = "medium";
  if (normalized.includes("progress") || status.includes("対応中")) tone = "high";
  if (normalized.includes("ready") || normalized.includes("done") || normalized.includes("accepted") || status.includes("完了") || status.includes("承認")) tone = "success";
  if (normalized.includes("hold") || normalized.includes("pending") || status.includes("保留") || status.includes("待ち")) tone = "default";
  return <Badge label={status} tone={tone} />;
}

export function Alert({ title, message, level = "medium" }: { title: string; message: string; level?: "high" | "medium" }) {
  return (
    <Card className={level === "high" ? "border-red-200 bg-red-50/50" : "border-amber-200 bg-amber-50/50"}>
      <div className="mb-1 flex items-center gap-2">
        <Badge label={level === "high" ? "要注意" : "確認"} tone={level === "high" ? "high" : "medium"} />
        <p className="text-sm font-semibold text-ink">{title}</p>
      </div>
      <p className="text-sm text-sub">{message}</p>
    </Card>
  );
}

export function KpiCard({ label, value, trend }: { label: string; value: string; trend?: string }) {
  return (
    <Card>
      <p className="text-xs text-sub">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {trend ? <p className="mt-1 text-xs text-sub">{trend}</p> : null}
    </Card>
  );
}

type TaskCardProps = {
  title: string;
  project: string;
  due: string;
  reason: string;
  actions?: ReactNode;
};

export function TaskCard({ title, project, due, reason, actions }: TaskCardProps) {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-xs text-sub">案件: {project}</p>
      <p className="text-xs text-sub">期限: {due}</p>
      <p className="mt-2 text-xs text-sub">理由: {reason}</p>
      {actions ? <div className="mt-3 flex flex-wrap gap-2">{actions}</div> : null}
    </Card>
  );
}

export function ProjectCard({ name, summary, owner, status, href }: { name: string; summary: string; owner: string; status: string; href?: string }) {
  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">{name}</h3>
        <StatusBadge status={status} />
      </div>
      <p className="text-sm text-sub">{summary}</p>
      <p className="mt-2 text-xs text-sub">担当: {owner}</p>
      {href ? (
        <div className="mt-3">
          <Button href={href} tone="ghost" size="sm">
            案件を開く
          </Button>
        </div>
      ) : null}
    </Card>
  );
}

export function Timeline({ items }: { items: Array<{ id: string; title: string; time: string; detail?: string }> }) {
  return (
    <ol className="space-y-3">
      {items.map((item) => (
        <li key={item.id} className="relative pl-5">
          <span className="absolute left-0 top-1.5 h-2 w-2 rounded-full bg-accent" />
          <p className="text-sm font-medium text-ink">{item.title}</p>
          <p className="text-xs text-sub">{item.time}</p>
          {item.detail ? <p className="text-xs text-sub">{item.detail}</p> : null}
        </li>
      ))}
    </ol>
  );
}

export function Progress({ value, label }: { value: number; label: string }) {
  const safeValue = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-sub">{label}</span>
        <span className="font-medium text-ink">{safeValue}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-accent transition-all" style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
        {subtitle ? <p className="text-sm text-sub">{subtitle}</p> : null}
      </div>
      {action ? <div>{action}</div> : null}
    </header>
  );
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <Card className="border-dashed text-center">
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="mt-1 text-sm text-sub">{description}</p>
      {action ? <div className="mt-3 flex justify-center">{action}</div> : null}
    </Card>
  );
}

export function ActionPanel({ title, items, action }: { title: string; items: Array<{ label: string; value: string }>; action?: ReactNode }) {
  return (
    <Card>
      <SectionHeader title={title} />
      <dl className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-start justify-between gap-3">
            <dt className="text-xs text-sub">{item.label}</dt>
            <dd className="text-xs font-medium text-ink text-right">{item.value}</dd>
          </div>
        ))}
      </dl>
      {action ? <div className="mt-3">{action}</div> : null}
    </Card>
  );
}
