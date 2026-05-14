"use client";

import { useTranslations } from "next-intl";
import { User, Wrench } from "lucide-react";
import clsx from "clsx";
import { useAuthStore, type RoleIntent } from "@/lib/store/auth";

type Props = {
  /** Translation key under "roleToggle" — usually "signInAs" or "signUpAs". */
  labelKey: "signInAs" | "signUpAs";
};

export default function RoleToggle({ labelKey }: Props) {
  const t = useTranslations("roleToggle");
  const roleIntent = useAuthStore((s) => s.roleIntent);
  const setRoleIntent = useAuthStore((s) => s.setRoleIntent);
  const selected: RoleIntent = roleIntent ?? "client";

  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
        {t(labelKey)}
      </p>
      <div
        role="tablist"
        aria-label={t(labelKey)}
        className="grid grid-cols-2 gap-2 rounded-xl border border-zinc-200 bg-zinc-50 p-1"
      >
        <Pill
          icon={<User className="size-4" />}
          label={t("client")}
          selected={selected === "client"}
          onClick={() => setRoleIntent("client")}
        />
        <Pill
          icon={<Wrench className="size-4" />}
          label={t("provider")}
          selected={selected === "detailer"}
          onClick={() => setRoleIntent("detailer")}
        />
      </div>
    </div>
  );
}

function Pill({
  icon,
  label,
  selected,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={selected}
      onClick={onClick}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
        selected
          ? "bg-white text-zinc-900 shadow-sm ring-1 ring-brand-500/50"
          : "text-zinc-600 hover:text-zinc-900"
      )}
    >
      {icon}
      {label}
    </button>
  );
}
