export type Entity = {
  id: number;
  active: boolean;
  name?: string;
  [key: string]: any;
};
export type Data = { revision: number; [key: string]: Entity[] | number };
export type Allocation = { employee_id: number; duty_id: number; date: string };
export type Finding = {
  code: string;
  date: string;
  duty_id: number | null;
  employee_id: number | null;
  brand: string | null;
  process: string | null;
  required: number | null;
  eligible: number | null;
  actual: number | null;
  severity: "hard" | "soft";
  reason: string;
  suggestion: string;
};
export type Roster = {
  id: number;
  month: string;
  revision: number;
  status: string;
  stale: boolean;
  days: string[];
  horizon: string[];
  allocations: Allocation[];
  statuses: { employee_id: number; date: string; status: string }[];
  findings: Finding[];
  publishable: boolean;
  solver_status: string;
  solver_name: string;
  repair_scope?: { dates: string[]; expanded: boolean; reason: string };
  diagnostic: boolean;
  summary: {
    hard: number;
    soft: number;
    required_slots: number;
    covered_slots: number;
  };
  boundary_note: string;
};
export type Preview = {
  change_id: number;
  affected: Allocation[];
  before_findings: Finding[];
  candidates: {
    employee_id: number;
    name: string;
    resulting_load: number;
    capacity: number;
    note: string;
  }[];
  diff: { added: Allocation[]; removed: Allocation[] };
  result: Roster;
};
export const rows = (data: Data, key: string): Entity[] =>
  data[key] as Entity[];
export const nameOf = (data: Data, key: string, id: number) =>
  rows(data, key).find((x) => x.id === id)?.name || `#${id}`;
export const dutyName = (data: Data, id: number) => {
  const d = rows(data, "duties").find((x) => x.id === id);
  return d
    ? `${nameOf(data, "brands", d.brand_id)} · ${nameOf(data, "processes", d.process_id)}`
    : `#${id}`;
};
export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method: method || (body ? "POST" : "GET"),
    headers: {
      "Content-Type": "application/json",
      "X-Manager-Token": sessionStorage.getItem("manager-token") || "",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const err = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail),
    );
  }
  return response.json();
}
