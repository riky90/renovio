import { createBrowserRouter, RouterProvider } from "react-router";
import { EstimatePage } from "@/pages/EstimatePage";
import { RegistratiPage } from "@/routes/RegistratiPage";
import { AccediPage } from "@/routes/AccediPage";
import { PasswordDimenticataPage } from "@/routes/PasswordDimenticataPage";
import { ReimpostaPasswordPage } from "@/routes/ReimpostaPasswordPage";

const router = createBrowserRouter([
  { path: "/", element: <EstimatePage /> },
  { path: "/registrati", element: <RegistratiPage /> },
  { path: "/accedi", element: <AccediPage /> },
  { path: "/password-dimenticata", element: <PasswordDimenticataPage /> },
  { path: "/reimposta-password", element: <ReimpostaPasswordPage /> },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
