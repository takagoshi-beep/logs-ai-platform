import { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export function SectionCard({ title, subtitle, children }: SectionCardProps) {
  return (
    <section className="card">
      <header className="mb-3">
        <h2 className="text-base font-semibold">{title}</h2>
        {subtitle ? <p className="text-xs text-sub">{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}
