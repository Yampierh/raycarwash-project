// Extra icons for the provider dashboard. Reuses <Ic> from icons.jsx
const IconDash = (p) => (
  <Ic {...p} d={<><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></>} />
);
const IconBriefcase = (p) => (
  <Ic {...p} d={<><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M3 13h18"/></>} />
);
const IconChart = (p) => (
  <Ic {...p} d={<><line x1="4" y1="20" x2="4" y2="4"/><line x1="4" y1="20" x2="20" y2="20"/><polyline points="8 16 12 10 15 13 20 6"/></>} />
);
const IconUsers = (p) => (
  <Ic {...p} d={<><circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1"/><path d="M16 4a4 4 0 0 1 0 8"/><path d="M22 21v-1a6 6 0 0 0-3-5.2"/></>} />
);
const IconMessageSquare = (p) => (
  <Ic {...p} d={<path d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4Z"/>} />
);
const IconTag = (p) => (
  <Ic {...p} d={<><path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9Z"/><circle cx="8" cy="8" r="1.5"/></>} />
);
const IconSettings = (p) => (
  <Ic {...p} d={<><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.5-2.4.9a7 7 0 0 0-2-1.2L14 3h-4l-.5 2.5a7 7 0 0 0-2 1.2L5 5.8 3 9.3l2 1.5a7 7 0 0 0 0 2.4l-2 1.5 2 3.5 2.5-.9a7 7 0 0 0 2 1.2L10 21h4l.5-2.5a7 7 0 0 0 2-1.2l2.4.9 2-3.5-2-1.5a7 7 0 0 0 .1-1.2Z"/></>} />
);
const IconBell = (p) => (
  <Ic {...p} d={<><path d="M18 16H6a3 3 0 0 0 0 0c1.5 0 2.5-1 2.5-2.5V10a3.5 3.5 0 0 1 7 0v3.5c0 1.5 1 2.5 2.5 2.5Z"/><path d="M10 20a2 2 0 0 0 4 0"/></>} />
);
const IconSearch = (p) => (
  <Ic {...p} d={<><circle cx="11" cy="11" r="7"/><line x1="16" y1="16" x2="21" y2="21"/></>} />
);
const IconHelp = (p) => (
  <Ic {...p} d={<><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.5-2.5 2-2.5 3.5"/><circle cx="12" cy="16.5" r="0.5" fill="currentColor"/></>} />
);
const IconLogOut = (p) => (
  <Ic {...p} d={<><path d="M9 5H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h4"/><polyline points="14 8 19 12 14 16"/><line x1="19" y1="12" x2="9" y2="12"/></>} />
);
const IconFilter = (p) => (
  <Ic {...p} d={<polygon points="3 4 21 4 14 13 14 19 10 21 10 13"/>} />
);
const IconUpload = (p) => (
  <Ic {...p} d={<><path d="M3 16v3a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3"/><polyline points="8 8 12 4 16 8"/><line x1="12" y1="4" x2="12" y2="16"/></>} />
);
const IconDownload = (p) => (
  <Ic {...p} d={<><path d="M3 16v3a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3"/><polyline points="8 12 12 16 16 12"/><line x1="12" y1="4" x2="12" y2="16"/></>} />
);
const IconChevronRight = (p) => (
  <Ic {...p} d={<polyline points="9 6 15 12 9 18"/>} />
);
const IconChevronLeft = (p) => (
  <Ic {...p} d={<polyline points="15 6 9 12 15 18"/>} />
);
const IconMore = (p) => (
  <Ic {...p} d={<><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/></>} />
);
const IconArrowUpRight = (p) => (
  <Ic {...p} d={<><line x1="6" y1="18" x2="18" y2="6"/><polyline points="9 6 18 6 18 15"/></>} />
);
const IconArrowDownRight = (p) => (
  <Ic {...p} d={<><line x1="6" y1="6" x2="18" y2="18"/><polyline points="9 18 18 18 18 9"/></>} />
);
const IconX = (p) => (
  <Ic {...p} d={<><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></>} />
);
const IconPlay = (p) => (
  <Ic {...p} d={<polygon points="7 4 19 12 7 20" fill="currentColor"/>} />
);
const IconPause = (p) => (
  <Ic {...p} d={<><rect x="6" y="4" width="4" height="16" fill="currentColor"/><rect x="14" y="4" width="4" height="16" fill="currentColor"/></>} />
);
const IconCamera = (p) => (
  <Ic {...p} d={<><path d="M3 8a2 2 0 0 1 2-2h2.5l1.5-2h6l1.5 2H19a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><circle cx="12" cy="13" r="3.5"/></>} />
);
const IconFile = (p) => (
  <Ic {...p} d={<><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><polyline points="14 3 14 9 20 9"/></>} />
);
const IconMail = (p) => (
  <Ic {...p} d={<><rect x="3" y="5" width="18" height="14" rx="2"/><polyline points="3 7 12 13 21 7"/></>} />
);
const IconPin = (p) => (
  <Ic {...p} d={<><path d="M12 22s-7-7-7-12a7 7 0 0 1 14 0c0 5-7 12-7 12Z"/><circle cx="12" cy="10" r="2.5"/></>} />
);
const IconWaze = (p) => (
  <Ic {...p} d={<><circle cx="12" cy="12" r="9"/><polyline points="9 12 11 14 15 9"/></>} />
);
const IconRoute = (p) => (
  <Ic {...p} d={<><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M6 9v4a4 4 0 0 0 4 4h4"/></>} />
);
const IconShoppingBag = (p) => (
  <Ic {...p} d={<><path d="M6 7h12l-1 13a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2Z"/><path d="M9 7V5a3 3 0 0 1 6 0v2"/></>} />
);
const IconAlertTriangle = (p) => (
  <Ic {...p} d={<><path d="M12 3 2 21h20Z"/><line x1="12" y1="10" x2="12" y2="15"/><circle cx="12" cy="18" r="0.5" fill="currentColor"/></>} />
);
const IconRefresh = (p) => (
  <Ic {...p} d={<><polyline points="20 4 20 10 14 10"/><polyline points="4 20 4 14 10 14"/><path d="M20 10A8 8 0 0 0 6.3 6.3L4 8.5"/><path d="M4 14a8 8 0 0 0 13.7 3.7L20 15.5"/></>} />
);
const IconTrending = (p) => (
  <Ic {...p} d={<><polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/></>} />
);
const IconLink = (p) => (
  <Ic {...p} d={<><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7L11 7"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7L13 17"/></>} />
);
const IconShare = (p) => (
  <Ic {...p} d={<><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><line x1="8" y1="11" x2="16" y2="7"/><line x1="8" y1="13" x2="16" y2="17"/></>} />
);

Object.assign(window, {
  IconDash, IconBriefcase, IconChart, IconUsers, IconMessageSquare, IconTag,
  IconSettings, IconBell, IconSearch, IconHelp, IconLogOut, IconFilter,
  IconUpload, IconDownload, IconChevronRight, IconChevronLeft, IconMore,
  IconArrowUpRight, IconArrowDownRight, IconX, IconPlay, IconPause,
  IconCamera, IconFile, IconMail, IconPin, IconWaze, IconRoute,
  IconShoppingBag, IconAlertTriangle, IconRefresh, IconTrending,
  IconLink, IconShare,
});
