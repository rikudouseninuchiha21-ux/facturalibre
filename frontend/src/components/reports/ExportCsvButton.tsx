"use client";

import { Button } from "@/components/ui/button";
import { downloadFile } from "@/lib/api";

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
      await downloadFile(path, fileName);
    } catch (cause) {
      const message =
        cause instanceof Error
          ? cause.message
          : "No se pudo descargar el archivo.";
      window.alert(message);
    }
  }

  return <Button onClick={handleDownload}>{label}</Button>;
}
