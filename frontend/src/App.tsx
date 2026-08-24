import { EstimateForm } from "@/components/EstimateForm";

function App() {
  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[480px] flex-col gap-6 px-4 py-8 sm:max-w-[640px] sm:px-6 sm:py-12 lg:py-16">
      <div className="flex flex-col gap-2 text-center">
        <h1 className="text-lg font-semibold text-foreground">ristruttura-stima</h1>
        <p className="text-sm text-muted-foreground">
          Inserisci i dati per ottenere la tua stima gratuita. Bastano tre informazioni: città,
          superficie in m² e tipo di ristrutturazione. La stima è gratuita e non richiede
          registrazione.
        </p>
      </div>
      <EstimateForm onSubmit={() => {}} />
    </main>
  );
}

export default App;
