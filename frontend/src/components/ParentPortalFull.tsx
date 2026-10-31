import type { StudentPortalData } from "../types";

type Props = { data: StudentPortalData | null };

export function ParentPortalFull({ data }: Props) {
  if (!data) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-12 text-center text-mist/50 shadow-panel">
        Loading school portal status…
      </div>
    );
  }

  return (
    <section className="rounded-[2rem] border border-warning/30 bg-panel/90 p-6 shadow-panel">
      <p className="text-xs uppercase tracking-[0.24em] text-warning">School-scoped portal</p>
      <h2 className="mt-3 text-xl font-semibold text-white">Student identity link required</h2>
      <p className="mt-2 text-sm leading-6 text-mist/70">{data.message}</p>
      <p className="mt-4 text-xs text-mist/40">Authorized school: {data.school_id}</p>
      <p className="mt-2 text-xs text-mist/40">
        No student profile, attendance, location, or notification data is shown until an authenticated student/parent link is configured.
      </p>
    </section>
  );
}
