import { useCallback, useEffect, useState } from "react";
import { Link2, RefreshCw, ShieldCheck, UserRound, XCircle } from "lucide-react";
import { authFetch } from "../../auth";
import { Field, inputCls, type Flash } from "./ui";

type ParentLink = {
  link_id: number;
  student_id: string;
  student_name: string;
  parent_username: string;
  verification_method: string;
  verified_at: string;
  is_active: boolean;
  revoked_at: string | null;
};

export function ParentLinksTab({ flash }: { flash: Flash }) {
  const [links, setLinks] = useState<ParentLink[]>([]);
  const [studentId, setStudentId] = useState("");
  const [parentUsername, setParentUsername] = useState("");
  const [method, setMethod] = useState<"school_records" | "in_person" | "official_email">("school_records");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const response = await authFetch("/api/v1/parent/links");
      if (!response.ok) throw new Error(`Unable to load parent links (HTTP ${response.status}).`);
      setLinks((await response.json()) as ParentLink[]);
    } catch (error) {
      flash("err", (error as Error).message);
    } finally {
      setLoading(false);
    }
  }, [flash]);

  useEffect(() => { void reload(); }, [reload]);

  const createLink = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      const response = await authFetch("/api/v1/parent/links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: studentId.trim(),
          parent_username: parentUsername.trim(),
          verification_method: method,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Unable to create parent link (HTTP ${response.status}).`);
      }
      flash("ok", "Verified parent link created.");
      setStudentId("");
      setParentUsername("");
      await reload();
    } catch (error) {
      flash("err", (error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const revokeLink = async (link: ParentLink) => {
    if (!confirm(`Revoke parent access for ${link.parent_username} to ${link.student_name}?`)) return;
    setBusy(true);
    try {
      const response = await authFetch(`/api/v1/parent/links/${link.link_id}`, { method: "DELETE" });
      if (!response.ok) throw new Error(`Unable to revoke parent link (HTTP ${response.status}).`);
      flash("ok", "Parent link revoked and audit details recorded.");
      await reload();
    } catch (error) {
      flash("err", (error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning">
        <div className="flex items-center gap-2 font-semibold"><ShieldCheck className="h-4 w-4" /> Identity verification is a school responsibility</div>
        <p className="mt-2 leading-relaxed">Before creating a link, verify the adult against authoritative school records or an approved in-person/official-email process. The parent login must already exist with the exact Parent role. This form records your attestation; it does not perform identity proofing or create login credentials.</p>
      </section>

      <form onSubmit={createLink} className="grid gap-3 rounded-2xl border border-white/10 bg-panel/60 p-4 md:grid-cols-2">
        <Field label="Student ID">
          <input required value={studentId} onChange={(event) => setStudentId(event.target.value)} placeholder="STU-2024-0847" className={inputCls} />
        </Field>
        <Field label="Existing parent username">
          <input required value={parentUsername} onChange={(event) => setParentUsername(event.target.value)} placeholder="parent.account" className={inputCls} />
        </Field>
        <Field label="Verification method">
          <select value={method} onChange={(event) => setMethod(event.target.value as typeof method)} className={inputCls}>
            <option value="school_records">Official school records</option>
            <option value="in_person">In-person verification</option>
            <option value="official_email">Official school email</option>
          </select>
        </Field>
        <div className="flex items-end">
          <button type="submit" disabled={busy} className="w-full rounded-xl bg-cobalt px-4 py-2.5 text-sm font-semibold text-white hover:bg-cobalt/90 disabled:opacity-50">
            <Link2 className="mr-2 inline h-4 w-4" /> Create verified link
          </button>
        </div>
      </form>

      <section className="overflow-hidden rounded-2xl border border-white/10 bg-panel/60">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white"><UserRound className="h-4 w-4" /> Parent links for this school</div>
          <button type="button" onClick={reload} disabled={loading} className="rounded-lg border border-white/10 p-2 text-mist/70 hover:bg-white/10" aria-label="Refresh parent links"><RefreshCw className="h-4 w-4" /></button>
        </div>
        {loading ? (
          <p className="p-5 text-sm text-mist/60">Loading verified links…</p>
        ) : links.length === 0 ? (
          <p className="p-5 text-sm text-mist/60">No parent links have been recorded for this school.</p>
        ) : (
          <div className="divide-y divide-white/8">
            {links.map((link) => (
              <div key={link.link_id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">{link.student_name} <span className="font-mono text-xs text-mist/55">({link.student_id})</span></p>
                  <p className="mt-1 text-xs text-mist/65">{link.parent_username} · {link.verification_method.replace(/_/g, " ")}</p>
                  <p className="mt-1 text-[11px] text-mist/45">Verified {new Date(link.verified_at).toLocaleString()}{link.revoked_at ? ` · Revoked ${new Date(link.revoked_at).toLocaleString()}` : ""}</p>
                </div>
                {link.is_active ? (
                  <button type="button" disabled={busy} onClick={() => revokeLink(link)} className="flex items-center gap-2 rounded-xl border border-critical/35 bg-critical/10 px-3 py-2 text-xs text-critical hover:bg-critical/20 disabled:opacity-50">
                    <XCircle className="h-4 w-4" /> Revoke access
                  </button>
                ) : (
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-mist/55">Revoked</span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
