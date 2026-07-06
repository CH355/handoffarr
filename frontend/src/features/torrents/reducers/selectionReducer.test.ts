import { describe, expect, it } from "vitest";
import {
  initialSelectionState,
  selectionReducer,
} from "./selectionReducer";

describe("selectionReducer", () => {
  it("toggles an individual torrent", () => {
    const selected = selectionReducer(initialSelectionState, {
      type: "toggle",
      hash: "abc",
    });
    expect([...selected.selected]).toEqual(["abc"]);

    const cleared = selectionReducer(selected, {
      type: "toggle",
      hash: "abc",
    });
    expect(cleared.selected.size).toBe(0);
  });

  it("selects and clears all visible torrents without changing hidden selections", () => {
    const hidden = selectionReducer(initialSelectionState, {
      type: "toggle",
      hash: "hidden",
    });
    const selected = selectionReducer(hidden, {
      type: "select-visible",
      hashes: ["a", "b"],
    });
    expect([...selected.selected].sort()).toEqual(["a", "b", "hidden"]);

    const visibleCleared = selectionReducer(selected, {
      type: "clear-visible",
      hashes: ["a", "b"],
    });
    expect([...visibleCleared.selected]).toEqual(["hidden"]);
  });

  it("prunes torrents no longer in the snapshot", () => {
    const selected = {
      selected: new Set(["current", "removed"]),
    };
    const pruned = selectionReducer(selected, {
      type: "prune",
      hashes: ["current", "other"],
    });
    expect([...pruned.selected]).toEqual(["current"]);
  });
});
