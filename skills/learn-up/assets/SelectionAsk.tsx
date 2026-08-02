import { useEffect, useRef, useState, type RefObject } from "react";
import type { AskOutcome, FaqEntry } from "../api/types";

interface SelectionAskProps {
  containerRef: RefObject<HTMLElement | null>;
  onAsk: (
    selectedText: string,
    question: string,
    onDelta: (text: string) => void,
    useFullSources: boolean,
  ) => Promise<AskOutcome>;
  onAnswered: (entry: FaqEntry) => void;
}

interface TriggerState {
  x: number;
  y: number;
  text: string;
}

export default function SelectionAsk({
  containerRef,
  onAsk,
  onAnswered,
}: SelectionAskProps) {
  const [trigger, setTrigger] = useState<TriggerState | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [askingFullSources, setAskingFullSources] = useState(false);
  const [needsFullSourceConfirm, setNeedsFullSourceConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onSelectionChange() {
      if (panelOpen) return;
      const container = containerRef.current;
      const selection = window.getSelection();
      if (
        !container ||
        !selection ||
        selection.isCollapsed ||
        selection.rangeCount === 0
      ) {
        setTrigger(null);
        return;
      }
      const range = selection.getRangeAt(0);
      if (!container.contains(range.commonAncestorContainer)) {
        setTrigger(null);
        return;
      }
      const text = selection.toString().trim();
      if (!text) {
        setTrigger(null);
        return;
      }
      const rect = range.getBoundingClientRect();
      setTrigger({ x: rect.left + rect.width / 2, y: rect.top, text });
    }
    document.addEventListener("selectionchange", onSelectionChange);
    return () =>
      document.removeEventListener("selectionchange", onSelectionChange);
  }, [containerRef, panelOpen]);

  function openPanel() {
    setPanelOpen(true);
    setQuestion("");
    setStreamedAnswer("");
    setError(null);
    setNeedsFullSourceConfirm(false);
  }

  function closePanel() {
    setPanelOpen(false);
    setTrigger(null);
    window.getSelection()?.removeAllRanges();
  }

  async function runAsk(useFullSources: boolean) {
    if (!trigger || !question.trim()) return;
    setAsking(true);
    setAskingFullSources(useFullSources);
    setError(null);
    setStreamedAnswer("");
    setNeedsFullSourceConfirm(false);
    try {
      const outcome = await onAsk(
        trigger.text,
        question.trim(),
        (delta) => setStreamedAnswer((prev) => prev + delta),
        useFullSources,
      );
      if (outcome.type === "insufficient") {
        setStreamedAnswer("");
        if (useFullSources) {
          // Already searched everything available — nothing further to offer.
          setError(
            "No answer found, even after searching the topic's full source material.",
          );
        } else {
          setNeedsFullSourceConfirm(true);
        }
      } else {
        onAnswered(outcome.entry);
        closePanel();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAsking(false);
    }
  }

  if (!trigger) return null;

  if (!panelOpen) {
    return (
      <button
        type="button"
        className="selection-ask__trigger"
        style={{ left: trigger.x, top: trigger.y - 8 }}
        onMouseDown={(event) => event.preventDefault()}
        onClick={openPanel}
      >
        Ask about this
      </button>
    );
  }

  return (
    <div
      className="panel selection-ask__panel"
      style={{ left: trigger.x, top: trigger.y - 8 }}
      ref={panelRef}
    >
      <p className="selection-ask__quote">{trigger.text}</p>
      <div className="field">
        <label className="field__label" htmlFor="selection-ask-question">
          Your question
        </label>
        <textarea
          id="selection-ask-question"
          rows={2}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (!asking && question.trim()) void runAsk(false);
            }
          }}
          disabled={asking}
        />
      </div>
      {error && <div className="banner banner--error">{error}</div>}
      {streamedAnswer && (
        <div className="selection-ask__answer">{streamedAnswer}</div>
      )}
      {needsFullSourceConfirm ? (
        <>
          <p className="muted">
            This lesson alone doesn't have enough information to answer
            confidently. Search the whole topic's source material instead?
            That's slower and costs more, so it's not done by default.
          </p>
          <div className="selection-ask__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={closePanel}
            >
              Never mind
            </button>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => void runAsk(true)}
            >
              Search full topic sources
            </button>
          </div>
        </>
      ) : (
        <div className="selection-ask__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={closePanel}
            disabled={asking}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => void runAsk(false)}
            disabled={asking || !question.trim()}
          >
            {asking
              ? askingFullSources
                ? "Searching full topic sources…"
                : "Asking…"
              : "Ask"}
          </button>
        </div>
      )}
    </div>
  );
}
