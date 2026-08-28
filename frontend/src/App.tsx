import { createBrowserRouter, Navigate, RouterProvider } from "react-router";
import { EstimatePage } from "@/pages/EstimatePage";
import { RegistratiPage } from "@/routes/RegistratiPage";
import { AccediPage } from "@/routes/AccediPage";
import { PasswordDimenticataPage } from "@/routes/PasswordDimenticataPage";
import { ReimpostaPasswordPage } from "@/routes/ReimpostaPasswordPage";
import { LeMieStimePage } from "@/routes/LeMieStimePage";
import { PassaAProPage } from "@/routes/PassaAProPage";
import { DettaglioProPage } from "@/pages/DettaglioProPage";
import { LeadDashboardPage } from "@/pages/admin/LeadDashboardPage";
import { ReferentiPage } from "@/pages/admin/ReferentiPage";
import { ListiniPage } from "@/pages/admin/ListiniPage";
import { CoefficientiPage } from "@/pages/admin/CoefficientiPage";
import { CittaTestiPage } from "@/pages/admin/CittaTestiPage";
import { UtentiPage } from "@/pages/admin/UtentiPage";
import { DettaglioProAdminPage } from "@/pages/admin/DettaglioProPage";

const router = createBrowserRouter([
  { path: "/", element: <EstimatePage /> },
  { path: "/registrati", element: <RegistratiPage /> },
  { path: "/accedi", element: <AccediPage /> },
  { path: "/password-dimenticata", element: <PasswordDimenticataPage /> },
  { path: "/reimposta-password", element: <ReimpostaPasswordPage /> },
  { path: "/le-mie-stime", element: <LeMieStimePage /> },
  { path: "/passa-a-pro", element: <PassaAProPage /> },
  { path: "/dettaglio-pro", element: <DettaglioProPage /> },
  { path: "/admin", element: <Navigate to="/admin/lead" replace /> },
  { path: "/admin/lead", element: <LeadDashboardPage /> },
  { path: "/admin/listini", element: <ListiniPage /> },
  { path: "/admin/dettaglio-pro", element: <DettaglioProAdminPage /> },
  { path: "/admin/coefficienti", element: <CoefficientiPage /> },
  { path: "/admin/citta-testi", element: <CittaTestiPage /> },
  { path: "/admin/referenti", element: <ReferentiPage /> },
  { path: "/admin/utenti", element: <UtentiPage /> },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
