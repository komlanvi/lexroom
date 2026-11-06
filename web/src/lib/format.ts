// Every date is shown in the plan's time zone, whatever the browser's.
// Month names are fixed here: locale data differs between runtimes (e.g. "Sep" vs "Sept").
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const LONG_MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const romeParts = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Rome",
  year: "numeric",
  day: "numeric",
  month: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

function inRome(iso: string) {
  const parts = Object.fromEntries(romeParts.formatToParts(new Date(iso)).map((part) => [part.type, part.value]));
  return {
    day: Number(parts.day),
    month: MONTHS[Number(parts.month) - 1],
    year: parts.year,
    time: `${parts.hour}:${parts.minute}`,
    seconds: parts.second,
  };
}

/** "6 Nov" */
export function formatDay(iso: string): string {
  const { day, month } = inRome(iso);
  return `${day} ${month}`;
}

/** "1 Dec, 00:00" */
export function formatDayTime(iso: string): string {
  const { day, month, time } = inRome(iso);
  return `${day} ${month}, ${time}`;
}

/** "1 Dec 2026, 00:00" */
export function formatDateTime(iso: string): string {
  const { day, month, year, time } = inRome(iso);
  return `${day} ${month} ${year}, ${time}`;
}

/** "14:10:05" */
export function formatTime(iso: string): string {
  const { time, seconds } = inRome(iso);
  return `${time}:${seconds}`;
}

/** "2026-11" → "November" */
export function formatPeriod(period: string): string {
  return LONG_MONTHS[Number(period.slice(5, 7)) - 1];
}

/** Seconds as "m:ss", e.g. 72 → "1:12". */
export function formatElapsed(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function firstName(fullName: string): string {
  return fullName.split(" ")[0];
}
