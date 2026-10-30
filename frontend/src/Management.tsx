import { useState } from "react";
import { Data, Entity, rows, nameOf, dutyName, api } from "./api";
type Field = {
  key: string;
  label: string;
  type?: string;
  ref?: string;
  options?: string[];
  default?: unknown;
  optional?: boolean;
};
const common: Field[] = [
  { key: "active", label: "Active", type: "checkbox", default: true },
];
const config: Record<string, Field[]> = {
  employees: [
    { key: "name", label: "Full name" },
    { key: "pod_id", label: "Pod", ref: "pods" },
    {
      key: "capacity",
      label: "Daily workload capacity",
      type: "number",
      default: 8,
    },
    {
      key: "preferred_off",
      label: "Preferred off weekdays",
      type: "days",
      default: [6],
    },
    {
      key: "fixed_off",
      label: "Mandatory off weekdays",
      type: "days",
      default: [],
    },
    {
      key: "max_consecutive",
      label: "Maximum consecutive workdays",
      type: "number",
      default: 6,
    },
    {
      key: "weekly_rest",
      label: "Minimum rest days per week",
      type: "number",
      default: 1,
    },
  ],
  pods: [
    { key: "name", label: "Pod name" },
    {
      key: "lead_id",
      label: "Pod lead (must belong to pod)",
      ref: "employees",
      optional: true,
    },
  ],
  brands: [
    { key: "name", label: "Brand name" },
    {
      key: "calendar_id",
      label: "Default operating calendar",
      ref: "calendars",
    },
  ],
  processes: [{ key: "name", label: "Process name" }],
  calendars: [
    { key: "name", label: "Calendar name" },
    {
      key: "weekdays",
      label: "Operating weekdays",
      type: "days",
      default: [0, 1, 2, 3, 4, 5, 6],
    },
    {
      key: "holidays_off",
      label: "Exclude configured public holidays",
      type: "checkbox",
      default: false,
    },
  ],
  duties: [
    { key: "brand_id", label: "Brand", ref: "brands" },
    { key: "process_id", label: "Process", ref: "processes" },
    {
      key: "calendar_id",
      label: "Process calendar override",
      ref: "calendars",
      optional: true,
    },
    {
      key: "minimum",
      label: "Minimum distinct employees",
      type: "number",
      default: 1,
    },
    {
      key: "effort",
      label: "Workload units per employee",
      type: "number",
      default: 2,
    },
    {
      key: "start_minute",
      label: "Exclusive start minute (0–1439)",
      type: "number",
      optional: true,
    },
    {
      key: "end_minute",
      label: "Exclusive end minute (1–1440)",
      type: "number",
      optional: true,
    },
  ],
  assignments: [
    { key: "employee_id", label: "Employee", ref: "employees" },
    { key: "duty_id", label: "Brand / process", ref: "duties" },
    {
      key: "role",
      label: "Responsibility",
      options: ["primary", "backup"],
      default: "primary",
    },
    { key: "starts", label: "Eligible from", type: "date", optional: true },
    { key: "ends", label: "Eligible until", type: "date", optional: true },
  ],
  absences: [
    { key: "employee_id", label: "Employee", ref: "employees" },
    { key: "starts", label: "From", type: "date" },
    { key: "ends", label: "Until", type: "date" },
    {
      key: "kind",
      label: "Absence type",
      options: ["leave", "comp_off", "unavailable", "weekly_off"],
      default: "leave",
    },
    {
      key: "approved",
      label: "Approved (blocks scheduling)",
      type: "checkbox",
      default: true,
    },
    { key: "note", label: "Note", optional: true, default: "" },
  ],
  holidays: [
    { key: "name", label: "Holiday name" },
    { key: "date", label: "Date", type: "date" },
  ],
  overrides: [
    { key: "duty_id", label: "Brand / process", ref: "duties" },
    { key: "date", label: "Date", type: "date" },
    {
      key: "operating",
      label: "Operating on this date",
      type: "checkbox",
      default: true,
    },
    {
      key: "minimum",
      label: "Required employees on this date",
      type: "number",
      default: 1,
    },
  ],
};
export const labels: Record<string, string> = {
  employees: "Employees",
  pods: "Pods & leads",
  brands: "Brands",
  processes: "Processes",
  calendars: "Operating calendars",
  duties: "Brand processes",
  assignments: "Resource eligibility",
  absences: "Leave & availability",
  holidays: "Public holidays",
  overrides: "Daily staffing rules",
};
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export default function Management({
  data,
  onSaved,
  onError,
}: {
  data: Data;
  onSaved: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [table, setTable] = useState("employees");
  const [search, setSearch] = useState("");
  const [edit, setEdit] = useState<Record<string, any> | null>(null);
  const [saving, setSaving] = useState(false);
  const fields = [...config[table], ...common];
  function start(item?: Entity) {
    setEdit(
      item
        ? { ...item }
        : Object.fromEntries(
            fields.map((f) => [
              f.key,
              f.default ??
                (f.optional
                  ? null
                  : f.ref
                    ? (rows(data, f.ref).find((x) => x.active)?.id ?? null)
                    : ""),
            ]),
          ),
    );
  }
  function format(item: Entity, f: Field): string {
    const v = item[f.key];
    if (v === null || v === undefined) return "Default";
    if (f.ref)
      return f.ref === "duties" ? dutyName(data, v) : nameOf(data, f.ref, v);
    if (f.type === "days")
      return v.map((n: number) => weekdays[n]).join(", ") || "None";
    if (f.type === "checkbox") return v ? "Yes" : "No";
    return String(v).replaceAll("_", " ");
  }
  async function save() {
    if (!edit) return;
    setSaving(true);
    try {
      const { id, ...body } = edit;
      await api(
        `/entities/${table}${id ? "/" + id : ""}`,
        body,
        id ? "PUT" : "POST",
      );
      setEdit(null);
      await onSaved();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  const filtered = rows(data, table).filter((item) =>
    fields.some((f) =>
      format(item, f).toLowerCase().includes(search.toLowerCase()),
    ),
  );
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Organisation & rules</h2>
          <p>
            Keep ownership, eligibility and operating requirements in one place.
          </p>
        </div>
        <button className="primary" onClick={() => start()}>
          + Add {labels[table].toLowerCase()}
        </button>
      </div>
      <div className="tabs wrap">
        {Object.entries(labels).map(([key, label]) => (
          <button
            key={key}
            className={table === key ? "selected" : ""}
            onClick={() => {
              setTable(key);
              setSearch("");
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="panel">
        <div className="table-tools">
          <input
            aria-label="Search records"
            placeholder="Search records…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <span>{filtered.length} records</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {fields.slice(0, 5).map((f) => (
                  <th key={f.key}>{f.label}</th>
                ))}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  {fields.slice(0, 5).map((f) => (
                    <td key={f.key}>{format(item, f)}</td>
                  ))}
                  <td>
                    <button className="text-button" onClick={() => start(item)}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filtered.length && (
            <div className="empty">No matching records.</div>
          )}
        </div>
      </div>
      {edit && (
        <div className="overlay">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-title"
          >
            <div className="section-heading">
              <h2 id="edit-title">
                {edit.id ? "Edit" : "Add"} {labels[table].toLowerCase()}
              </h2>
              <button aria-label="Close editor" onClick={() => setEdit(null)}>
                ×
              </button>
            </div>
            <p className="muted">
              Changes are saved to the database and mark existing published
              rosters stale. Use roster change preview for a validated
              replacement.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void save();
              }}
            >
              <div className="form-grid">
                {fields.map((f) => (
                  <label
                    key={f.key}
                    className={f.type === "days" ? "full" : ""}
                  >
                    {f.label}
                    {f.type === "days" ? (
                      <div className="day-options">
                        {weekdays.map((d, n) => (
                          <button
                            type="button"
                            key={d}
                            className={
                              (edit[f.key] || []).includes(n) ? "selected" : ""
                            }
                            onClick={() =>
                              setEdit({
                                ...edit,
                                [f.key]: (edit[f.key] || []).includes(n)
                                  ? edit[f.key].filter((v: number) => v !== n)
                                  : [...(edit[f.key] || []), n],
                              })
                            }
                          >
                            {d}
                          </button>
                        ))}
                      </div>
                    ) : f.ref ? (
                      <select
                        required={!f.optional}
                        value={edit[f.key] ?? ""}
                        onChange={(e) =>
                          setEdit({
                            ...edit,
                            [f.key]: e.target.value
                              ? Number(e.target.value)
                              : null,
                          })
                        }
                      >
                        <option value="">
                          {f.optional ? "Use default / none" : "Select…"}
                        </option>
                        {rows(data, f.ref)
                          .filter((x) => x.active || x.id === edit[f.key])
                          .map((x) => (
                            <option key={x.id} value={x.id}>
                              {f.ref === "duties"
                                ? dutyName(data, x.id)
                                : x.name}
                            </option>
                          ))}
                      </select>
                    ) : f.options ? (
                      <select
                        value={edit[f.key]}
                        onChange={(e) =>
                          setEdit({ ...edit, [f.key]: e.target.value })
                        }
                      >
                        {f.options.map((o) => (
                          <option key={o} value={o}>
                            {o.replaceAll("_", " ")}
                          </option>
                        ))}
                      </select>
                    ) : f.type === "checkbox" ? (
                      <input
                        type="checkbox"
                        checked={!!edit[f.key]}
                        onChange={(e) =>
                          setEdit({ ...edit, [f.key]: e.target.checked })
                        }
                      />
                    ) : (
                      <input
                        type={f.type || "text"}
                        required={!f.optional}
                        value={edit[f.key] ?? ""}
                        onChange={(e) =>
                          setEdit({
                            ...edit,
                            [f.key]:
                              f.type === "number"
                                ? e.target.value === ""
                                  ? null
                                  : Number(e.target.value)
                                : e.target.value ||
                                  (f.optional && f.type === "date" ? null : ""),
                          })
                        }
                      />
                    )}
                  </label>
                ))}
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setEdit(null)}>
                  Cancel
                </button>
                <button className="primary" disabled={saving}>
                  {saving ? "Saving…" : "Save changes"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
