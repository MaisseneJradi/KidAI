import { useTranslation } from "react-i18next";
import { Link, Navigate, NavLink, Outlet } from "react-router-dom";
import { useChildren } from "../api/hooks";
import { useAppStore } from "../store/useAppStore";
import { Avatar } from "./Avatar";

const tabs = [
  { to: "/chat", icon: "💬", key: "nav.chat" },
  { to: "/decouvertes", icon: "🗺️", key: "nav.discoveries" },
  { to: "/badges", icon: "🏅", key: "nav.badges" },
  { to: "/reglages", icon: "⚙️", key: "nav.settings" },
];

/** Cadre des écrans enfant : en-tête + barre de navigation (en bas sur téléphone, en haut sur ordinateur). */
export function ChildLayout() {
  const { t } = useTranslation();
  const childId = useAppStore((s) => s.currentChildId);
  const { data: children, isLoading } = useChildren();
  const child = children?.find((c) => c.id === childId);

  if (!childId || (!isLoading && !child)) return <Navigate to="/" replace />;

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col">
      <header className="flex items-center justify-between gap-3 px-4 py-3">
        <Link
          to="/"
          className="flex min-h-12 items-center gap-2 rounded-full pe-4 font-semibold hover:bg-white"
          aria-label={t("nav.switchProfile")}
        >
          {child && <Avatar emoji={child.avatar} />}
          <span>{child?.first_name}</span>
        </Link>
        <span className="text-xl font-bold text-ciel-fonce">{t("app.name")}</span>
      </header>

      <nav
        aria-label={t("nav.label")}
        className="fixed inset-x-0 bottom-0 z-10 border-t border-encre/10 bg-white md:static md:order-first md:border-0 md:bg-transparent"
      >
        <ul className="mx-auto flex max-w-3xl md:justify-center md:gap-2 md:pt-3">
          {tabs.map((tab) => (
            <li key={tab.to} className="min-w-0 flex-1 md:flex-none">
              <NavLink
                to={tab.to}
                className={({ isActive }) =>
                  `flex min-h-14 flex-col items-center justify-center rounded-2xl px-1 py-1 text-xs font-semibold sm:text-sm md:flex-row md:gap-2 md:px-3 md:text-base ${
                    isActive ? "bg-soleil" : "hover:bg-creme md:hover:bg-white"
                  }`
                }
              >
                <span aria-hidden="true" className="text-xl">
                  {tab.icon}
                </span>
                {t(tab.key)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <main className="flex flex-1 flex-col px-4 pb-28 md:pb-8">
        <Outlet />
      </main>
    </div>
  );
}
