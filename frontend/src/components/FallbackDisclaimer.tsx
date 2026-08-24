import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface FallbackDisclaimerProps {
  disclaimer: string;
}

/** Amber informational alert — rendered only when the API reports fallback=true. */
export function FallbackDisclaimer({ disclaimer }: FallbackDisclaimerProps) {
  return (
    <Alert className="border-amber-border bg-amber-bg text-amber-fg">
      <AlertTriangle className="text-amber-fg" />
      <AlertDescription className="text-amber-fg">{disclaimer}</AlertDescription>
    </Alert>
  );
}
