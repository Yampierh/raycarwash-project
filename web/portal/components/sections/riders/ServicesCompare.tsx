import { useTranslations } from "next-intl";
import { Check, Clock, Minus } from "lucide-react";

type Service = { name: string; price: string; duration: string; tag: string };
type Row = { label: string; values: boolean[] };
type Addon = { name: string; price: string };

export default function ServicesCompare() {
  const t = useTranslations("ridersPage.compare");
  const services = t.raw("services") as Service[];
  const rows = t.raw("rows") as Row[];
  const addons = t.raw("addons") as Addon[];

  return (
    <section id="services" className="bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="max-w-2xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
            {t("kicker")}
          </span>
          <h2 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink-900 md:text-5xl">
            {t("h2")}
          </h2>
          <p className="mt-4 text-lg text-ink-600">{t("sub")}</p>
        </div>

        <div className="mt-12 overflow-hidden rounded-3xl border border-ink-150 bg-white shadow-sm">
          <table className="w-full">
            <thead>
              <tr>
                <th className="w-1/3 bg-ink-50/60 p-5 text-left"></th>
                {services.map((s, i) => {
                  const featured = i === 2;
                  return (
                    <th
                      key={s.name}
                      className={`p-5 text-left ${
                        featured ? "bg-ink-900 text-white" : "bg-ink-50/60"
                      }`}
                    >
                      <div
                        className={`text-[10px] font-semibold uppercase tracking-wider ${
                          featured ? "text-brand-300" : "text-brand-600"
                        }`}
                      >
                        {s.tag}
                      </div>
                      <div
                        className={`mt-2 font-display text-lg font-bold ${
                          featured ? "text-white" : "text-ink-900"
                        }`}
                      >
                        {s.name}
                      </div>
                      <div
                        className={`mt-2 flex items-baseline gap-1.5 ${
                          featured ? "text-white" : "text-ink-900"
                        }`}
                      >
                        <span
                          className={`text-[10px] font-medium uppercase tracking-wider ${
                            featured ? "text-white/60" : "text-ink-500"
                          }`}
                        >
                          {t("fromLabel")}
                        </span>
                        <span className="font-display text-2xl font-bold">
                          {s.price}
                        </span>
                      </div>
                      <div
                        className={`mt-1 flex items-center gap-1 text-[11px] ${
                          featured ? "text-white/60" : "text-ink-500"
                        }`}
                      >
                        <Clock className="size-3" />
                        {s.duration}
                      </div>
                      <a
                        href="#book"
                        className={`mt-4 inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                          featured
                            ? "bg-white text-ink-900 hover:bg-ink-100"
                            : "border border-ink-200 bg-white text-ink-900 hover:bg-ink-50"
                        }`}
                      >
                        {t("bookCta")}
                      </a>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-150">
              {rows.map((row) => (
                <tr key={row.label}>
                  <td className="p-4 text-sm font-medium text-ink-700">
                    {row.label}
                  </td>
                  {row.values.map((on, i) => {
                    const featured = i === 2;
                    return (
                      <td
                        key={i}
                        className={`p-4 ${featured ? "bg-ink-900/[0.02]" : ""}`}
                      >
                        {on ? (
                          <Check
                            className="size-4 text-brand-600"
                            strokeWidth={2.5}
                          />
                        ) : (
                          <Minus className="size-4 text-ink-300" />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-12 rounded-3xl border border-ink-150 bg-ink-50 p-6 md:p-10">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="text-sm font-semibold uppercase tracking-wider text-brand-600">
                {t("addonsKicker")}
              </span>
              <h3 className="mt-2 font-display text-2xl font-bold text-ink-900">
                {t("addonsTitle")}
              </h3>
            </div>
          </div>
          <ul className="mt-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {addons.map((a) => (
              <li
                key={a.name}
                className="flex items-center justify-between rounded-xl border border-ink-150 bg-white px-4 py-3 text-sm"
              >
                <span className="font-medium text-ink-900">{a.name}</span>
                <span className="font-mono text-xs font-bold text-ink-700">
                  {a.price}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
