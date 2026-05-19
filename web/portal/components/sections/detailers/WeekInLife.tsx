import { useTranslations } from "next-intl";

interface Job {
  t: string;
  svc: string;
  pay: number;
}

interface Day {
  d: string;
  date: string;
  jobs?: Job[];
  off?: boolean;
}

const SAMPLE: Day[] = [
  {
    d: "Mon",
    date: "Jun 3",
    jobs: [
      { t: "9:00", svc: "Exterior · M3", pay: 49 },
      { t: "11:30", svc: "Full · Civic", pay: 149 },
      { t: "3:00", svc: "Interior · F-150", pay: 89 },
    ],
  },
  {
    d: "Tue",
    date: "Jun 4",
    jobs: [
      { t: "10:00", svc: "Full · CX-5", pay: 149 },
      { t: "2:00", svc: "Exterior · Camry", pay: 49 },
    ],
  },
  {
    d: "Wed",
    date: "Jun 5",
    jobs: [
      { t: "9:00", svc: "Interior · Pilot", pay: 89 },
      { t: "1:00", svc: "Full · Wrangler", pay: 189 },
      { t: "4:30", svc: "Ext+Int · Sienna", pay: 169 },
    ],
  },
  { d: "Thu", date: "Jun 6", off: true },
  {
    d: "Fri",
    date: "Jun 7",
    jobs: [
      { t: "8:30", svc: "Full · Model Y", pay: 159 },
      { t: "12:00", svc: "Full · Tacoma", pay: 189 },
      { t: "4:00", svc: "Interior · Outback", pay: 89 },
    ],
  },
  {
    d: "Sat",
    date: "Jun 8",
    jobs: [
      { t: "9:00", svc: "Full · CR-V", pay: 149 },
      { t: "1:00", svc: "Full · Q5", pay: 179 },
    ],
  },
  { d: "Sun", date: "Jun 9", off: true },
];

export default function WeekInLife() {
  const t = useTranslations("detailersPage.week");

  const total = SAMPLE.reduce(
    (s, d) => s + (d.jobs?.reduce((a, j) => a + j.pay, 0) || 0),
    0,
  );
  const jobsCount = SAMPLE.reduce((s, d) => s + (d.jobs?.length || 0), 0);
  const daysWorked = SAMPLE.filter((d) => !d.off).length;

  return (
    <section id="week" className="bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              {t("kicker")}
            </span>
            <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
              {t("h2")}
            </h2>
            <p className="mt-4 text-lg text-ink-600">{t("sub")}</p>
          </div>
          <div className="rounded-2xl border border-ink-150 bg-ink-50 px-5 py-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-500">
              {t("totalLbl")}
            </div>
            <div className="mt-1 font-display text-3xl font-bold text-ink-900">
              ${total.toLocaleString()}
            </div>
            <div className="mt-0.5 text-xs text-ink-500">
              {t("totalSub", { jobs: jobsCount, days: daysWorked })}
            </div>
          </div>
        </div>

        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-7">
          {SAMPLE.map((d) => {
            const dayTotal = d.jobs?.reduce((a, j) => a + j.pay, 0) || 0;
            return (
              <div
                key={d.d}
                className={`flex flex-col rounded-2xl border p-4 ${
                  d.off
                    ? "border-dashed border-ink-200 bg-ink-50/40"
                    : "border-ink-150 bg-white shadow-sm"
                }`}
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-display text-base font-bold text-ink-900">
                    {d.d}
                  </span>
                  <span className="font-mono text-[10px] text-ink-400">
                    {d.date}
                  </span>
                </div>
                {d.off ? (
                  <div className="mt-6 flex flex-1 flex-col items-center justify-center text-center">
                    <span className="rounded-full bg-ink-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-ink-700">
                      {t("offTag")}
                    </span>
                    <span className="mt-2 text-[11px] text-ink-500">
                      {t("offMeta")}
                    </span>
                  </div>
                ) : (
                  <>
                    <ul className="mt-3 space-y-1.5">
                      {d.jobs?.map((j, i) => (
                        <li
                          key={i}
                          className="rounded-lg bg-ink-50 px-2 py-1.5 text-[11px]"
                        >
                          <div className="font-mono font-semibold text-ink-700">
                            {j.t}
                          </div>
                          <div className="text-ink-600">{j.svc}</div>
                          <div className="mt-0.5 font-bold text-ink-900">
                            ${j.pay}
                          </div>
                        </li>
                      ))}
                    </ul>
                    <div className="mt-auto border-t border-ink-100 pt-2 text-right">
                      <div className="font-display text-sm font-bold text-ink-900">
                        ${dayTotal}
                      </div>
                      <div className="text-[10px] text-ink-500">
                        {d.jobs?.length}{" "}
                        {d.jobs?.length === 1 ? "job" : "jobs"}
                      </div>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
