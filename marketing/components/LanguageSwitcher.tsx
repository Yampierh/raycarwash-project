"use client";

import { useLocale } from "next-intl";
import { useRouter, usePathname } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { Globe } from "lucide-react";
import { useState, useRef, useEffect } from "react";

export default function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50"
        aria-label="Change language"
        aria-expanded={open}
      >
        <Globe className="size-3.5" />
        <span className="uppercase">{locale}</span>
      </button>
      {open && (
        <ul
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-32 overflow-hidden rounded-lg border border-zinc-200 bg-white py-1 shadow-lg"
        >
          {routing.locales.map((l) => (
            <li key={l}>
              <button
                type="button"
                onClick={() => {
                  router.replace(pathname, { locale: l });
                  setOpen(false);
                }}
                className={
                  "flex w-full items-center justify-between px-3 py-2 text-sm transition hover:bg-zinc-50 " +
                  (l === locale ? "font-semibold text-zinc-900" : "text-zinc-600")
                }
              >
                <span>{l === "en" ? "English" : "Español"}</span>
                <span className="text-xs uppercase text-zinc-400">{l}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
