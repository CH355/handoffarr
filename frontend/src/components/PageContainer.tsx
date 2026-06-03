import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface PageContainerProps {
  title: string;
  description?: string;
  children?: ReactNode;
  className?: string;
}

export function PageContainer({ title, description, children, className }: PageContainerProps) {
  return (
    <section aria-labelledby="page-title" className={cn("flex flex-col gap-6", className)}>
      <header className="flex flex-col gap-2">
        <h1 id="page-title" className="text-title text-text">
          {title}
        </h1>
        {description ? (
          <p className="max-w-[44ch] text-body text-text-muted">{description}</p>
        ) : null}
      </header>
      {children}
    </section>
  );
}
