import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./api/client";
import "./App.css";

interface HealthDbResponse {
  status: string;
  listini: number;
}

function App() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["health-db"],
    queryFn: () => apiGet<HealthDbResponse>("/health/db"),
  });

  return (
    <main id="center">
      <h1>ristruttura-stima</h1>
      {isLoading && <p>Verifica connessione al database...</p>}
      {isError && (
        <p className="error">
          Errore di connessione: {error instanceof Error ? error.message : "sconosciuto"}
        </p>
      )}
      {data && (
        <p className="ok">
          Database connesso &mdash; {data.listini} listini
        </p>
      )}
    </main>
  );
}

export default App;
