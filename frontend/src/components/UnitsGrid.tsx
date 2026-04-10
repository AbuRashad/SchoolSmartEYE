import { motion } from "framer-motion";
import {
  Camera, Eye, Navigation, ShieldAlert, Brain, Users, TrendingUp,
  ClipboardList, Bell, Monitor, FileBarChart2, UserCheck, BarChart3, Lock,
} from "lucide-react";
import type { UnitInfo } from "../types";

const UNIT_ICONS = [Camera, Eye, Navigation, ShieldAlert, Brain, Users, TrendingUp, ClipboardList, Bell, Monitor, FileBarChart2, UserCheck, BarChart3, Lock];

const UNIT_DESCRIPTIONS = [
  "استلام البث من الكاميرات في المواقع الحيوية",
  "تقدير الكثافة واتجاهات الحركة ومناطق التكدس",
  "رصد الانتقالات المعتادة وكشف الانحرافات",
  "كشف السقوط، التدافع، الشجار، البقاء غير المبرر",
  "بناء النموذج التاريخي وحساب معامل الغرابة",
  "قياس التناسق الحركي الجماعي واكتشاف انهياره",
  "استشراف مناطق الخطر قبل وقوعها",
  "كشف التناقض بين الحضور المسجل والحركة الفعلية",
  "إصدار التنبيهات وفق الأولوية وتوجيهها",
  "المؤشرات اللحظية والخرائط الحرارية",
  "تقارير تشغيلية، تحليلية، إشرافية، وزارية",
  "إشعارات الحضور والانصراف وتنبيهات الأمان",
  "تقرير نهاية الفصل الدراسي والتقييم الذاتي",
  "نموذج الحوكمة والخصوصية المصمم للسياق العربي",
];

const UNIT_COLORS = [
  "#4f8fd8", "#4f8fd8", "#4f8fd8", "#e84d5b",
  "#9b6dff", "#46c37b", "#ffb84d", "#46c37b",
  "#e84d5b", "#4f8fd8", "#9b6dff", "#46c37b",
  "#ffb84d", "#e84d5b",
];

type Props = { units: UnitInfo[] };

export function UnitsGrid({ units }: Props) {
  return (
    <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mist/55">System Architecture</p>
          <h2 className="mt-2 text-xl font-semibold text-white">14 Integrated Operational Units</h2>
          <p className="mt-2 text-sm text-mist/60">
            Each unit is an independent, interconnected module contributing to the School Safety Index.
          </p>
        </div>
        <span className="rounded-full border border-safe/35 bg-safe/10 px-3 py-1 text-xs font-medium text-safe">
          All {units.length} Active
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {units.map((unit, i) => {
          const Icon = UNIT_ICONS[i] ?? Monitor;
          const color = UNIT_COLORS[i] ?? "#4f8fd8";
          const desc = UNIT_DESCRIPTIONS[i] ?? "";
          return (
            <motion.div
              key={unit.unit_id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.04 }}
              className="group rounded-[1.6rem] border border-white/10 bg-white/5 p-4 transition hover:border-white/20 hover:bg-white/8"
            >
              <div className="flex items-start justify-between gap-3">
                <div
                  className="rounded-2xl p-2.5"
                  style={{ backgroundColor: `${color}20` }}
                >
                  <Icon className="h-5 w-5" style={{ color }} />
                </div>
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-mist/50">
                  U{String(unit.unit_id).padStart(2, "0")}
                </span>
              </div>
              <h3 className="mt-3 text-sm font-semibold leading-snug text-white">{unit.name}</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-mist/55" dir="rtl">{desc}</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-safe" />
                <span className="text-[10px] uppercase tracking-[0.18em] text-mist/40">{unit.status}</span>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
