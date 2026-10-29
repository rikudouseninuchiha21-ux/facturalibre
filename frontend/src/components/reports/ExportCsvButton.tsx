"use client";

import { Button } from "@/components/ui/button";
import { downloadFileNative } from "@/lib/api";

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
  async function handleDownload(): Promise<void> {
    try {
      await downloadFileNative(path, fileName);
    } catch (cause) {
      window.alert(
        cause instanceof Error
          ? cause.message
          : "No se pudo descargar el archivo. Inténtalo de nuevo.",
      );
    }
  }

  return (
    <Button
      onClick={() => {
        void handleDownload();
      }}
    >
      {label}
    </Button>
  );
}
