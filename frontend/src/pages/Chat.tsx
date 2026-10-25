import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useChildren, useImage, useSendMessage, useSimplify } from "../api/hooks";
import { ANSWER_ACTIONS, type MessageResponse } from "../api/types";
import { Bubble } from "../components/Bubble";
import { Button } from "../components/Button";
import { Chaty, type ChatyMood } from "../components/Chaty";
import { playPop } from "../lib/sound";
import { useAppStore } from "../store/useAppStore";

interface Exchange {
  question: string;
  response: MessageResponse;
}

function moodFor(pending: boolean, last?: MessageResponse): ChatyMood {
  if (pending) return "think";
  if (!last) return "wave";
  return ANSWER_ACTIONS.includes(last.action) ? "wonder" : "reassure";
}

function Illustration({ childId, messageId }: { childId: string; messageId: string }) {
  const { t } = useTranslation();
  const { data } = useImage(childId, messageId, true);
  if (!data || data.status === "pending") {
    return (
      <p className="mt-3 flex items-center gap-2 text-sm" role="status">
        <span aria-hidden="true">🎨</span>
        {t("chat.imageLoading")}
      </p>
    );
  }
  if (data.status !== "ready" || !data.url) return null;
  return (
    <motion.img
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      src={data.url}
      alt={t("chat.imageAlt")}
      className="mt-3 w-full max-w-xs rounded-2xl"
    />
  );
}

function ThinkingBubble() {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  return (
    <Bubble from="chaty">
      <span role="status" className="flex items-center gap-2">
        {t("chat.thinking")}
        <span aria-hidden="true" className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="h-2 w-2 rounded-full bg-ciel"
              animate={reduce ? undefined : { y: [0, -5, 0] }}
              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
            />
          ))}
        </span>
      </span>
    </Bubble>
  );
}

export default function Chat() {
  const { t } = useTranslation();
  const childId = useAppStore((s) => s.currentChildId)!;
  const lang = useAppStore((s) => s.lang);
  const sounds = useAppStore((s) => s.sounds);
  const child = useChildren().data?.find((c) => c.id === childId);
  const send = useSendMessage(childId);
  const simplify = useSimplify(childId);
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  const pending = send.isPending || simplify.isPending;
  const last = exchanges.at(-1)?.response;
  const suggestions = t("chat.suggestions", { returnObjects: true }) as string[];

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [exchanges.length, pending]);

  const addExchange = (exchange: Exchange) => {
    setExchanges((prev) => [...prev, exchange]);
    if (sounds) playPop();
  };

  const ask = (text: string) => {
    const q = text.trim();
    if (!q || pending) return;
    setQuestion("");
    send.mutate(
      { question: q, lang },
      { onSuccess: (response) => addExchange({ question: q, response }) },
    );
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    ask(question);
  };

  const askSimpler = (ex: Exchange) =>
    simplify.mutate(ex.response.message_id, {
      onSuccess: (response) => addExchange({ question: t("chat.simpler"), response }),
    });

  return (
    <div className="flex flex-1 flex-col gap-4">
      <div className="flex justify-center">
        <Chaty mood={moodFor(pending, last)} size={110} />
      </div>

      <div className="flex flex-col gap-3" aria-live="polite">
        <Bubble from="chaty">{t("chat.greeting", { name: child?.first_name ?? "" })}</Bubble>

        {exchanges.map((ex, i) => {
          const answered = ANSWER_ACTIONS.includes(ex.response.action);
          const src = ex.response.rag_source;
          return (
            <div key={`${ex.response.message_id}-${i}`} className="flex flex-col gap-3">
              <Bubble from="child">{ex.question}</Bubble>
              <Bubble from={answered ? "chaty" : "gentle"}>
                <p>{ex.response.text}</p>
                {!answered && (
                  <p className="mt-2 text-sm font-semibold">💛 {t("chat.gentleHint")}</p>
                )}
                {src && (
                  <p className="mt-2 text-sm text-encre/80">
                    📘 {t("chat.source", { book: src.book, chapter: src.chapter })}
                  </p>
                )}
                {ex.response.image_status !== "none" && (
                  <Illustration childId={childId} messageId={ex.response.message_id} />
                )}
                {answered && i === exchanges.length - 1 && (
                  <Button
                    variant="soft"
                    className="mt-3 text-sm"
                    disabled={pending}
                    onClick={() => askSimpler(ex)}
                  >
                    🐣 {t("chat.simpler")}
                  </Button>
                )}
              </Bubble>
            </div>
          );
        })}

        {pending && <ThinkingBubble />}
        {(send.isError || simplify.isError) && <Bubble from="gentle">{t("chat.error")}</Bubble>}
        <div ref={endRef} />
      </div>

      {exchanges.length === 0 && (
        <section aria-labelledby="suggestions-title" className="mt-2">
          <h2 id="suggestions-title" className="mb-2 font-semibold">
            {t("chat.suggestionsTitle")}
          </h2>
          <ul className="flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <li key={s}>
                <Button
                  variant="soft"
                  className="text-sm"
                  onClick={() => ask(s)}
                  disabled={pending}
                >
                  {s}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <form
        onSubmit={onSubmit}
        className="sticky bottom-24 mt-auto flex gap-2 rounded-full bg-white p-2 shadow-lg md:bottom-4"
      >
        <label htmlFor="question" className="sr-only">
          {t("chat.inputLabel")}
        </label>
        <input
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("chat.placeholder")}
          autoComplete="off"
          maxLength={500}
          className="min-h-12 min-w-0 flex-1 rounded-full bg-creme px-4 text-encre outline-none focus-visible:ring-2 focus-visible:ring-ciel-fonce"
        />
        <Button type="submit" className="shrink-0" disabled={!question.trim() || pending}>
          {t("chat.send")}
        </Button>
      </form>
    </div>
  );
}
