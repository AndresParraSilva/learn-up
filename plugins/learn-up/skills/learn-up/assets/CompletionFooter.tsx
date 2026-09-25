import { Link } from "react-router-dom";
import type { NextItemOut } from "../api/types";
import type { BackNavState } from "../lib/backNav";
import { completionState } from "../lib/completion";

interface CompletionFooterProps {
  statusLabel: string;
  next: NextItemOut | null | undefined;
  hrefFor: (next: NextItemOut) => string;
  nextLabel: string;
  lastLabel: string;
  backState?: BackNavState;
}

export default function CompletionFooter({
  statusLabel,
  next,
  hrefFor,
  nextLabel,
  lastLabel,
  backState,
}: CompletionFooterProps) {
  const state = completionState(next);
  return (
    <div className="completion-footer">
      <span className="chip chip--moss">{statusLabel}</span>
      {state.kind === "next" && (
        <div className="completion-footer__next">
          <span className="completion-footer__next-title">
            Up next: {state.next.title}
          </span>
          <Link
            to={hrefFor(state.next)}
            state={backState}
            className="btn btn--primary"
          >
            {nextLabel} &rarr;
          </Link>
        </div>
      )}
      {state.kind === "last" && (
        <span className="completion-footer__next-title">{lastLabel}</span>
      )}
      {state.kind === "stale" && (
        <span className="banner banner--error completion-footer__stale">
          This page was loaded before the app knew what comes next — reload to
          continue.
        </span>
      )}
    </div>
  );
}
