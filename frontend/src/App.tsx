import { createBrowserRouter, RouterProvider } from "react-router";
import { EstimatePage } from "@/pages/EstimatePage";
import { RegistratiPage } from "@/routes/RegistratiPage";
import { AccediPage } from "@/routes/AccediPage";

const router = createBrowserRouter([
  { path: "/", element: <EstimatePage /> },
  { path: "/registrati", element: <RegistratiPage /> },
  { path: "/accedi", element: <AccediPage /> },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
