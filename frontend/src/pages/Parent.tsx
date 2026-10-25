import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  useAlerts,
  useChildren,
  useDeleteChild,
  useDeleteChildData,
  useFeedback,
  useHistory,
  useSaveChild,
  useSummary,
  useVerifyPin,
} from "../api/hooks";
import {
  ACTIONS,
  INTERESTS,
  NEEDS,
  SEXES,
  type CautionLevel,
  type Child,
  type ChildInput,
  type HistoryItem,
  type Lang,
  type Sex,
  type Topic,
} from "../api/types";
import { Avatar } from "../components/Avatar";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { PinPad } from "../components/PinPad";
import { birthDateBounds } from "../lib/age";
import { AVATARS } from "../lib/avatars";
import { useAppStore } from "../store/useAppStore";

const GRADES = Array.from({ length: 9 }, (_, i) => `${i + 1}e_annee`);
const fieldClass = "min-h-12 w-full rounded-2xl border-2 border-encre/15 bg-white px-3";

const emptyChild: ChildInput = {
  first_name: "",
  avatar: AVATARS[0],
  birth_date: "",
  sex: "non_precise",
  grade: "3e_annee",
  lang: "fr",
  caution_level: "standard",
  interests: [],
  needs: [],
};

function toInput(child: Child): ChildInput {
  const input: Partial<Child> = { ...child };
  delete input.id;
  delete input.age;
  return input as ChildInput;
}

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function ChildForm({
  initial,
  onSubmit,
  onCancel,
  saving,
}: {
  initial: ChildInput;
  onSubmit: (input: ChildInput) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState(initial);
  const set = <K extends keyof ChildInput>(key: K, value: ChildInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));
  const bounds = birthDateBounds();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (form.first_name.trim()) onSubmit({ ...form, first_name: form.first_name.trim() });
  };

  return (
    <form onSubmit={submit} className="mt-3 grid gap-3 sm:grid-cols-2">
      <label className="flex flex-col gap-1">
        {t("parent.firstName")}
        <input
          required
          maxLength={30}
          value={form.first_name}
          onChange={(e) => set("first_name", e.target.value)}
          className={fieldClass}
        />
      </label>
      <label className="flex flex-col gap-1">
        {t("parent.birthDate")}
        <input
          type="date"
          required
          min={bounds.min}
          max={bounds.max}
          value={form.birth_date}
          onChange={(e) => set("birth_date", e.target.value)}
          className={fieldClass}
        />
      </label>
      <div className="flex flex-col gap-1">
        <label htmlFor="child-sex">{t("parent.sex")}</label>
        <select
          id="child-sex"
          value={form.sex}
          onChange={(e) => set("sex", e.target.value as Sex)}
          className={fieldClass}
          aria-describedby="sex-help"
        >
          {SEXES.map((s) => (
            <option key={s} value={s}>
              {t(`parent.sexes.${s}`)}
            </option>
          ))}
        </select>
        <span id="sex-help" className="text-sm text-encre/80">
          {t("parent.sexHelp")}
        </span>
      </div>
      <label className="flex flex-col gap-1">
        {t("parent.grade")}
        <select
          value={form.grade}
          onChange={(e) => set("grade", e.target.value)}
          className={fieldClass}
        >
          {GRADES.map((g) => (
            <option key={g} value={g}>
              {t(`grades.${g}`)}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1">
        {t("parent.lang")}
        <select
          value={form.lang}
          onChange={(e) => set("lang", e.target.value as Lang)}
          className={fieldClass}
        >
          <option value="fr">{t("languages.fr")}</option>
          <option value="ar">{t("languages.ar")}</option>
        </select>
      </label>
      <label className="flex flex-col gap-1">
        {t("parent.caution")}
        <select
          value={form.caution_level}
          onChange={(e) => set("caution_level", e.target.value as CautionLevel)}
          className={fieldClass}
        >
          <option value="standard">{t("parent.cautionLevels.standard")}</option>
          <option value="renforce">{t("parent.cautionLevels.renforce")}</option>
        </select>
      </label>
      <fieldset className="flex flex-col gap-1">
        <legend>{t("parent.avatar")}</legend>
        <div className="flex flex-wrap gap-1">
          {AVATARS.map((a) => (
            <button
              key={a}
              type="button"
              aria-pressed={form.avatar === a}
              onClick={() => set("avatar", a)}
              className={`rounded-full border-2 p-0.5 ${form.avatar === a ? "border-encre" : "border-transparent"}`}
            >
              <Avatar emoji={a} />
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="flex flex-col gap-2 sm:col-span-2">
        <legend>{t("parent.interests")}</legend>
        <p className="text-sm text-encre/80">{t("parent.interestsHelp")}</p>
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map((i) => (
            <button
              key={i}
              type="button"
              aria-pressed={form.interests.includes(i)}
              onClick={() => set("interests", toggle(form.interests, i))}
              className={`min-h-12 rounded-full border-2 px-4 font-semibold ${
                form.interests.includes(i) ? "border-encre bg-soleil" : "border-encre/15 bg-white"
              }`}
            >
              {form.interests.includes(i) && "✓ "}
              {t(`interests.${i}`)}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="flex flex-col gap-2 sm:col-span-2">
        <legend>{t("parent.needs")}</legend>
        <p className="text-sm text-encre/80">🔒 {t("parent.needsHelp")}</p>
        {NEEDS.map((n) => (
          <label key={n} className="flex min-h-12 cursor-pointer items-center gap-3">
            <input
              type="checkbox"
              checked={form.needs.includes(n)}
              onChange={() => set("needs", toggle(form.needs, n))}
              className="h-6 w-6 shrink-0 accent-ciel-fonce"
            />
            <span>
              <span className="font-semibold">{t(`parent.needsList.${n}.name`)}</span>
              <span className="text-sm text-encre/80"> — {t(`parent.needsList.${n}.desc`)}</span>
            </span>
          </label>
        ))}
      </fieldset>
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" disabled={saving}>
          {t("parent.save")}
        </Button>
        <Button variant="soft" onClick={onCancel}>
          {t("parent.cancel")}
        </Button>
      </div>
    </form>
  );
}

function ChildrenSection({ children }: { children: Child[] }) {
  const { t } = useTranslation();
  const save = useSaveChild();
  const remove = useDeleteChild();
  const [editing, setEditing] = useState<string | "new" | null>(null);

  const submit = (input: ChildInput, id?: string) =>
    save.mutate({ id, input }, { onSuccess: () => setEditing(null) });

  return (
    <Card aria-labelledby="p-children">
      <h2 id="p-children" className="text-xl font-semibold">
        {t("parent.children")}
      </h2>
      <ul className="mt-3 flex flex-col gap-3">
        {children.map((c) => (
          <li key={c.id} className="rounded-2xl bg-creme p-3">
            <div className="flex flex-wrap items-center gap-3">
              <Avatar emoji={c.avatar} />
              <span className="flex-1">
                <span className="block font-semibold">{c.first_name}</span>
                <span className="text-sm">
                  {t("age", { count: c.age })} · {t(`parent.sexes.${c.sex}`)} ·{" "}
                  {t(`grades.${c.grade}`)} · {t(`languages.${c.lang}`)}
                </span>
              </span>
              <Button variant="soft" className="text-sm" onClick={() => setEditing(c.id)}>
                {t("parent.edit")}
              </Button>
              <Button
                variant="soft"
                className="text-sm"
                onClick={() => {
                  if (window.confirm(t("parent.confirmRemoveChild", { name: c.first_name })))
                    remove.mutate(c.id);
                }}
              >
                {t("parent.remove")}
              </Button>
            </div>
            {editing === c.id && (
              <ChildForm
                initial={toInput(c)}
                saving={save.isPending}
                onSubmit={(input) => submit(input, c.id)}
                onCancel={() => setEditing(null)}
              />
            )}
          </li>
        ))}
      </ul>
      {save.isError && (
        <p role="alert" className="mt-3 font-semibold">
          ⚠️ {t("parent.saveError")}
        </p>
      )}
      {editing === "new" ? (
        <ChildForm
          initial={emptyChild}
          saving={save.isPending}
          onSubmit={(input) => submit(input)}
          onCancel={() => setEditing(null)}
        />
      ) : (
        <Button variant="secondary" className="mt-3" onClick={() => setEditing("new")}>
          ➕ {t("parent.addChild")}
        </Button>
      )}
    </Card>
  );
}

function FeedbackRow({ item }: { item: HistoryItem }) {
  const { t } = useTranslation();
  const feedback = useFeedback();
  const [comment, setComment] = useState("");

  return (
    <li className="rounded-2xl bg-creme p-3">
      <p className="font-semibold">{item.question}</p>
      <p className="mt-1 text-sm">{item.answer}</p>
      <p className="mt-1 text-sm text-encre/80">{t(`parent.actions.${item.action}`)}</p>
      {feedback.isSuccess ? (
        <p className="mt-2 text-sm font-semibold">✓ {t("parent.feedbackThanks")}</p>
      ) : (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t("parent.feedbackComment")}
            aria-label={t("parent.feedbackComment")}
            className={`${fieldClass} flex-1`}
          />
          {(["up", "down"] as const).map((rating) => (
            <Button
              key={rating}
              variant="soft"
              aria-label={t(rating === "up" ? "parent.feedbackUp" : "parent.feedbackDown")}
              disabled={feedback.isPending}
              onClick={() =>
                feedback.mutate({
                  message_id: item.message_id,
                  rating,
                  comment: comment || undefined,
                })
              }
            >
              {rating === "up" ? "👍" : "👎"}
            </Button>
          ))}
        </div>
      )}
    </li>
  );
}

function ChildActivity({ child }: { child: Child }) {
  const { t } = useTranslation();
  const { data: summary } = useSummary(child.id);
  const { data: history } = useHistory(child.id);
  const deleteData = useDeleteChildData();

  return (
    <>
      <Card aria-labelledby="p-summary">
        <h2 id="p-summary" className="text-xl font-semibold">
          {t("parent.summary")}
        </h2>
        {summary && (
          <dl className="mt-3 grid gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-sm">{t("parent.totalQuestions")}</dt>
              <dd className="text-3xl font-bold">{summary.total_questions}</dd>
            </div>
            <div>
              <dt className="text-sm">{t("parent.byTopic")}</dt>
              <dd>
                <ul>
                  {Object.entries(summary.by_topic).map(([topic, n]) => (
                    <li key={topic}>
                      {t(`topics.${topic as Topic}`)} : {n}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
            <div>
              <dt className="text-sm">{t("parent.byAction")}</dt>
              <dd>
                <ul>
                  {ACTIONS.map((a) => (
                    <li key={a}>
                      {t(`parent.actions.${a}`)} : {summary.by_action[a]}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          </dl>
        )}
      </Card>

      <Card aria-labelledby="p-recent">
        <h2 id="p-recent" className="text-xl font-semibold">
          {t("parent.recent")}
        </h2>
        {history?.length === 0 && <p className="mt-2">{t("parent.noHistory")}</p>}
        <ul className="mt-3 flex flex-col gap-3">
          {history?.slice(0, 10).map((item) => (
            <FeedbackRow key={item.message_id} item={item} />
          ))}
        </ul>
        {deleteData.isSuccess ? (
          <p className="mt-3 font-semibold">✓ {t("parent.deleted")}</p>
        ) : (
          <Button
            variant="danger"
            className="mt-4"
            disabled={deleteData.isPending}
            onClick={() => {
              if (window.confirm(t("parent.deleteConfirm", { name: child.first_name })))
                deleteData.mutate(child.id);
            }}
          >
            🗑️ {t("parent.deleteData", { name: child.first_name })}
          </Button>
        )}
      </Card>
    </>
  );
}

function Dashboard() {
  const { t } = useTranslation();
  const lock = useAppStore((s) => s.setParentUnlocked);
  const logout = useAppStore((s) => s.logout);
  const { data: children = [] } = useChildren();
  const { data: alerts = [] } = useAlerts(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = children.find((c) => c.id === selectedId) ?? children[0];
  const nameOf = (id: string) => children.find((c) => c.id === id)?.first_name ?? "";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-3xl font-bold">{t("parent.title")}</h1>
        <div className="flex flex-wrap gap-2">
          <Button variant="soft" onClick={() => lock(false)}>
            🔒 {t("parent.lock")}
          </Button>
          <Button variant="soft" onClick={logout}>
            {t("parent.logout")}
          </Button>
        </div>
      </div>

      <Card aria-labelledby="p-alerts">
        <h2 id="p-alerts" className="text-xl font-semibold">
          {t("parent.alerts")} {alerts.length > 0 && `(${alerts.length})`}
        </h2>
        {alerts.length === 0 && <p className="mt-2">{t("parent.noAlerts")}</p>}
        <ul className="mt-3 flex flex-col gap-2">
          {alerts.map((a) => (
            <li key={a.id} className="rounded-2xl border-2 border-corail bg-creme p-3">
              <span aria-hidden="true">🔔 </span>
              {t("parent.alertText", { name: nameOf(a.child_id), question: a.question })}
            </li>
          ))}
        </ul>
      </Card>

      <ChildrenSection children={children} />

      {selected && (
        <>
          <label className="flex flex-col gap-1 font-semibold">
            {t("parent.child")}
            <select
              value={selected.id}
              onChange={(e) => setSelectedId(e.target.value)}
              className={fieldClass}
            >
              {children.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.first_name}
                </option>
              ))}
            </select>
          </label>
          <ChildActivity key={selected.id} child={selected} />
        </>
      )}
    </div>
  );
}

export default function Parent() {
  const { t } = useTranslation();
  const unlocked = useAppStore((s) => s.parentUnlocked);
  const setUnlocked = useAppStore((s) => s.setParentUnlocked);
  const verify = useVerifyPin();

  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col gap-4 px-4 py-6">
      <Link to="/" className="flex min-h-12 items-center gap-2 self-start font-semibold">
        <span aria-hidden="true" className="inline-block rtl:rotate-180">
          ←
        </span>
        {t("common.back")}
      </Link>
      {unlocked ? (
        <Dashboard />
      ) : (
        <div className="flex flex-col items-center gap-4 pt-6">
          <h1 className="text-3xl font-bold">{t("parent.title")}</h1>
          <p className="text-lg">{t("parent.pinPrompt")}</p>
          <PinPad
            error={verify.isError}
            disabled={verify.isPending}
            onComplete={(pin) => verify.mutate(pin, { onSuccess: () => setUnlocked(true) })}
          />
          <p className="text-sm text-encre/80">{t("parent.pinHint")}</p>
        </div>
      )}
    </main>
  );
}
