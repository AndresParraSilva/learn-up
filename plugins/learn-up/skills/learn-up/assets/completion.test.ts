import { describe, expect, it } from "vitest";
import { completionState } from "./completion";

describe("completionState", () => {
  it("continues to the next item", () => {
    const next = { slug: "next-lesson", title: "Next lesson" };
    expect(completionState(next)).toEqual({ kind: "next", next });
  });
  it("recognizes an explicit final item", () => {
    expect(completionState(null)).toEqual({ kind: "last" });
  });
  it("requires reload for an old payload", () => {
    expect(completionState(undefined)).toEqual({ kind: "stale" });
  });
});
