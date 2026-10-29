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
}: ExportCsvButtonProps) {
  return (
    <Button onClick={() => downloadFileNative(path)}>
      {label}
    </Button>
  );
}
