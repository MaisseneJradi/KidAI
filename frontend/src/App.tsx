import { useEffect, useState } from "react";

type Status = "loading" | "ok" | "error";

// Page provisoire de l'étape 0 : remplacée par la vraie interface à l'étape 1.
export default function App() {
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    fetch("/health")
      .then((res) => setStatus(res.ok ? "ok" : "error"))
      .catch(() => setStatus("error"));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-amber-50 text-slate-800">
      <h1 className="text-5xl font-bold">KidAI</h1>
      <p role="status" className="text-xl">
        {status === "loading" && "…"}
        {status === "ok" && "backend OK"}
        {status === "error" && "backend indisponible"}
      </p>
    </main>
  );
}
