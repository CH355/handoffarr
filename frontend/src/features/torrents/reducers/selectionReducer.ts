export interface SelectionState {
  selected: ReadonlySet<string>;
}

export type SelectionAction =
  | { type: "toggle"; hash: string }
  | { type: "select-visible"; hashes: string[] }
  | { type: "clear-visible"; hashes: string[] }
  | { type: "clear" }
  | { type: "prune"; hashes: string[] };

export const initialSelectionState: SelectionState = {
  selected: new Set<string>(),
};

export function selectionReducer(
  state: SelectionState,
  action: SelectionAction,
): SelectionState {
  if (action.type === "clear") return initialSelectionState;

  const selected = new Set(state.selected);
  if (action.type === "toggle") {
    if (selected.has(action.hash)) selected.delete(action.hash);
    else selected.add(action.hash);
  } else if (action.type === "select-visible") {
    action.hashes.forEach((hash) => selected.add(hash));
  } else if (action.type === "clear-visible") {
    action.hashes.forEach((hash) => selected.delete(hash));
  } else {
    const current = new Set(action.hashes);
    selected.forEach((hash) => {
      if (!current.has(hash)) selected.delete(hash);
    });
  }

  return { selected };
}
