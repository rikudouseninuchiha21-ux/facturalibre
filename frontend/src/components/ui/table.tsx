import type { ComponentProps } from "react";

interface TableProps extends ComponentProps<"table"> {
  wrapperClassName?: string;
}

export function Table({
  className = "",
  wrapperClassName = "overflow-x-auto",
  ...props
}: TableProps) {
  return (
    <div className={`rounded-xl border border-slate-200 ${wrapperClassName}`}>
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

interface DenseTableHeadProps extends ComponentProps<"th"> {
  dense?: boolean;
}

interface DenseTableCellProps extends ComponentProps<"td"> {
  dense?: boolean;
}

export function TableHead({
  className = "",
  dense = false,
  ...props
}: DenseTableHeadProps) {
  const padding = dense ? "px-2 py-2" : "px-4 py-3";
  return (
    <th
      scope="col"
      className={`whitespace-nowrap ${padding} text-xs font-semibold uppercase tracking-wide text-slate-500 ${className}`}
      {...props}
    />
  );
}

export function TableCell({
  className = "",
  dense = false,
  ...props
}: DenseTableCellProps) {
  const cellStyles = dense
    ? "whitespace-normal break-words px-2 py-2 text-xs"
    : "whitespace-nowrap px-4 py-3 text-sm";
  return (
    <td className={`${cellStyles} text-slate-700 ${className}`} {...props} />
  );
}
