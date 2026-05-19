// Inline lucide-style icons, 24x24 viewBox, currentColor stroke.
const Ic = ({ d, fill, w = 1.75, size = 18, ...rest }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill={fill ? "currentColor" : "none"}
    stroke="currentColor"
    strokeWidth={w}
    strokeLinecap="round"
    strokeLinejoin="round"
    {...rest}
  >
    {d}
  </svg>
);

const IconMapPin = (p) => (
  <Ic {...p} d={<><path d="M20 10c0 7-8 12-8 12s-8-5-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></>} />
);
const IconClock = (p) => (
  <Ic {...p} d={<><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></>} />
);
const IconSparkles = (p) => (
  <Ic {...p} d={<><path d="m12 3 1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6Z"/><path d="M18 16v3M20 17.5h-3"/><path d="M5 17v2M6 18H4"/></>} />
);
const IconCheck = (p) => (
  <Ic {...p} d={<polyline points="4 12 10 18 20 6"/>} />
);
const IconArrowRight = (p) => (
  <Ic {...p} d={<><line x1="4" y1="12" x2="20" y2="12"/><polyline points="14 6 20 12 14 18"/></>} />
);
const IconStar = (p) => (
  <Ic {...p} d={<polygon points="12 3 14.5 9 21 9.5 16 14 17.5 20.5 12 17 6.5 20.5 8 14 3 9.5 9.5 9"/>} fill />
);
const IconShield = (p) => (
  <Ic {...p} d={<><path d="M12 3 4 6v6c0 5 3.5 8.5 8 9 4.5-.5 8-4 8-9V6Z"/><polyline points="9 12 11 14 15 10"/></>} />
);
const IconUserCheck = (p) => (
  <Ic {...p} d={<><circle cx="9" cy="8" r="4"/><path d="M3 21v-1a6 6 0 0 1 6-6h2"/><polyline points="15 14 17 16 21 12"/></>} />
);
const IconWallet = (p) => (
  <Ic {...p} d={<><path d="M3 7a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M16 12h4"/><circle cx="17" cy="12" r="0.5" fill="currentColor"/></>} />
);
const IconCalendar = (p) => (
  <Ic {...p} d={<><rect x="3" y="5" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/></>} />
);
const IconWrench = (p) => (
  <Ic {...p} d={<path d="M14.7 6.3a4 4 0 1 1 3 3l-9 9-3 1 1-3Z"/>} />
);
const IconPhone = (p) => (
  <Ic {...p} d={<rect x="6" y="3" width="12" height="18" rx="2.5"/>} />
);
const IconCar = (p) => (
  <Ic {...p} d={<><path d="M3 13 5 8h14l2 5"/><path d="M3 13v5h2v-1h14v1h2v-5"/><circle cx="7" cy="15.5" r="1.5"/><circle cx="17" cy="15.5" r="1.5"/></>} />
);
const IconDroplet = (p) => (
  <Ic {...p} d={<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z"/>} />
);
const IconPlus = (p) => (
  <Ic {...p} d={<><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>} />
);
const IconMenu = (p) => (
  <Ic {...p} d={<><line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/></>} />
);
const IconChevronDown = (p) => (
  <Ic {...p} d={<polyline points="6 9 12 15 18 9"/>} />
);
const IconApple = (p) => (
  <Ic {...p} d={<><path d="M16 13c0-3 2.4-4.3 2.5-4.4-1.4-2-3.4-2.3-4.2-2.3-1.8-.2-3.4 1-4.3 1s-2.3-1-3.7-1c-1.9 0-3.7 1.1-4.7 2.8-2 3.4-.5 8.4 1.5 11.2 1 1.4 2.1 2.9 3.6 2.8 1.4-.1 2-.9 3.7-.9s2.2.9 3.7.9c1.5 0 2.5-1.4 3.5-2.7 1.1-1.6 1.5-3.1 1.6-3.2-.1 0-3-1.2-3-4.2Z" fill="currentColor"/><path d="M13.8 4.5c.7-.9 1.2-2.1 1.1-3.3-1 0-2.3.7-3 1.5-.7.8-1.3 2-1.1 3.2 1.1.1 2.3-.6 3-1.4Z" fill="currentColor"/></>} />
);
const IconAndroid = (p) => (
  <Ic {...p} d={<><path d="M5 10h14v8a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2Z"/><path d="M5 10c0-3 3-6 7-6s7 3 7 6"/><line x1="9" y1="6" x2="8" y2="4"/><line x1="15" y1="6" x2="16" y2="4"/><circle cx="9" cy="8" r="0.5" fill="currentColor"/><circle cx="15" cy="8" r="0.5" fill="currentColor"/></>} />
);

Object.assign(window, {
  IconMapPin, IconClock, IconSparkles, IconCheck, IconArrowRight,
  IconStar, IconShield, IconUserCheck, IconWallet, IconCalendar,
  IconWrench, IconPhone, IconCar, IconDroplet, IconPlus, IconMenu,
  IconChevronDown, IconApple, IconAndroid,
});
