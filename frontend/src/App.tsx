import { createBrowserRouter, RouterProvider } from "react-router";
import { routes } from "@/routes";
import { tracciaPagina } from "@/lib/tracciamento";

const router = createBrowserRouter(routes);

// Pagine viste per le statistiche (solo con il consenso: vedi lib/tracciamento).
let ultimoPercorso = "";
router.subscribe((stato) => {
  const percorso = stato.location.pathname + stato.location.search;
  if (stato.navigation.state === "idle" && percorso !== ultimoPercorso) {
    ultimoPercorso = percorso;
    tracciaPagina(percorso);
  }
});

function App() {
  return <RouterProvider router={router} />;
}

export default App;
