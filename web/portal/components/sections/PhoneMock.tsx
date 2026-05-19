"use client";

import { Battery, Wifi, Signal, MapPin, Star } from "lucide-react";

type Variant = "client" | "detailer";

interface PhoneMockProps {
  variant: Variant;
  step: number;
  size?: "md" | "lg";
}

export function PhoneMock({ variant, step, size = "md" }: PhoneMockProps) {
  const widthClass = size === "lg" ? "max-w-[300px]" : "max-w-[280px]";

  return (
    <div
      className={`relative mx-auto aspect-[9/19] w-full ${widthClass} overflow-hidden rounded-[2.5rem] border-[10px] border-ink-900 bg-ink-900 shadow-phone`}
    >
      <div className="absolute left-1/2 top-2 z-20 h-6 w-32 -translate-x-1/2 rounded-b-2xl bg-ink-900" />
      <div className="absolute inset-x-6 top-2 z-10 flex items-center justify-between text-[10px] font-semibold text-white">
        <span>9:38</span>
        <span className="flex items-center gap-1">
          <Signal className="size-3" />
          <Wifi className="size-3" />
          <Battery className="size-3" />
        </span>
      </div>
      <div className="absolute inset-0 z-0 bg-gradient-to-br from-brand-500 via-brand-600 to-ink-900">
        {variant === "client" ? (
          <ClientScreen step={step} />
        ) : (
          <DetailerScreen step={step} />
        )}
      </div>
    </div>
  );
}

function ClientScreen({ step }: { step: number }) {
  return (
    <div className="absolute inset-x-4 top-12 space-y-3">
      {step === 0 && <ClientBook />}
      {step === 1 && <ClientEnroute />}
      {step === 2 && <ClientInProgress />}
      {step === 3 && <ClientComplete />}
    </div>
  );
}

function ClientBook() {
  return (
    <div className="ray-fade space-y-3">
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">
          Pick a service
        </div>
        <div className="mt-2 grid grid-cols-3 gap-1.5">
          <div className="rounded-lg bg-ink-100 p-2 text-[10px] font-medium text-ink-700">
            Exterior
          </div>
          <div className="rounded-lg bg-brand-600 p-2 text-[10px] font-semibold text-white">
            Full detail
          </div>
          <div className="rounded-lg bg-ink-100 p-2 text-[10px] font-medium text-ink-700">
            Interior
          </div>
        </div>
      </div>
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">
            Quote
          </div>
          <div className="font-display text-base font-bold text-ink-900">
            from $149
          </div>
        </div>
        <div className="mt-1.5 text-[10px] text-ink-600">
          Flat-rate · Final quote in-app
        </div>
        <button className="mt-3 w-full rounded-lg bg-ink-900 py-2 text-[11px] font-semibold text-white">
          Confirm booking
        </button>
      </div>
    </div>
  );
}

function ClientEnroute() {
  return (
    <div className="ray-fade space-y-3">
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="flex items-center gap-2">
          <div className="size-9 rounded-full bg-gradient-to-br from-brand-500 to-brand-700" />
          <div className="flex-1">
            <div className="text-[11px] font-semibold text-ink-900">
              Detailer en route
            </div>
            <div className="text-[9px] text-ink-500">
              <Star className="mr-0.5 inline size-2.5" />
              Highly rated · Verified
            </div>
          </div>
          <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-700">
            ETA soon
          </span>
        </div>
      </div>
      <div className="relative aspect-square overflow-hidden rounded-2xl bg-white/95 p-2 shadow-lg">
        <svg viewBox="0 0 100 100" className="h-full w-full" preserveAspectRatio="none">
          <rect width="100" height="100" fill="#f4f4f5" />
          <path
            d="M5 80 Q35 65 50 70 T95 35"
            stroke="#2563eb"
            strokeWidth="2"
            fill="none"
            strokeDasharray="3 3"
          />
          <circle cx="5" cy="80" r="4" fill="#2563eb" />
          <circle cx="95" cy="35" r="5" fill="#09090b">
            <animate
              attributeName="r"
              from="3"
              to="8"
              dur="1.8s"
              repeatCount="indefinite"
            />
          </circle>
          <text
            x="50"
            y="55"
            fontSize="6"
            textAnchor="middle"
            fontFamily="ui-monospace, monospace"
            fontWeight="700"
            fill="#09090b"
          >
            12 MIN
          </text>
        </svg>
      </div>
    </div>
  );
}

function ClientInProgress() {
  return (
    <div className="ray-fade space-y-3">
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">
            In progress
          </div>
          <span className="flex items-center gap-1 text-[9px] font-semibold text-red-600">
            <span className="size-1.5 rounded-full bg-red-500" />
            Live
          </span>
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-100">
          <div className="h-full w-2/3 rounded-full bg-gradient-to-r from-brand-500 to-brand-600" />
        </div>
        <div className="mt-1.5 flex justify-between text-[9px] text-ink-500">
          <span>Exterior · 100%</span>
          <span>Interior · 60%</span>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-1.5">
        <div className="aspect-square rounded-lg bg-gradient-to-br from-ink-200 to-ink-300 shadow-md" />
        <div className="aspect-square rounded-lg bg-gradient-to-br from-brand-100 to-brand-200 shadow-md" />
        <div className="aspect-square rounded-lg bg-gradient-to-br from-ink-100 to-ink-200 shadow-md" />
      </div>
    </div>
  );
}

