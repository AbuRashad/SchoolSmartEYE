import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2, RefreshCw, Users, Eye, Search, ChevronDown, ChevronUp } from "lucide-react";
import type { StudentCreatePayload, StudentRecord } from "../../types";
import { api } from "./api";
import { Field, inputCls, type Flash } from "./ui";
import { StudentProfileModal } from "./StudentProfileModal";

export function StudentsTab({ flash }: { flash: Flash }) {
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [gradeFilter, setGradeFilter] = useState("");
  const [sectionFilter, setSectionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [openForm, setOpenForm] = useState(false);
  const [profileId, setProfileId] = useState<string | null>(null);

  const [form, setForm] = useState<StudentCreatePayload>({
    student_id: "",
    name: "",
    grade: "",
    class_section: "",
    parent_id: "",
    photo_initial: "",
    is_active: true,
  });

  const reload = useCallback(async () => {
    try {
      const s = await api<StudentRecord[]>("/students");
      setStudents(s);
    } catch (e) {
      flash("err", `Failed to load: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [flash]);

  useEffect(() => {
    reload();
  }, [reload]);

  const grades = useMemo(
    () => Array.from(new Set(students.map((s) => s.grade))).sort(),
    [students],
  );
  const sections = useMemo(
    () => Array.from(new Set(students.map((s) => s.class_section))).sort(),
    [students],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return students.filter((s) => {
      if (gradeFilter && s.grade !== gradeFilter) return false;
      if (sectionFilter && s.class_section !== sectionFilter) return false;
      if (statusFilter === "active" && !s.is_active) return false;
      if (statusFilter === "inactive" && s.is_active) return false;
      if (!q) return true;
      return (
        s.name.toLowerCase().includes(q) ||
        s.student_id.toLowerCase().includes(q) ||
        s.parent_id.toLowerCase().includes(q)
      );
    });
  }, [students, query, gradeFilter, sectionFilter, statusFilter]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload: StudentCreatePayload = {
        ...form,
        photo_initial: form.photo_initial?.trim() || form.name.charAt(0).toUpperCase(),
      };
      await api<StudentRecord>("/students", { method: "POST", body: JSON.stringify(payload) });
      flash("ok", `Student ${form.name} added`);
      setForm({
        student_id: "",
        name: "",
        grade: "",
        class_section: "",
        parent_id: "",
        photo_initial: "",
        is_active: true,
      });
      setOpenForm(false);
      reload();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeOne = async (id: string) => {
    if (!confirm(`Delete student "${id}"? Their bracelet (if any) will also be removed.`))
      return;
    setBusy(true);
    try {
      await api(`/students/${encodeURIComponent(id)}`, { method: "DELETE" });
      flash("ok", `Student ${id} deleted`);
      reload();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const clearFilters = () => {
    setQuery("");
    setGradeFilter("");
    setSectionFilter("");
    setStatusFilter("all");
  };

  const hasFilters =
    query.length > 0 || gradeFilter || sectionFilter || statusFilter !== "all";

  return (
    <>
      <div className="space-y-4">
        {/* Toolbar */}
        <div className="rounded-2xl border border-white/10 bg-panel/60 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[220px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-mist/50" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name, ID, or parent…"
                className={`${inputCls} pl-9`}
              />
            </div>
            <select
              value={gradeFilter}
              onChange={(e) => setGradeFilter(e.target.value)}
              className={`${inputCls} min-w-[130px] flex-none`}
            >
              <option value="">All grades</option>
              {grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
            <select
              value={sectionFilter}
              onChange={(e) => setSectionFilter(e.target.value)}
              className={`${inputCls} min-w-[110px] flex-none`}
            >
              <option value="">All sections</option>
              {sections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
              className={`${inputCls} min-w-[120px] flex-none`}
            >
              <option value="all">Any status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-mist/80 hover:bg-white/10 hover:text-white"
              >
                Clear
              </button>
            )}
            <button
              type="button"
              onClick={reload}
              disabled={busy}
              title="Refresh"
              className="rounded-xl border border-white/10 bg-white/5 p-2 text-mist/80 hover:bg-white/10 hover:text-white disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setOpenForm((o) => !o)}
              className="flex items-center gap-2 rounded-xl bg-cobalt px-3 py-2 text-sm font-semibold text-white transition hover:bg-cobalt/90"
            >
              {openForm ? <ChevronUp className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              {openForm ? "Close" : "Add Student"}
            </button>
          </div>

          {/* Collapsible Add Form */}
          {openForm && (
            <form
              onSubmit={submit}
              className="mt-3 grid gap-3 rounded-xl border border-white/10 bg-black/20 p-4 md:grid-cols-3"
            >
              <Field label="Student ID">
                <input
                  required
                  value={form.student_id}
                  onChange={(e) => setForm({ ...form, student_id: e.target.value.trim() })}
                  placeholder="STU-2024-0900"
                  className={inputCls}
                />
              </Field>
              <Field label="Full Name">
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Ahmed Al-Rashidi"
                  className={inputCls}
                />
              </Field>
              <Field label="Parent ID">
                <input
                  required
                  value={form.parent_id}
                  onChange={(e) => setForm({ ...form, parent_id: e.target.value.trim() })}
                  placeholder="PAR-2024-0900"
                  className={inputCls}
                />
              </Field>
              <Field label="Grade">
                <input
                  required
                  value={form.grade}
                  onChange={(e) => setForm({ ...form, grade: e.target.value })}
                  placeholder="Grade 9"
                  className={inputCls}
                />
              </Field>
              <Field label="Section">
                <input
                  required
                  value={form.class_section}
                  onChange={(e) => setForm({ ...form, class_section: e.target.value })}
                  placeholder="A"
                  className={inputCls}
                />
              </Field>
              <Field label="Photo Initial" hint="Single letter (auto if blank)">
                <input
                  value={form.photo_initial ?? ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      photo_initial: e.target.value.slice(0, 1).toUpperCase(),
                    })
                  }
                  placeholder="A"
                  maxLength={1}
                  className={inputCls}
                />
              </Field>
              <div className="md:col-span-3">
                <button
                  type="submit"
                  disabled={busy}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-cobalt px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-cobalt/90 disabled:opacity-50"
                >
                  <Plus className="h-4 w-4" /> Add Student
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-mist/60">
            Students ({filtered.length}
            {filtered.length !== students.length && ` of ${students.length}`})
          </h3>
        </div>

        {/* List */}
        {loading ? (
          <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-8 text-center text-sm text-mist/60">
            Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-10 text-center text-sm text-mist/70">
            <Users className="mx-auto mb-2 h-8 w-8 text-mist/40" />
            {students.length === 0 ? "No students yet." : "No students match your filters."}
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-panel/60">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-white/5 text-left text-[11px] uppercase tracking-wider text-mist/60">
                  <tr>
                    <th className="px-3 py-2">Student</th>
                    <th className="px-3 py-2">ID</th>
                    <th className="px-3 py-2">Grade</th>
                    <th className="px-3 py-2">Section</th>
                    <th className="px-3 py-2">Parent</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => (
                    <tr
                      key={s.student_id}
                      className="border-t border-white/5 transition hover:bg-white/5"
                    >
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => setProfileId(s.student_id)}
                          className="flex items-center gap-2 text-left"
                        >
                          <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-cobalt/40 bg-cobalt/15 text-sm font-bold text-white">
                            {s.photo_initial || s.name.charAt(0).toUpperCase()}
                          </span>
                          <span className="font-medium text-white hover:text-cobalt">
                            {s.name}
                          </span>
                        </button>
                      </td>
                      <td className="px-3 py-2 font-mono text-[11px] text-mist/80">
                        {s.student_id}
                      </td>
                      <td className="px-3 py-2 text-mist/75">{s.grade}</td>
                      <td className="px-3 py-2 text-mist/75">{s.class_section}</td>
                      <td className="px-3 py-2 font-mono text-[11px] text-mist/60">
                        {s.parent_id}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                            s.is_active
                              ? "border-safe/40 bg-safe/10 text-safe"
                              : "border-white/15 bg-white/5 text-mist/70"
                          }`}
                        >
                          {s.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => setProfileId(s.student_id)}
                            title="View profile"
                            className="rounded-lg border border-cobalt/40 bg-cobalt/10 p-1.5 text-cobalt hover:bg-cobalt/20"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => removeOne(s.student_id)}
                            disabled={busy}
                            title="Delete"
                            className="rounded-lg border border-critical/40 bg-critical/10 p-1.5 text-critical hover:bg-critical/20 disabled:opacity-50"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {profileId && (
        <StudentProfileModal
          studentId={profileId}
          flash={flash}
          onClose={() => setProfileId(null)}
          onChanged={reload}
        />
      )}
    </>
  );
}
