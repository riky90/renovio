// PRIMA di tutto, e prima di `App` (che crea il router): toglie il
// `session_id` di Stripe dall'URL prima che lo vedano router e tracciamento.
import "@/lib/checkoutSession";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App.tsx";
import { Toaster } from "@/components/ui/sonner";
import { avviaConsenso } from "@/lib/tracciamento";

const queryClient = new QueryClient();

void avviaConsenso();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster />
    </QueryClientProvider>
  </StrictMode>,
);
