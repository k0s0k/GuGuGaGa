import type {
  AppState,
  Capabilities,
  Detail,
  Problem,
  RunResult,
} from "./types";
let token = "";
let queue: Promise<unknown> = Promise.resolve();
async function request<T>(path: string, payload?: unknown): Promise<T> {
  const response = await fetch(
    "/api" + path,
    payload === undefined
      ? undefined
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CodeRecall-Token": token,
          },
          body: JSON.stringify(payload),
        },
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "操作失败，请重试");
  return data;
}
export async function bootstrap() {
  const result = await request<{
    problems: Problem[];
    categories: string[];
    state: AppState;
    capabilities: Capabilities;
    token: string;
  }>("/bootstrap");
  token = result.token;
  return result;
}
export const getProblem = (id: number) => request<Detail>("/problems/" + id);
export function action(payload: unknown): Promise<AppState> {
  const next = queue
    .catch(() => {})
    .then(() => request<AppState>("/action", payload));
  queue = next;
  return next;
}
export const runCode = (payload: unknown) =>
  request<RunResult>("/run", payload);
