export default function GlobalNotFound() {
  return (
    <html lang="en">
      <body className="bg-white text-zinc-900 antialiased">
        <div className="flex min-h-screen items-center justify-center px-6">
          <div className="text-center">
            <p className="text-sm font-semibold uppercase tracking-wider text-zinc-500">
              404
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">
              Page not found
            </h1>
            <p className="mt-3 text-zinc-600">
              The page you were looking for doesn&rsquo;t exist.
            </p>
            <a
              href="/en"
              className="mt-8 inline-flex rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white"
            >
              Back to home
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
