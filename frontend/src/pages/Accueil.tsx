import { motion, useReducedMotion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useChildren } from "../api/hooks";
import { Avatar } from "../components/Avatar";
import { Chaty } from "../components/Chaty";
import { useAppStore } from "../store/useAppStore";

export default function Accueil() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const selectChild = useAppStore((s) => s.selectChild);
  const { data: children, isLoading } = useChildren();

  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col items-center gap-6 px-4 py-8">
      <Chaty mood="wave" size={150} />
      <div className="text-center">
        <h1 className="text-4xl font-bold">{t("home.title")}</h1>
        <p className="mt-2 text-lg">{t("home.subtitle")}</p>
      </div>

      {isLoading && <p>{t("common.loading")}</p>}
      {children?.length === 0 && <p className="text-center">{t("home.empty")}</p>}

      <ul className="grid w-full grid-cols-2 gap-4 sm:grid-cols-3">
        {children?.map((child, i) => (
          <motion.li
            key={child.id}
            initial={reduce ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08, type: "spring", stiffness: 300, damping: 20 }}
          >
            <button
              type="button"
              onClick={() => {
                selectChild(child.id, child.lang);
                navigate("/chat");
              }}
              className="flex w-full flex-col items-center gap-2 rounded-3xl bg-white p-5 shadow-[0_6px_0_rgba(36,50,74,0.08)] transition hover:-translate-y-1 active:translate-y-0"
            >
              <Avatar emoji={child.avatar} size="lg" />
              <span className="text-xl font-semibold">{child.first_name}</span>
              <span className="text-sm">{t("age", { count: child.age })}</span>
            </button>
          </motion.li>
        ))}
      </ul>

      <Link
        to="/parent"
        className="mt-auto flex min-h-12 items-center gap-2 rounded-full px-4 font-semibold underline-offset-4 hover:underline"
      >
        <span aria-hidden="true">🔐</span>
        {t("home.parent")}
      </Link>
    </main>
  );
}
