export function PageHeader({
  title,
  sub,
  action,
}: {
  title: string;
  sub?: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight text-zinc-900">
          {title}
        </h1>
        {sub && <p className="mt-2 text-sm text-zinc-600">{sub}</p>}
      </div>
      {action}
    </header>
  );
}
