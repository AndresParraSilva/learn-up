import type { NextItemOut } from "../api/types";

export type CompletionState =
  | { kind: "next"; next: NextItemOut }
  | { kind: "last" }
  | { kind: "stale" };

export function completionState(
  next: NextItemOut | null | undefined,
): CompletionState {
  if (next) return { kind: "next", next };
  return next === null ? { kind: "last" } : { kind: "stale" };
}
