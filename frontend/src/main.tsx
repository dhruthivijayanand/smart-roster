import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  CalendarDays,
  Users,
  ShieldCheck,
  History,
  ArrowUpRight,
  Layers,
  Download,
  RefreshCw,
} from "lucide-react";
import { api, Data, Roster, rows } from "./api";
import Management from "./Management";
import RosterView from "./RosterView";
import ChangeDialog, { Findings } from "./ChangeDialog";
import "./styles.css";
function App() {
  const [data, setData] = useState<Data | null>(null);
  const [roster, setRoster] = useState<Roster | null>(null);
  const [month, setMonth] = useState("2026-11");
  const [page, setPage] = useState("roster");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [edit, setEdit] = useState<{ employee: number; date: string } | null>(
    null,
  );
  const [history, setHistory] = useState<any[]>([]);
  const [versions, setVersions] = useState<any[]>([]);
  const [toast, setToast] = useState("");
  const [token, setToken] = useState(
    sessionStorage.getItem("manager-token") || "",
  );
  const [settings, setSettings] = useState(false);
  async function load() {
    setData(await api<Data>("/data"));
  }
  async function refreshVersions(m = month) {
    const v = await api<any[]>("/rosters?month=" + m);
    setVersions(v);
    return v;
  }
  useEffect(() => {
    void load().catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    let cancelled = false;
    setRoster(null);
    void api<any[]>("/rosters?month=" + month)
      .then(async (list) => {
        if (cancelled) return;
        setVersions(list);
        if (list.length) {
          const r = await api<Roster>("/rosters/" + list[0].id);
          if (!cancelled) setRoster(r);
        }
      })
      .catch((e) => setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [month]);
  async function run(label: string, fn: () => Promise<void>) {
    setError("");
    setBusy(label);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function generate() {
    await run("Solving coverage, capacity and rest…", async () => {
      setRoster(await api<Roster>("/rosters/generate", { month }));
      await refreshVersions();
      setToast("Roster generated. Review coverage before publishing.");
    });
  }
  async function changed() {
    await load();
    if (roster) setRoster(await api<Roster>("/rosters/" + roster.id));
    setToast("Saved. Existing roster inputs may need revalidation.");
  }
  async function publish() {
    if (roster)
      await run("Validating publication…", async () => {
        setRoster(
          await api<Roster>(`/rosters/${roster.id}/publish`, {
            expected_revision: roster.revision,
          }),
        );
        await refreshVersions();
        setToast("Roster published after independent validation.");
      });
  }
  async function validate() {
    if (roster)
      await run("Rechecking all constraints…", async () => {
        const current = await api<Roster>(`/rosters/${roster.id}/validate`, {});
        setRoster({ ...roster, ...current });
        setToast("Validation complete.");
        setPage("conflicts");
      });
  }
  const hard =
    roster?.findings.filter(
      (f) => f.severity === "hard" && roster.days.includes(f.date),
    ).length || 0;
  const coverage =
    roster && roster.summary.required_slots
      ? Math.round(
          (100 *
            Math.min(
              roster.summary.covered_slots,
              roster.summary.required_slots,
            )) /
            roster.summary.required_slots,
        )
      : 0;
  const activeCount = (key: string) =>
    data ? rows(data, key).filter((x) => x.active).length : 0;
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("roster");
          }}
        >
          <span className="brand-mark">ds</span>
          <span>
            datastraw<small>OPERATIONS WORKSPACE</small>
          </span>
        </a>
        <div className="workspace">
          <span className="live-dot" /> Smart roster{" "}
          <span className="badge neutral">DEMO</span>
        </div>
        <nav>
          {[
            { id: "roster", label: "Monthly roster", icon: CalendarDays },
            { id: "management", label: "Organisation & rules", icon: Users },
            { id: "conflicts", label: "Validation centre", icon: ShieldCheck },
            { id: "history", label: "Change history", icon: History },
          ].map((n) => (
            <button
              key={n.id}
              className={page === n.id ? "active" : ""}
              onClick={() => {
                setPage(n.id);
                if (n.id === "history")
                  void api<any[]>("/audit")
                    .then(setHistory)
                    .catch((e) => setError(e.message));
              }}
            >
              <n.icon size={18} />
              {n.label}
              {n.id === "conflicts" && hard > 0 && <b>{hard}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <Layers size={22} />
          <strong>Coverage comes first.</strong>
          <p>Plan every process. Respect every person's availability.</p>
        </div>
        <button className="profile" onClick={() => setSettings(true)}>
          <span className="avatar">DV</span>
          <span>
            Dhruthi Vijayanand<small>Operations manager</small>
          </span>
        </button>
      </aside>
      <main>
        <header className="topbar">
          <span>
            Operations <span className="slash">/</span>{" "}
            {page === "roster"
              ? "Monthly planning"
              : page === "management"
                ? "Organisation"
                : page === "conflicts"
                  ? "Validation"
                  : "Audit trail"}
          </span>
          <span className="timezone">Asia/Kolkata · fictional demo data</span>
        </header>
        <div className="content">
          {error && (
            <div className="notice error" role="alert">
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          {toast && (
            <div className="notice success" role="status">
              <span>{toast}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setToast("")}
              >
                ×
              </button>
            </div>
          )}
          {!data ? (
            <div className="empty">
              <h2>Loading operations data…</h2>
              <button onClick={() => void run("Loading…", load)}>Retry</button>
            </div>
          ) : (
            <>
              {page !== "management" && page !== "history" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="eyebrow">WORKFORCE PLANNING</span>
                      <h1>
                        {page === "conflicts"
                          ? "Every constraint, accounted for."
                          : "A clear plan for every day."}
                      </h1>
                      <p>
                        Coordinate people, brands and processes without losing
                        sight of coverage.
                      </p>
                    </div>
                    <div className="month-control">
                      <label htmlFor="month">Planning month</label>
                      <input
                        id="month"
                        type="month"
                        value={month}
                        min="2020-01"
                        max="2100-12"
                        onChange={(e) => {
                          if (e.target.value) setMonth(e.target.value);
                        }}
                      />
                    </div>
                  </div>
                  <div className="stats">
                    <div>
                      <span>Active employees</span>
                      <strong>
                        {activeCount("employees")}
                        <small>across {activeCount("pods")} pods</small>
                      </strong>
                    </div>
                    <div>
                      <span>Brand portfolio</span>
                      <strong>
                        {activeCount("brands")}
                        <small>
                          {activeCount("duties")} process requirements
                        </small>
                      </strong>
                    </div>
                    <div>
                      <span>Monthly coverage</span>
                      <strong>
                        {roster ? coverage + "%" : "—"}
                        <small>
                          {roster
                            ? `${roster.summary.covered_slots} / ${roster.summary.required_slots} staffing slots`
                            : "Generate a roster to evaluate"}
                        </small>
                      </strong>
                    </div>
                    <div className={hard ? "alert-stat" : ""}>
                      <span>Mandatory findings</span>
                      <strong>
                        {roster ? hard : "—"}
                        <small>
                          {roster
                            ? `${roster.summary.soft} preference deviations in planning horizon`
                            : "No roster evaluated yet"}
                        </small>
                      </strong>
                    </div>
                  </div>
                </>
              )}
              {page === "roster" && (
                <>
                  <div className="section-heading">
                    <div>
                      <h2>
                        Monthly roster{" "}
                        {roster && (
                          <span
                            className={`badge ${roster.stale ? "soft" : roster.publishable ? "good" : "hard"}`}
                          >
                            {roster.stale
                              ? "Inputs changed"
                              : roster.status === "published"
                                ? "Published"
                                : roster.publishable
                                  ? "Valid draft"
                                  : "Needs attention"}
                          </span>
                        )}
                      </h2>
                      <p>
                        {roster
                          ? `Version ${roster.id} · ${roster.solver_name} · ${roster.solver_status} · select a cell to manage a change`
                          : "Generate a real schedule from configured rules and availability."}
                      </p>
                    </div>
                    <div className="actions">
                      {roster && (
                        <>
                          <a
                            className="button"
                            href={`/api/rosters/${roster.id}/export`}
                          >
                            <Download size={15} />
                            CSV
                          </a>
                          <button
                            onClick={() => void validate()}
                            disabled={!!busy}
                          >
                            <ShieldCheck size={15} />
                            Validate
                          </button>
                          <button
                            disabled={
                              !!busy || !roster.publishable || roster.stale
                            }
                            onClick={() => void publish()}
                          >
                            Publish
                          </button>
                        </>
                      )}
                      <button
                        className="primary"
                        disabled={!!busy}
                        onClick={() => void generate()}
                      >
                        <RefreshCw size={15} />
                        {roster ? "Generate new version" : "Generate roster"}
                      </button>
                    </div>
                  </div>
                  {busy && (
                    <div className="progress" role="status">
                      <span className="spinner" />
                      {busy}
                    </div>
                  )}
                  {versions.length > 1 && (
                    <label className="version-select">
                      Saved versions{" "}
                      <select
                        value={roster?.id || ""}
                        onChange={(e) =>
                          void run("Loading version…", async () =>
                            setRoster(
                              await api<Roster>("/rosters/" + e.target.value),
                            ),
                          )
                        }
                      >
                        {versions.map((v) => (
                          <option key={v.id} value={v.id}>
                            Version {v.id} · {v.status}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  {roster?.stale && (
                    <div className="notice warning">
                      Organisation rules changed after this roster was
                      generated. Generate a new version or preview a validated
                      change before publishing.
                    </div>
                  )}
                  {roster?.diagnostic && (
                    <div className="notice warning">
                      <strong>Coverage requirements are infeasible.</strong>{" "}
                      This is a diagnostic draft, not a publishable schedule.
                      Review the validation centre for specific gaps.
                    </div>
                  )}
                  {roster ? (
                    <>
                      <RosterView
                        data={data}
                        roster={roster}
                        onEdit={(employee, date) => setEdit({ employee, date })}
                      />
                      <p className="footnote">{roster.boundary_note}</p>
                    </>
                  ) : (
                    <div className="empty hero-empty">
                      <div className="empty-icon">
                        <CalendarDays size={38} />
                      </div>
                      <h2>Your next month starts here.</h2>
                      <p>
                        The engine checks operating calendars, resource
                        eligibility,
                        <br />
                        workload, rest days and approved absences together.
                      </p>
                      <button
                        className="primary"
                        disabled={!!busy}
                        onClick={() => void generate()}
                      >
                        Generate {month} <ArrowUpRight size={17} />
                      </button>
                      <div className="empty-facts">
                        <span>36 fictional people</span>
                        <span>25 brands</span>
                        <span>Independent validation</span>
                      </div>
                    </div>
                  )}
                </>
              )}
              {page === "management" && (
                <Management data={data} onSaved={changed} onError={setError} />
              )}
              {page === "conflicts" &&
                (roster ? (
                  <>
                    <div className="section-heading">
                      <div>
                        <h2>Validation report</h2>
                        <p>
                          Hard violations block publication. Preferences are
                          reported separately. Includes adjacent rest-planning
                          weeks.
                        </p>
                      </div>
                      <button onClick={() => void validate()} disabled={!!busy}>
                        Revalidate
                      </button>
                    </div>
                    <Findings items={roster.findings} data={data} />
                  </>
                ) : (
                  <div className="empty">
                    Generate a roster to inspect its constraints.
                  </div>
                ))}
              {page === "history" && (
                <>
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">ACCOUNTABILITY</span>
                      <h1>A record of every decision.</h1>
                      <p>Saved changes, previews and publication outcomes.</p>
                    </div>
                    <button
                      onClick={() => void api<any[]>("/audit").then(setHistory)}
                    >
                      Refresh
                    </button>
                  </div>
                  <div className="panel padded">
                    {history.length ? (
                      history.map((h) => (
                        <details className="audit" key={h.id}>
                          <summary>
                            <span className="badge neutral">{h.action}</span>
                            <span>
                              {h.roster_id
                                ? "Roster " + h.roster_id
                                : "Organisation data"}
                            </span>
                            <time>
                              {new Date(h.created_at).toLocaleString("en-IN", {
                                timeZone: "Asia/Kolkata",
                              })}
                            </time>
                          </summary>
                          <pre>{JSON.stringify(h.detail, null, 2)}</pre>
                        </details>
                      ))
                    ) : (
                      <div className="empty">
                        Changes will appear here after your first action.
                      </div>
                    )}
                  </div>
                </>
              )}
              {edit && roster && (
                <ChangeDialog
                  data={data}
                  roster={roster}
                  {...edit}
                  onClose={() => setEdit(null)}
                  onError={setError}
                  onApplied={async (r) => {
                    setRoster(r);
                    await load();
                    await refreshVersions();
                    setToast("Change applied. Unaffected dates preserved.");
                  }}
                />
              )}
            </>
          )}
          <footer>
            Smart Roster Management System{" "}
            <span>
              Built for the DataStraw internship assessment · Dhruthi Vijayanand
            </span>
          </footer>
        </div>
      </main>
      {settings && (
        <div className="overlay">
          <section
            className="modal small"
            role="dialog"
            aria-modal="true"
            aria-label="Manager access"
          >
            <h2>Manager access</h2>
            <p>
              If this deployment requires a manager token, enter it here. It
              stays in this browser session.
            </p>
            <label>
              Manager token
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </label>
            <div className="modal-footer">
              <button onClick={() => setSettings(false)}>Cancel</button>
              <button
                className="primary"
                onClick={() => {
                  sessionStorage.setItem("manager-token", token);
                  setSettings(false);
                }}
              >
                Save
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
