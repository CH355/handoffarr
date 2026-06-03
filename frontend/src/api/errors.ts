/* Foundation §10.3 — normalize backend error envelope to a single shape so
   feature code reacts to one ApiError type. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | undefined;
  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}