function ClientComplete() {
  return (
    <div className="ray-fade space-y-3">
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
            ✓ Complete
          </div>
          <div className="font-display text-base font-bold text-ink-900">$149</div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-1.5">
          <div className="aspect-video rounded-lg bg-gradient-to-br from-ink-300 to-ink-400 p-1 text-[8px] text-white">
            Before
          </div>
          <div className="aspect-video rounded-lg bg-gradient-to-br from-brand-300 to-brand-500 p-1 text-[8px] text-white">
            After
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <div className="flex gap-0.5 text-yellow-400">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star key={i} className="size-3 fill-current" />
            ))}
          </div>
          <button className="rounded-md bg-ink-900 px-2.5 py-1 text-[10px] font-semibold text-white">
            Add tip
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailerScreen({ step }: { step: number }) {
  return (
    <div className="absolute inset-x-4 top-12 space-y-3">
      {step === 0 && <DetJobOffer />}
      {step === 1 && <DetSchedule />}
      {step === 2 && <DetEarnings />}
      {step === 3 && <DetProfile />}
    </div>
  );
}

function DetJobOffer() {
  return (
    <div className="ray-fade space-y-3">
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-brand-700">
            Job offered
          </div>
          <span className="flex items-center gap-1 text-[9px] font-semibold text-brand-700">
            <span className="size-1.5 animate-pulse rounded-full bg-brand-500" />
            New
          </span>
        </div>
        <div className="mt-2 font-display text-sm font-bold text-ink-900">
          Full detail · Civic
        </div>
        <div className="mt-1 flex items-center gap-1 text-[10px] text-ink-500">
          <MapPin className="size-2.5" />
          2.1 mi · Today 2:30 PM
        </div>
        <div className="mt-3 flex items-center justify-between rounded-lg bg-brand-50 px-2.5 py-2">
          <span className="text-[10px] font-semibold text-brand-700">
            Pays
          </span>
          <span className="font-display text-base font-bold text-brand-700">
            $149
          </span>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-1.5">
          <button className="rounded-lg bg-ink-100 py-1.5 text-[10px] font-semibold text-ink-700">
            Decline
          </button>
          <button className="rounded-lg bg-ink-900 py-1.5 text-[10px] font-semibold text-white">
            Accept
          </button>
        </div>
      </div>
    </div>
  );
}

function DetSchedule() {
  return (
    <div className="ray-fade space-y-2">
      <div className="rounded-2xl bg-white/95 p-3 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">
            Today
          </div>
          <span className="text-[9px] font-semibold text-emerald-700">
            4 stops
          </span>
        </div>
        <div className="mt-2 space-y-1">
          {[
            { t: "9:00", svc: "Exterior · M3", p: "$49" },
            { t: "11:30", svc: "Full · Civic", p: "$149" },
            { t: "2:00", svc: "Interior · F-150", p: "$89" },
            { t: "4:30", svc: "Full · Sienna", p: "$169" },
          ].map((j, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-lg bg-ink-50 px-2 py-1.5"
            >
              <div>
                <div className="text-[9px] font-semibold text-ink-900">{j.t}</div>
                <div className="text-[8px] text-ink-500">{j.svc}</div>
              </div>
              <div className="text-[10px] font-bold text-ink-900">{j.p}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DetEarnings() {
  return (
    <div className="ray-fade space-y-3">
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">
          This week
        </div>
        <div className="mt-1 font-display text-2xl font-bold text-ink-900">
          $1,840
        </div>
        <div className="text-[10px] font-semibold text-emerald-600">
          ▲ trending up
        </div>
        <div className="mt-3 flex items-end gap-1">
          {[40, 65, 30, 80, 55, 90, 70].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-gradient-to-t from-brand-400 to-brand-600"
              style={{ height: `${h * 0.6}px` }}
            />
          ))}
        </div>
        <div className="mt-1 flex justify-between text-[8px] text-ink-400">
          <span>M</span>
          <span>T</span>
          <span>W</span>
          <span>T</span>
          <span>F</span>
          <span>S</span>
          <span>S</span>
        </div>
      </div>
      <div className="rounded-2xl bg-white/95 p-3 shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold text-ink-700">
            Cash out
          </span>
          <button className="rounded-md bg-ink-900 px-2.5 py-1 text-[10px] font-semibold text-white">
            $412 →
          </button>
        </div>
      </div>
    </div>
  );
}

function DetProfile() {
  return (
    <div className="ray-fade space-y-3">
      <div className="rounded-2xl bg-white/95 p-3.5 shadow-lg">
        <div className="flex items-center gap-2">
          <div className="size-10 rounded-full bg-gradient-to-br from-brand-500 to-brand-700" />
          <div>
            <div className="text-[11px] font-bold text-ink-900">Marcus T.</div>
            <div className="text-[9px] text-ink-500">
              <Star className="mr-0.5 inline size-2.5 fill-yellow-400 text-yellow-400" />
              Top-rated · Verified pro
            </div>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-1.5 text-center">
          <div className="rounded-lg bg-ink-50 p-1.5">
            <div className="text-[10px] font-bold text-ink-900">★ 4.9</div>
            <div className="text-[8px] text-ink-500">Rating</div>
          </div>
          <div className="rounded-lg bg-ink-50 p-1.5">
            <div className="text-[10px] font-bold text-ink-900">312</div>
            <div className="text-[8px] text-ink-500">Jobs</div>
          </div>
          <div className="rounded-lg bg-ink-50 p-1.5">
            <div className="text-[10px] font-bold text-ink-900">98%</div>
            <div className="text-[8px] text-ink-500">On-time</div>
          </div>
        </div>
      </div>
    </div>
  );
}
