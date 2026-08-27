import { createBrowserRouter, RouterProvider } from "react-router";
import { EstimatePage } from "@/pages/EstimatePage";
import { RegistratiPage } from "@/routes/RegistratiPage";
import { AccediPage } from "@/routes/AccediPage";
import { PasswordDimenticataPage } from "@/routes/PasswordDimenticataPage";
import { ReimpostaPasswordPage } from "@/routes/ReimpostaPasswordPage";
import { LeMieStimePage } from "@/routes/LeMieStimePage";
import { PassaAProPage } from "@/routes/PassaAProPage";

const router = createBrowserRouter([
  { path: "/", element: <EstimatePage /> },
  { path: "/registrati", element: <RegistratiPage /> },
  { path: "/accedi", element: <AccediPage /> },
  { path: "/password-dimenticata", element: <PasswordDimenticataPage /> },
  { path: "/reimposta-password", element: <ReimpostaPasswordPage /> },
  { path: "/le-mie-stime", element: <LeMieStimePage /> },
  { path: "/passa-a-pro", element: <PassaAProPage /> },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
