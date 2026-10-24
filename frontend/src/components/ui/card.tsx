import type { ComponentProps } from "react";

export function Card({
  className = "",
  ...props
}: ComponentProps<"section">) {
  return (
    <section
      className={`rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900 ${className}`}
      {...props}
    />
  );
}

export function CardHeader({
  className = "",
  ...props
}: ComponentProps<"div">) {
  return (
    <div className={`flex flex-col gap-1.5 p-6 ${className}`} {...props} />
  );
}

export function CardTitle({
  className = "",
  ...props
}: ComponentProps<"h2">) {
  return (
    <h2
      className={`text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50 ${className}`}
      {...props}
    />
  );
}

export function CardDescription({
  className = "",
  ...props
}: ComponentProps<"p">) {
  return (
    <p
      className={`text-sm leading-6 text-zinc-600 dark:text-zinc-400 ${className}`}
      {...props}
    />
  );
}

export function CardContent({
  className = "",
  ...props
}: ComponentProps<"div">) {
  return <div className={`p-6 pt-0 ${className}`} {...props} />;
}
