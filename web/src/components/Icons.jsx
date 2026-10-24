// Small inline SVG icons (no icon library to install). All use currentColor, so they follow
// the text colour in light and dark mode.
const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export const PlusIcon = () => (
  <svg {...base}><path d="M12 5v14M5 12h14" /></svg>
);
export const ChatIcon = () => (
  <svg {...base}><path d="M21 12a8 8 0 0 1-11.8 7L4 20l1-4.6A8 8 0 1 1 21 12z" /></svg>
);
export const TrashIcon = () => (
  <svg {...base}><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" /></svg>
);
export const PencilIcon = () => (
  <svg {...base}><path d="M4 20h4L19 9l-4-4L4 16z" /></svg>
);
export const ClipIcon = () => (
  <svg {...base}><path d="M21 11.5 12.5 20a5 5 0 0 1-7-7L14 4.5a3.5 3.5 0 0 1 5 5L10.5 18a2 2 0 0 1-3-3L15 7.5" /></svg>
);
export const SendIcon = () => (
  <svg {...base}><path d="M12 19V5M5 12l7-7 7 7" /></svg>
);
export const StopIcon = () => (
  <svg {...base} fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
);
export const FileIcon = () => (
  <svg {...base}><path d="M14 3H6v18h12V7z" /><path d="M14 3v4h4" /></svg>
);
export const CloseIcon = () => (
  <svg {...base} width={14} height={14}><path d="M6 6l12 12M18 6 6 18" /></svg>
);
export const MenuIcon = () => (
  <svg {...base}><path d="M4 6h16M4 12h16M4 18h16" /></svg>
);
export const CheckIcon = () => (
  <svg {...base} width={14} height={14}><path d="M5 12l5 5L20 7" /></svg>
);
export const AlertIcon = () => (
  <svg {...base} width={14} height={14}><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></svg>
);
export const SunIcon = () => (
  <svg {...base} width={16} height={16}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
);
export const MoonIcon = () => (
  <svg {...base} width={16} height={16}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
);
export const BookIcon = () => (
  <svg {...base} width={16} height={16}><path d="M4 5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2z" /><path d="M4 20a2 2 0 0 0 2 2h13v-4" /></svg>
);
export const LockIcon = () => (
  <svg {...base} width={14} height={14}><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>
);
export const LinkIcon = () => (
  <svg {...base} width={12} height={12}><path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6" /></svg>
);
export const LogoIcon = () => (
  <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
    <rect width="32" height="32" rx="8" fill="var(--accent)" />
    <path d="M10 8h8l4 4v12H10z" fill="white" />
    <path d="M13 16h6M13 19.5h6" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);
