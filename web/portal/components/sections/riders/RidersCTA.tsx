import { useTranslations } from "next-intl";
import { Apple, Play, Check } from "lucide-react";

export default function RidersCTA() {
  const t = useTranslations("ridersPage.cta");
  const footnotes = t.raw("footnotes") as string[];
  const appStore = process.env.NEXT_PUBLIC_APPSTORE_URL ?? "#";
  const playStore = process.env.NEXT_PUBLIC_PLAYSTORE_URL ?? "#";

  return (
    <section id="book" className="bg-white py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-ink-900 via-ink-900 to-brand-900 p-8 text-white shadow-2xl md:p-14">
          <div
            className="absolute inset-0 -z-0 opacity-30"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, #71717a 1px, transparent 0)",
              backgroundSize: "32px 32px",
            }}
          />
          <div className="relative grid gap-10 md:grid-cols-[1.3fr_0.7fr] md:items-center">
            <div>
              <span className="text-sm font-semibold uppercase tracking-wider text-brand-400">
                {t("kicker")}
              </span>
              <h2 className="mt-3 font-display text-4xl font-bold tracking-tight md:text-5xl">
                {t("h2")}
              </h2>
              <p className="mt-4 max-w-lg text-lg text-ink-300">{t("sub")}</p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <a
                  href={appStore}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-ink-900 shadow-sm transition hover:bg-ink-100"
                >
                  <Apple className="size-4" />
                  {t("appStore")}
                </a>
                <a
                  href={playStore}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  <Play className="size-4" />
                  {t("playStore")}
                </a>
              </div>
              <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-400">
                {footnotes.map((f) => (
                  <span key={f} className="inline-flex items-center gap-1.5">
                    <Check className="size-3 text-brand-400" strokeWidth={3} />
                    {f}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex justify-center">
              <div className="rounded-2xl bg-white p-5 shadow-2xl">
                <QRCode />
                <div className="mt-3 text-center">
                  <div className="text-sm font-bold text-ink-900">
                    {t("qrTitle")}
                  </div>
                  <p className="mt-1 max-w-[200px] text-xs text-ink-500">
                    {t("qrBody")}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function QRCode() {
  return (
    <svg viewBox="0 0 100 100" width="140" height="140">
      <rect width="100" height="100" fill="white" />
      {Array.from({ length: 12 }).flatMap((_, r) =>
        Array.from({ length: 12 }).map((_, c) => {
          const fill = (r + c * 3 + r * c) % 3 === 0;
          return fill ? (
            <rect
              key={`${r}-${c}`}
              x={c * 8 + 2}
              y={r * 8 + 2}
              width="6"
              height="6"
              fill="#09090b"
            />
          ) : null;
        }),
      )}
      <rect x="2" y="2" width="22" height="22" fill="white" stroke="#09090b" strokeWidth="3" />
      <rect x="76" y="2" width="22" height="22" fill="white" stroke="#09090b" strokeWidth="3" />
      <rect x="2" y="76" width="22" height="22" fill="white" stroke="#09090b" strokeWidth="3" />
      <rect x="9" y="9" width="8" height="8" fill="#09090b" />
      <rect x="83" y="9" width="8" height="8" fill="#09090b" />
      <rect x="9" y="83" width="8" height="8" fill="#09090b" />
    </svg>
  );
}
