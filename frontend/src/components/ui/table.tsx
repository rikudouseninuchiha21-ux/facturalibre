import type { ComponentProps } from "react";

export function Table({
  className = "",
  ...props
}: ComponentProps<"table">) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table
        className={`min-w-full divide-y divide-slate-200 text-left ${className}`}
        {...props}
      />
    </div>
  );
}

export function TableHeader({
  className = "",
  ...props
}: ComponentProps<"thead">) {
  return <thead className={`bg-slate-50 ${className}`} {...props} />;
}

export function TableBody({
  className = "",
  ...props
}: ComponentProps<"tbody">) {
  return (
    <tbody
      className={`divide-y divide-slate-100 bg-white ${className}`}
      {...props}
    />
  );
}

export function TableRow({
  className = "",
  ...props
}: ComponentProps<"tr">) {
  return (
    <tr
      className={`transition-colors hover:bg-slate-50/80 ${className}`}
      {...props}
    />
  );
}

export function TableHead({
  className = "",
  ...props
}: ComponentProps<"th">) {
  return (
    <th
      scope="col"
      className={`whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 ${className}`}
      {...props}
    />
  );
}

export function TableCell({
  className = "",
  ...props
}: ComponentProps<"td">) {
  return (
    <td
      className={`whitespace-nowrap px-4 py-3 text-sm text-slate-700 ${className}`}
      {...props}
    />
  );
}
