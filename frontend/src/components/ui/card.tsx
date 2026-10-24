import type { ComponentProps } from "react";

export function Card({
  className = "",
  ...props
}: ComponentProps<"section">) {
  return (
    <section
      className={`rounded-2xl border border-zinc-200/60 bg-white shadow-sm ${className}`}
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
      className={`text-lg font-semibold tracking-tight text-zinc-950 ${className}`}
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
      className={`text-sm leading-6 text-zinc-600 ${className}`}
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
