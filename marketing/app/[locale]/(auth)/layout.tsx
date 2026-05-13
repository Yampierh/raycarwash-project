import { Link } from "@/i18n/navigation";
import LanguageSwitcher from "@/components/LanguageSwitcher";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-zinc-900 text-sm font-bold text-white">
              R
            </span>
            <span className="font-display text-lg font-bold tracking-tight text-zinc-900">
              RayCarWash
            </span>
          </Link>
          <LanguageSwitcher />
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
