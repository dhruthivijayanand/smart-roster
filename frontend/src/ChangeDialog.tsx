import { useState } from "react";
import {
  api,
  Data,
  Preview,
  Roster,
  rows,
  nameOf,
  dutyName,
  Finding,
} from "./api";
export function Findings({ items, data }: { items: Finding[]; data: Data }) {
  const [severity, setSeverity] = useState("hard");
  const [date, setDate] = useState("");
  const selected = items.filter(
    (f) =>
      (severity === "all" || f.severity === severity) &&
      (!date || f.date === date),
  );
  return (
    <>
      <div className="table-tools">
        <div className="tabs">
          {["hard", "soft", "all"].map((s) => (
            <button
              key={s}
              className={severity === s ? "selected" : ""}
              onClick={() => setSeverity(s)}
            >
              {s === "hard"
                ? "Mandatory violations"
                : s === "soft"
                  ? "Preference deviations"
                  : "All findings"}
            </button>
          ))}
        </div>
        <input
          aria-label="Filter findings by date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </div>
      {!selected.length ? (
        <div className="empty">
          <strong>
            No{" "}
            {severity === "hard" ? "mandatory violations" : "matching findings"}
          </strong>
          <p>
            {severity === "hard"
              ? "Coverage and resource rules have no reported violations in this selection."
              : "Try another filter."}
          </p>
        </div>
      ) : (
        <div className="finding-list">
          {selected.slice(0, 200).map((f, i) => (
            <article key={i} className={`finding ${f.severity}`}>
              <div className="finding-top">
                <span className={`badge ${f.severity}`}>
                  {f.code.replaceAll("_", " ")}
                </span>
                <time>{f.date}</time>
              </div>
              <h4>
                {f.brand
                  ? `${f.brand} / ${f.process}`
                  : f.employee_id
                    ? nameOf(data, "employees", f.employee_id)
                    : "Planning rules"}
              </h4>
              <p>{f.reason}</p>
              {f.required !== null && (
                <div className="finding-counts">
                  <span>
                    Required <b>{f.required}</b>
                  </span>
                  <span>
                    Eligible <b>{f.eligible}</b>
                  </span>
                  <span>
                    Assigned <b>{f.actual}</b>
                  </span>
                </div>
              )}
              <small>{f.suggestion}</small>
            </article>
          ))}
        </div>
      )}
      {selected.length > 200 && (
        <p className="muted">
          Showing 200 of {selected.length} findings. Filter by date to inspect
          the rest.
        </p>
      )}
    </>
  );
}
export default function ChangeDialog({
  data,
  roster,
  employee,
  date,
  onClose,
  onApplied,
  onError,
}: {
  data: Data;
  roster: Roster;
  employee: number;
  date: string;
  onClose: () => void;
  onApplied: (r: Roster) => Promise<void>;
  onError: (s: string) => void;
}) {
  const [e, setE] = useState(employee);
  const [d, setD] = useState(date);
  const [kind, setKind] = useState("leave");
  const [repair, setRepair] = useState(true);
  const [replacement, setReplacement] = useState("");
  const [duty, setDuty] = useState("");
  const [remove, setRemove] = useState(true);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  function changed(fn: () => void) {
    fn();
    setPreview(null);
  }
  async function inspect() {
    setBusy(true);
    try {
      setPreview(
        await api<Preview>(`/rosters/${roster.id}/changes/preview`, {
          expected_revision: roster.revision,
          employee_id: e,
          date: d,
          kind,
          repair,
          replacement_id: replacement ? Number(replacement) : null,
          duty_id: duty ? Number(duty) : null,
          remove,
        }),
      );
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function apply() {
    if (!preview) return;
    setBusy(true);
    try {
      await onApplied(
        await api<Roster>(
          `/rosters/${roster.id}/changes/${preview.change_id}/apply`,
          { expected_revision: roster.revision },
        ),
      );
      onClose();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="overlay">
      <section
        className="modal wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-title"
      >
        <div className="section-heading">
          <div>
            <span className="eyebrow">CHANGE CONTROL</span>
            <h2 id="change-title">Preview the impact</h2>
          </div>
          <button aria-label="Close change preview" onClick={onClose}>
            ×
          </button>
        </div>
        <p className="muted">
          All brands and processes are checked together. Unaffected dates stay
          fixed.
        </p>
        <div className="form-grid">
          <label>
            Employee
            <select
              value={e}
              onChange={(v) => changed(() => setE(Number(v.target.value)))}
            >
              {rows(data, "employees")
                .filter((e) => e.active)
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Date
            <input
              type="date"
              value={d}
              min={roster.days[0]}
              max={roster.days.at(-1)}
              onChange={(v) => changed(() => setD(v.target.value))}
            />
          </label>
          <label>
            Change type
            <select
              value={kind}
              onChange={(v) => changed(() => setKind(v.target.value))}
            >
              {[
                "leave",
                "comp_off",
                "unavailable",
                "weekly_off",
                "allocation",
              ].map((k) => (
                <option key={k} value={k}>
                  {k.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Replacement (optional)
            <select
              value={replacement}
              onChange={(v) => changed(() => setReplacement(v.target.value))}
            >
              <option value="">Find a feasible repair automatically</option>
              {rows(data, "employees")
                .filter((x) => x.active && x.id !== e)
                .map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name}
                  </option>
                ))}
            </select>
          </label>
          {kind === "allocation" && (
            <>
              <label>
                Duty
                <select
                  value={duty}
                  onChange={(v) => changed(() => setDuty(v.target.value))}
                >
                  <option value="">Select a brand / process</option>
                  {rows(data, "duties")
                    .filter((j) => j.active)
                    .map((j) => (
                      <option key={j.id} value={j.id}>
                        {dutyName(data, j.id)}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Action
                <select
                  value={String(remove)}
                  onChange={(v) =>
                    changed(() => setRemove(v.target.value === "true"))
                  }
                >
                  <option value="true">Remove this allocation</option>
                  <option value="false">Add this allocation</option>
                </select>
              </label>
            </>
          )}
        </div>
        <label className="check-row">
          <input
            type="checkbox"
            checked={repair}
            onChange={(v) => changed(() => setRepair(v.target.checked))}
          />
          Find a repair while preserving other dates
        </label>
        <button
          className="primary"
          disabled={busy}
          onClick={() => void inspect()}
        >
          {busy ? "Checking constraints…" : "Preview change"}
        </button>
        {preview && (
          <div className="preview-result">
            <div
              className={`notice ${preview.result.publishable ? "success" : "warning"}`}
            >
              <strong>
                {preview.result.publishable
                  ? "Validated proposal — ready for your approval"
                  : "This change cannot be safely applied"}
              </strong>
              <p>
                {preview.affected.length} existing responsibilities affected ·{" "}
                {preview.diff.removed.length} allocations removed ·{" "}
                {preview.diff.added.length} added · solver{" "}
                {preview.result.solver_status}
              </p>
            </div>
            {preview.result.repair_scope?.expanded && (
              <div className="notice warning">
                {preview.result.repair_scope.reason} Scope:{" "}
                {preview.result.repair_scope.dates[0]} through{" "}
                {preview.result.repair_scope.dates.at(-1)}.
              </div>
            )}
            <h3>Impact before repair</h3>
            <Findings items={preview.before_findings} data={data} />
            {preview.candidates.length > 0 && (
              <>
                <h3>Replacement candidates</h3>
                <div className="chips">
                  {preview.candidates.map((c) => (
                    <button
                      key={c.employee_id}
                      onClick={() =>
                        changed(() => setReplacement(String(c.employee_id)))
                      }
                    >
                      {c.name} · {c.resulting_load}/{c.capacity} units
                    </button>
                  ))}
                </div>
                <p className="muted">
                  Selecting a candidate requires a fresh preview, including
                  their rest-day rules.
                </p>
              </>
            )}
            <h3>Proposed allocation changes</h3>
            <div className="diff-list">
              {(["removed", "added"] as const).map((t) =>
                preview.diff[t].map((a, i) => (
                  <div key={t + i}>
                    <span
                      className={`badge ${t === "added" ? "good" : "soft"}`}
                    >
                      {t}
                    </span>
                    <span>
                      {nameOf(data, "employees", a.employee_id)} ·{" "}
                      {dutyName(data, a.duty_id)} · {a.date}
                    </span>
                  </div>
                )),
              )}
            </div>
            {!preview.result.publishable && (
              <Findings
                items={preview.result.findings.filter((f) => f.date === d)}
                data={data}
              />
            )}
            <div className="modal-footer">
              <button onClick={onClose}>Cancel</button>
              <button
                className="primary"
                disabled={busy || !preview.result.publishable}
                onClick={() => void apply()}
              >
                Approve & apply changes
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
