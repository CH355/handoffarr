/* executionReducer — frontend-implementation-spec-v1.md §6.7.
   Drives Recover Space lifecycle: idle → confirming → executing → succeeded
   | partial-fail | total-fail. Driven by TanStack mutation lifecycle, not
   independent timers. */

export type ExecutionStatus =
  | "idle"
  | "confirming"
  | "executing"
  | "succeeded"
  | "partial-fail"
  | "total-fail";

export interface ExecutionState {
  status: ExecutionStatus;
  errorMessage?: string;
  completedCount?: number;
  failedCount?: number;
  recoveredBytes?: number;
}

export type ExecutionAction =
  | { type: "request-confirm" }
  | { type: "cancel" }
  | { type: "start" }
  | {
      type: "success";
      payload: { completedCount: number; failedCount: number; recoveredBytes: number };
    }
  | { type: "fail"; payload: { message: string } }
  | { type: "reset" };

export const initialExecutionState: ExecutionState = { status: "idle" };

export function executionReducer(
  state: ExecutionState,
  action: ExecutionAction,
): ExecutionState {
  switch (action.type) {
    case "request-confirm":
      return { status: "confirming" };
    case "cancel":
      return { status: "idle" };
    case "start":
      return { ...state, status: "executing" };
    case "success": {
      const { completedCount, failedCount, recoveredBytes } = action.payload;
      const status: ExecutionStatus = failedCount > 0 ? "partial-fail" : "succeeded";
      return { status, completedCount, failedCount, recoveredBytes };
    }
    case "fail":
      return { status: "total-fail", errorMessage: action.payload.message };
    case "reset":
      return initialExecutionState;
    default:
      return state;
  }
}
