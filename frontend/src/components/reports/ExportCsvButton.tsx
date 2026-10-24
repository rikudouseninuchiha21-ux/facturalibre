"use client";

import { Button } from "@/components/ui/button";

interface ExportCsvButtonProps {
  label: string;
  path: string;
  fileName: string;
}

export function ExportCsvButton({
  label,
  path,
  fileName,
}: ExportCsvButtonProps) {
  async function handleDownload() {
    try {
      const response = await fetch(path, {
        credentials: "include",
        cache: "no-store",
      });

      if (!response.ok) {
        const fallback = `${response.status} ${response.statusText}`.trim();
        throw new Error(`Error al descargar ${path}: ${fallback}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (cause) {
      const message =
        cause instanceof Error ? cause.message : "No se pudo descargar el archivo.";
      window.alert(message);
    }
  }

  return (
    <Button onClick={handleDownload}>{label}</Button>
  );
}
