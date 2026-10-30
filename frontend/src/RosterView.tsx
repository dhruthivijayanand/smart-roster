import { useMemo, useState } from "react";
import { Data, Roster, rows, nameOf, dutyName } from "./api";
const statusLabel: Record<string, string> = {
  work: "W",
  weekly_off: "OFF",
  holiday: "HOL",
  leave: "LV",
  comp_off: "CO",
  unavailable: "NA",
};
export default function RosterView({
  data,
  roster,
  onEdit,
}: {
  data: Data;
  roster: Roster;
  onEdit: (employee: number, date: string) => void;
}) {
  const [mode, setMode] = useState("Company");
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const options =
    mode === "Pod"
      ? rows(data, "pods")
      : mode === "Brand"
        ? rows(data, "brands")
        : mode === "Process"
          ? rows(data, "processes")
          : mode === "Employee"
            ? rows(data, "employees")
            : [];
  const employees = rows(data, "employees").filter(
    (e) =>
      e.active &&
      e.name?.toLowerCase().includes(search.toLowerCase()) &&
      (!filter ||
        mode === "Company" ||
        (mode === "Pod" && e.pod_id === Number(filter)) ||
        (mode === "Employee" && e.id === Number(filter)) ||
        (["Brand", "Process"].includes(mode) &&
          rows(data, "assignments").some(
            (a) =>
              a.active &&
              a.employee_id === e.id &&
              rows(data, "duties").some(
                (d) =>
                  d.id === a.duty_id &&
                  (mode === "Brand" ? d.brand_id : d.process_id) ===
                    Number(filter),
              ),
          ))),
  );
  const statusMap = useMemo(
    () =>
      new Map(
        roster.statuses.map((s) => [`${s.employee_id}/${s.date}`, s.status]),
      ),
    [roster],
  );
  const coverage = useMemo(() => {
    const map = new Map<string, Set<number>>();
    for (const a of roster.allocations) {
      const k = `${a.duty_id}/${a.date}`;
      if (!map.has(k)) map.set(k, new Set());
      map.get(k)!.add(a.employee_id);
    }
    return map;
  }, [roster]);
  const duties = rows(data, "duties").filter(
    (d) =>
      d.active &&
      (!filter ||
        !["Brand", "Process"].includes(mode) ||
        (mode === "Brand" ? d.brand_id : d.process_id) === Number(filter)),
  );
  const selectedPod =
    mode === "Pod" && filter
      ? rows(data, "pods").find((p) => p.id === Number(filter))
      : null;
  return (
    <>
      <div className="table-tools">
        <div className="tabs">
          {["Company", "Pod", "Brand", "Process", "Employee"].map((m) => (
            <button
              key={m}
              className={mode === m ? "selected" : ""}
              onClick={() => {
                setMode(m);
                setFilter("");
              }}
            >
              {m}
            </button>
          ))}
        </div>
        <div className="filters">
          {options.length > 0 && (
            <select
              aria-label={`${mode} filter`}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="">All {mode.toLowerCase()}s</option>
              {options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          )}
          <input
            placeholder="Find an employee…"
            aria-label="Search employees"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>
      {selectedPod && (
        <p className="info-line">
          Pod lead:{" "}
          {selectedPod.lead_id
            ? nameOf(data, "employees", selectedPod.lead_id)
            : "Not assigned"}
        </p>
      )}
      <div className="legend">
        {Object.entries(statusLabel).map(([key, label]) => (
          <span key={key}>
            <i className={`status ${key}`}>{label}</i>
            {key.replaceAll("_", " ")}
          </span>
        ))}
        <span className="muted">Select a day to preview a change</span>
      </div>
      <div className="panel table-scroll roster-scroll">
        <table className="roster-table">
          <thead>
            <tr>
              <th className="sticky-name">Employee / pod</th>
              {roster.days.map((d) => (
                <th
                  key={d}
                  className={
                    new Date(d + "T12:00:00").getDay() === 0 ? "sunday" : ""
                  }
                >
                  <strong>{d.slice(-2)}</strong>
                  <small>
                    {new Date(d + "T12:00:00").toLocaleDateString("en", {
                      weekday: "short",
                    })}
                  </small>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {employees.map((e) => (
              <tr key={e.id}>
                <td className="sticky-name">
                  <strong>{e.name}</strong>
                  <small>{nameOf(data, "pods", e.pod_id)}</small>
                </td>
                {roster.days.map((d) => {
                  const s = statusMap.get(`${e.id}/${d}`) || "weekly_off";
                  const assignments = roster.allocations.filter(
                    (a) => a.employee_id === e.id && a.date === d,
                  );
                  const conflict = roster.findings.some(
                    (f) =>
                      f.severity === "hard" &&
                      f.date === d &&
                      f.employee_id === e.id,
                  );
                  return (
                    <td key={d}>
                      <button
                        aria-label={`${e.name}, ${d}, ${s}`}
                        title={
                          assignments
                            .map((a) => dutyName(data, a.duty_id))
                            .join("\n") || s
                        }
                        className={`status ${s} ${conflict ? "conflict" : ""}`}
                        onClick={() => onEdit(e.id, d)}
                      >
                        {statusLabel[s] || s}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {!employees.length && (
          <div className="empty">No employees match these filters.</div>
        )}
      </div>
      {["Brand", "Process"].includes(mode) && (
        <>
          <h3>Process coverage</h3>
          <p className="muted">
            Assigned distinct employees by day. Red cells have a required
            coverage gap; — means no allocation.
          </p>
          <div className="panel table-scroll">
            <table className="roster-table">
              <thead>
                <tr>
                  <th className="sticky-name">Brand / process</th>
                  {roster.days.map((d) => (
                    <th key={d}>{d.slice(-2)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {duties.map((j) => (
                  <tr key={j.id}>
                    <td className="sticky-name">
                      <strong>{nameOf(data, "brands", j.brand_id)}</strong>
                      <small>
                        {nameOf(data, "processes", j.process_id)} · min{" "}
                        {j.minimum} ·{" "}
                        {nameOf(
                          data,
                          "calendars",
                          j.calendar_id ||
                            rows(data, "brands").find(
                              (b) => b.id === j.brand_id,
                            )?.calendar_id,
                        )}
                      </small>
                    </td>
                    {roster.days.map((d) => {
                      const gap = roster.findings.find(
                        (f) =>
                          f.code === "COVERAGE" &&
                          f.date === d &&
                          f.duty_id === j.id,
                      );
                      return (
                        <td
                          key={d}
                          className={gap ? "gap-cell" : ""}
                          title={gap?.reason}
                        >
                          {coverage.get(`${j.id}/${d}`)?.size || "—"}
                          {gap && <small>/{gap.required}</small>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {mode === "Employee" && filter && (
        <div className="panel padded">
          <h3>Eligible responsibilities</h3>
          <div className="chips">
            {rows(data, "assignments")
              .filter((a) => a.active && a.employee_id === Number(filter))
              .map((a) => (
                <span key={a.id}>
                  {dutyName(data, a.duty_id)} · {a.role}
                </span>
              ))}
          </div>
        </div>
      )}
    </>
  );
}
