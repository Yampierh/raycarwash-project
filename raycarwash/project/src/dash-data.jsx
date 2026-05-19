// Mock data for the provider dashboard
const dashData = {
  me: {
    name: "Marcus Tate",
    initials: "MT",
    role: "Detailer · L3 Pro",
    tier: "Gold",
    rating: 4.92,
    jobs: 312,
    onTime: 98,
    member: "Jan 2024",
  },

  kpis: {
    todayJobs: { v: 5, delta: 2, deltaPct: 25 },
    todayEarnings: { v: 412, delta: 78, deltaPct: 18 },
    weekEarnings: { v: 2148, delta: 312, deltaPct: 15 },
    monthEarnings: { v: 8642, delta: -428, deltaPct: -4.7 },
    rating: { v: 4.92, delta: 0.04 },
    completion: { v: 98, delta: 1 },
    avgTicket: { v: 153, delta: 7 },
    response: { v: 1.4, unit: "min", delta: -0.3 },
  },

  // 14d daily earnings (base + tips)
  earnings14d: [
    { d: "Apr 21", base: 124, tips: 18 },
    { d: "Apr 22", base: 198, tips: 24 },
    { d: "Apr 23", base: 0,   tips: 0  },
    { d: "Apr 24", base: 247, tips: 35 },
    { d: "Apr 25", base: 312, tips: 48 },
    { d: "Apr 26", base: 198, tips: 22 },
    { d: "Apr 27", base: 0,   tips: 0  },
    { d: "Apr 28", base: 178, tips: 28 },
    { d: "Apr 29", base: 224, tips: 31 },
    { d: "Apr 30", base: 156, tips: 14 },
    { d: "May 1",  base: 268, tips: 42 },
    { d: "May 2",  base: 312, tips: 56 },
    { d: "May 3",  base: 198, tips: 18 },
    { d: "May 4",  base: 0,   tips: 0  },
  ],

  incoming: [
    {
      id: "JR-1042",
      svc: "Full detail · interior + ext",
      addOns: ["Pet hair", "Clay bar"],
      car: "2022 Honda Pilot",
      where: "Aboite Twp · 4.2 mi",
      when: "Today · 2:00 PM",
      pay: 179,
      duration: 150,
      customer: "Sarah K.",
      rating: 5.0,
      new: true,
      surge: false,
    },
    {
      id: "JR-1041",
      svc: "Exterior wash",
      addOns: ["Tire shine"],
      car: "2019 Subaru Outback",
      where: "Northwood · 2.1 mi",
      when: "Tomorrow · 9:30 AM",
      pay: 65,
      duration: 60,
      customer: "Dan O.",
      rating: 4.8,
      new: true,
      surge: true,
    },
    {
      id: "JR-1040",
      svc: "Interior deep clean",
      addOns: [],
      car: "2021 Toyota Tacoma",
      where: "Waynedale · 5.6 mi",
      when: "Thu, May 8 · 11:00 AM",
      pay: 119,
      duration: 105,
      customer: "Maria L.",
      rating: 4.9,
      new: false,
      surge: false,
    },
  ],

  // today's route
  route: [
    { id: 1, time: "8:30", who: "Jennifer R.", svc: "Full detail · Q5",     where: "Lakeside",   pay: 179, status: "done" },
    { id: 2, time: "11:00", who: "Brad T.",     svc: "Exterior · F-150",     where: "Aboite",     pay: 65,  status: "done" },
    { id: 3, time: "1:00",  who: "Aisha M.",    svc: "Interior · Model Y",   where: "Glenwood",   pay: 119, status: "now" },
    { id: 4, time: "3:30",  who: "Chris P.",    svc: "Full detail · CR-V",   where: "Southwest",  pay: 149, status: "next" },
    { id: 5, time: "6:00",  who: "Linda H.",    svc: "Express wash · Civic", where: "Waynedale",  pay: 49,  status: "next" },
  ],

  customers: [
    { id: 1, name: "Jennifer Reyes",  init: "JR", color: "#2563eb", visits: 14, total: 1986, last: "Today",      vip: true,  loc: "Lakeside",  phone: "(260) 555-0142" },
    { id: 2, name: "Brad Thompson",   init: "BT", color: "#059669", visits: 8,  total: 720,  last: "Today",      vip: false, loc: "Aboite",    phone: "(260) 555-0134" },
    { id: 3, name: "Aisha Martin",    init: "AM", color: "#dc2626", visits: 6,  total: 894,  last: "2d ago",     vip: false, loc: "Glenwood",  phone: "(260) 555-0188" },
    { id: 4, name: "Chris Park",      init: "CP", color: "#7c3aed", visits: 4,  total: 596,  last: "1w ago",     vip: false, loc: "Southwest", phone: "(260) 555-0103" },
    { id: 5, name: "Linda Hoffmann",  init: "LH", color: "#ea580c", visits: 22, total: 2740, last: "3d ago",     vip: true,  loc: "Waynedale", phone: "(260) 555-0177" },
    { id: 6, name: "Marcus Ortiz",    init: "MO", color: "#0891b2", visits: 3,  total: 357,  last: "2w ago",     vip: false, loc: "Lakeside",  phone: "(260) 555-0116" },
    { id: 7, name: "Sarah Klein",     init: "SK", color: "#be185d", visits: 11, total: 1645, last: "Tomorrow",   vip: true,  loc: "Aboite",    phone: "(260) 555-0125" },
    { id: 8, name: "Daniel Okafor",   init: "DO", color: "#65a30d", visits: 7,  total: 565,  last: "Tomorrow",   vip: false, loc: "Northwood", phone: "(260) 555-0190" },
  ],

  reviews: [
    {
      id: 1, name: "Jennifer R.", stars: 5, when: "2 days ago", svc: "Full detail",
      body: "Marcus is incredible. Showed up on time, brought his own water hookup, and my Q5 looked better than the day I bought it. Will absolutely book again.",
      reply: "Thanks Jennifer! See you next month for the maintenance wash 🙌",
    },
    {
      id: 2, name: "Brad T.", stars: 5, when: "3 days ago", svc: "Exterior wash",
      body: "Fast and clean. Texted me when he was 10 minutes out, knocked it out in under an hour while I worked from home.",
      reply: null,
    },
    {
      id: 3, name: "Linda H.", stars: 4, when: "1 week ago", svc: "Interior detail",
      body: "Great job overall, but I noticed a couple of streaks on the back windows. He came back the next day to fix it for free which I really appreciated.",
      reply: "Appreciate the patience Linda — we always make it right!",
    },
    {
      id: 4, name: "Aisha M.", stars: 5, when: "1 week ago", svc: "Full detail",
      body: "Worth every penny. The interior smells like a new car again. Booking him for my husband's truck next.",
      reply: null,
    },
    {
      id: 5, name: "Tom W.", stars: 5, when: "2 weeks ago", svc: "Full detail",
      body: "Booked through the app last minute. Marcus picked up within 5 minutes and was at my house the next morning. Service was top tier.",
      reply: "Always happy to help! Thanks for the trust 🚗",
    },
  ],

  services: [
    { id: "s1", name: "Express exterior", price: 49,  dur: 45,  active: true,  feats: ["Hand wash", "Wheels & tires", "Bug & tar removal"], bookings30d: 38 },
    { id: "s2", name: "Interior detail",  price: 89,  dur: 90,  active: true,  feats: ["Full vacuum", "Steam clean", "Leather conditioner", "Cup holders"], bookings30d: 22 },
    { id: "s3", name: "Full detail",      price: 149, dur: 150, active: true,  feats: ["Everything in express + interior", "Hand wax", "Clay bar"], bookings30d: 16, popular: true },
    { id: "s4", name: "Premium ceramic",  price: 299, dur: 240, active: true,  feats: ["Full detail", "12-month ceramic coat", "Paint correction"], bookings30d: 4 },
    { id: "s5", name: "Pet hair removal", price: 35,  dur: 30,  active: true,  feats: ["Add-on only", "Specialty brushes", "Tape extraction"], bookings30d: 11, addon: true },
    { id: "s6", name: "Engine bay clean", price: 0,   dur: 60,  active: false, feats: ["Draft — not yet published"], bookings30d: 0, draft: true },
  ],

  payouts: [
    { d: "May 4, 2026", lbl: "Weekly payout · Chase ••2847",          amt: 1418.20, kind: "out" },
    { d: "May 3, 2026", lbl: "Job · Full detail · Brad T.",            amt: 65.00,   kind: "in" },
    { d: "May 3, 2026", lbl: "Tip · Jennifer R.",                      amt: 22.00,   kind: "in" },
    { d: "May 3, 2026", lbl: "Job · Interior · Aisha M.",              amt: 119.00,  kind: "in" },
    { d: "May 2, 2026", lbl: "Platform fee · 15%",                     amt: 32.40,   kind: "fee" },
    { d: "May 2, 2026", lbl: "Job · Full detail · Chris P.",           amt: 149.00,  kind: "in" },
    { d: "May 2, 2026", lbl: "Job · Express · Linda H.",               amt: 49.00,   kind: "in" },
    { d: "May 1, 2026", lbl: "Supply credit · Microfiber set",         amt: 24.00,   kind: "in" },
    { d: "Apr 28, 2026", lbl: "Weekly payout · Chase ••2847",          amt: 1812.40, kind: "out" },
  ],

  notifs: [
    { id: 1, t: "New job request", b: "Sarah K. · Full detail · $179 · Today 2:00 PM", m: "2 min ago", kind: "brand", unread: true },
    { id: 2, t: "Payout sent", b: "$1,418.20 deposited to Chase ••2847", m: "1 hr ago", kind: "ok", unread: true },
    { id: 3, t: "5★ review from Jennifer R.", b: "“Marcus is incredible. Showed up on time…”", m: "2 hr ago", kind: "ok", unread: true },
    { id: 4, t: "Supplies running low", b: "Wheel cleaner: 1 bottle left. Reorder?", m: "5 hr ago", kind: "warn", unread: false },
    { id: 5, t: "Schedule reminder", b: "Tomorrow you have 4 jobs starting at 8:30 AM", m: "Yesterday", kind: "brand", unread: false },
  ],

  // 7d schedule grid (hours 7..19)
  schedule: (() => {
    // generate fixed mock events
    return [
      { day: 0, start: 8.5, end: 11, label: "Jennifer R.", svc: "Full detail · Q5", type: "ok" },
      { day: 0, start: 11.5, end: 12.5, label: "Brad T.", svc: "Exterior · F-150", type: "ok" },
      { day: 0, start: 13, end: 14.75, label: "Aisha M.", svc: "Interior · Model Y", type: "brand" },
      { day: 0, start: 15.5, end: 18, label: "Chris P.", svc: "Full detail · CR-V", type: "" },
      { day: 0, start: 18, end: 18.75, label: "Linda H.", svc: "Express · Civic", type: "" },
      { day: 1, start: 9.5, end: 10.5, label: "Dan O.", svc: "Exterior · Outback", type: "" },
      { day: 1, start: 11, end: 13.5, label: "Sarah K.", svc: "Full detail · Pilot", type: "" },
      { day: 1, start: 14, end: 16, label: "M. Lopez", svc: "Interior · Tacoma", type: "" },
      { day: 2, start: 9, end: 12, label: "Tom W.", svc: "Premium ceramic · M3", type: "warn" },
      { day: 2, start: 13, end: 15, label: "Hold", svc: "Lunch + travel", type: "ghost" },
      { day: 2, start: 15, end: 17, label: "Available", svc: "open slot", type: "ghost" },
      { day: 3, start: 10, end: 12, label: "Kelly P.", svc: "Full detail · Q3", type: "" },
      { day: 3, start: 14, end: 17, label: "Premium · Wrangler", svc: "Add-ons: 2", type: "" },
      { day: 4, start: 8, end: 10, label: "Day off", svc: "Family", type: "ghost" },
      { day: 5, start: 9, end: 11.5, label: "M. Ortiz", svc: "Full detail · CX-5", type: "" },
      { day: 5, start: 12, end: 14, label: "S. Klein", svc: "Interior · X3", type: "" },
      { day: 5, start: 14.5, end: 17, label: "Available", svc: "open slot", type: "ghost" },
      { day: 6, start: 7, end: 19, label: "Closed", svc: "", type: "ghost" },
    ];
  })(),

  insights: [
    { t: "You earn 24% more on Saturdays", b: "Consider opening 2 more slots Sat morning", icon: "trending" },
    { t: "3 customers haven't rebooked in 60+ days", b: "Send a 'we miss you' offer →", icon: "warn" },
    { t: "Add-on attach rate is 41%", b: "Above platform avg (28%). Keep it up.", icon: "ok" },
  ],
};

window.dashData = dashData;
