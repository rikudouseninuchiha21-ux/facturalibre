import type { ComponentProps } from "react";

export function Button({
  className = "",
  type = "button",
  ...props
}: ComponentProps<"button">) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-600 hover:shadow-[0_0_15px_rgba(79,70,229,0.5)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}
