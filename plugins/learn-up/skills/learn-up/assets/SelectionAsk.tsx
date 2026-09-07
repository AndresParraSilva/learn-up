import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import type { AskOutcome, FaqEntry } from "../api/types";

const VIEWPORT_MARGIN = 12;
const PANEL_GAP = 8;

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
  top: number;
  bottom: number;
  text: string;
}

interface PanelLayout {
  left: number;
  top: number;
  maxWidth: number;
  maxHeight: number;
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
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
  const [panelLayout, setPanelLayout] = useState<PanelLayout | null>(null);
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
      setTrigger({
        x: rect.left + rect.width / 2,
        top: rect.top,
        bottom: rect.bottom,
        text,
      });
    }
    document.addEventListener("selectionchange", onSelectionChange);
    return () =>
      document.removeEventListener("selectionchange", onSelectionChange);
  }, [containerRef, panelOpen]);

  useLayoutEffect(() => {
    if (!panelOpen || !trigger) return;

    const panel = panelRef.current;
    if (!panel) {
      throw new Error("SelectionAsk panel is open but not mounted");
    }

    function positionPanel() {
      const visualViewport = window.visualViewport;
      const viewportLeft = visualViewport?.offsetLeft ?? 0;
      const viewportTop = visualViewport?.offsetTop ?? 0;
      const viewportWidth = visualViewport?.width ?? window.innerWidth;
      const viewportHeight = visualViewport?.height ?? window.innerHeight;
      const viewportRight = viewportLeft + viewportWidth;
      const viewportBottom = viewportTop + viewportHeight;
      const maxWidth = Math.max(0, viewportWidth - VIEWPORT_MARGIN * 2);
      const maxHeight = Math.max(0, viewportHeight - VIEWPORT_MARGIN * 2);
      const rect = panel.getBoundingClientRect();
      const panelWidth = Math.min(rect.width, maxWidth);
      const panelHeight = Math.min(rect.height, maxHeight);
      const maximumLeft = Math.max(
        viewportLeft + VIEWPORT_MARGIN,
        viewportRight - panelWidth - VIEWPORT_MARGIN,
      );
      const maximumTop = Math.max(
        viewportTop + VIEWPORT_MARGIN,
        viewportBottom - panelHeight - VIEWPORT_MARGIN,
      );
      const left = clamp(
        trigger.x - panelWidth / 2,
        viewportLeft + VIEWPORT_MARGIN,
        maximumLeft,
      );
      const belowSelection = trigger.bottom + PANEL_GAP;
      const aboveSelection = trigger.top - panelHeight - PANEL_GAP;
      const preferredTop =
        belowSelection + panelHeight <= viewportBottom - VIEWPORT_MARGIN
          ? belowSelection
          : aboveSelection;
      const top = clamp(
        preferredTop,
        viewportTop + VIEWPORT_MARGIN,
        maximumTop,
      );
      const nextLayout = { left, top, maxWidth, maxHeight };

      setPanelLayout((current) =>
        current &&
        current.left === nextLayout.left &&
        current.top === nextLayout.top &&
        current.maxWidth === nextLayout.maxWidth &&
        current.maxHeight === nextLayout.maxHeight
          ? current
          : nextLayout,
      );
    }

    positionPanel();
    const resizeObserver = new ResizeObserver(positionPanel);
    resizeObserver.observe(panel);
    window.addEventListener("resize", positionPanel);
    window.visualViewport?.addEventListener("resize", positionPanel);
    window.visualViewport?.addEventListener("scroll", positionPanel);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", positionPanel);
      window.visualViewport?.removeEventListener("resize", positionPanel);
      window.visualViewport?.removeEventListener("scroll", positionPanel);
    };
  }, [panelOpen, trigger]);

  function openPanel() {
    setPanelLayout(null);
    setPanelOpen(true);
    setQuestion("");
    setStreamedAnswer("");
    setError(null);
    setNeedsFullSourceConfirm(false);
  }

  function closePanel() {
    setPanelLayout(null);
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
        style={{ left: trigger.x, top: trigger.top - PANEL_GAP }}
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
      style={{
        left: panelLayout?.left ?? 0,
        top: panelLayout?.top ?? 0,
        maxWidth: panelLayout?.maxWidth,
        maxHeight: panelLayout?.maxHeight,
        visibility: panelLayout ? "visible" : "hidden",
      }}
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
