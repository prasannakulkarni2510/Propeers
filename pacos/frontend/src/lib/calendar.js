// "Add to calendar" without any calendar access: a Google Calendar link that
// opens the event pre-filled (the operator saves it there), and an .ics file
// for Outlook / Apple Calendar. PACOS never writes to a calendar itself.
import { localToday } from "./dates";

const compact = (iso) => iso.replaceAll("-", "");
const nextDay = (iso) => {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + 1);
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
};
// Local wall-clock start/end as YYYYMMDDTHHMMSS (no zone: Google gets ctz,
// .ics treats it as the viewer's local time).
function span(date, time, minutes) {
  const start = new Date(`${date}T${time}:00`);
  const end = new Date(start.getTime() + minutes * 60000);
  const fmt = (d) =>
    `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}` +
    `T${String(d.getHours()).padStart(2, "0")}${String(d.getMinutes()).padStart(2, "0")}00`;
  return [fmt(start), fmt(end)];
}

// event: { title, details, date: "YYYY-MM-DD", time?: "HH:MM", minutes? }
export function googleCalendarUrl(ev) {
  const dates = ev.time
    ? span(ev.date, ev.time, ev.minutes || 60).join("/")
    : `${compact(ev.date)}/${nextDay(ev.date)}`;
  const q = new URLSearchParams({ action: "TEMPLATE", text: ev.title, dates, details: ev.details || "" });
  if (ev.time) q.set("ctz", Intl.DateTimeFormat().resolvedOptions().timeZone);
  return `https://calendar.google.com/calendar/render?${q}`;
}

const icsText = (s) =>
  String(s || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
// RFC 5545: lines over 75 octets continue on the next line after a space.
const fold = (line) => {
  const out = [];
  for (let i = 0; i < line.length; i += 73) out.push((i ? " " : "") + line.slice(i, i + 73));
  return out.join("\r\n");
};

export function icsFile(ev) {
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
  const when = ev.time
    ? (([s, e]) => [`DTSTART:${s}`, `DTEND:${e}`])(span(ev.date, ev.time, ev.minutes || 60))
    : [`DTSTART;VALUE=DATE:${compact(ev.date)}`, `DTEND;VALUE=DATE:${nextDay(ev.date)}`];
  return [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PACOS//Chat//EN", "BEGIN:VEVENT",
    `UID:${Date.now()}-${Math.random().toString(36).slice(2)}@pacos`, `DTSTAMP:${stamp}`,
    ...when, `SUMMARY:${icsText(ev.title)}`, `DESCRIPTION:${icsText(ev.details)}`,
    "END:VEVENT", "END:VCALENDAR",
  ].map(fold).join("\r\n") + "\r\n";
}

export function downloadIcs(ev) {
  const url = URL.createObjectURL(new Blob([icsFile(ev)], { type: "text/calendar" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `${ev.title.replace(/[^\w -]+/g, "").trim().slice(0, 60) || "event"}.ics`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const who = (lead) =>
  [lead.full_name, lead.company_name].filter(Boolean).join(" at ") || "a lead";

export function interviewEvent(lead, date, time, note) {
  return {
    title: `Interview: ${who(lead)}`,
    date,
    time: time || "",
    details: [lead.job_title && `Role: ${lead.job_title}`, note, "Added from PACOS."]
      .filter(Boolean).join("\n"),
  };
}

// Leads waiting on a reply: an all-day reminder on the follow-up date, or
// today if that has already passed.
export function followUpEvent(lead) {
  const due = lead.follow_up_due;
  if (!due || lead.status !== "sent") return null;
  const today = localToday();
  const sent = lead.outreach_sent_date
    ? `Sent ${lead.outreach_sent_date}${lead.channel ? ` by ${lead.channel}` : ""}, no reply yet.`
    : "";
  const email = lead.email || lead.predicted_email || "";
  return {
    title: `Follow up: ${who(lead)}`,
    date: due < today ? today : due,
    details: [sent, email && `Email: ${email}`, "Added from PACOS."].filter(Boolean).join("\n"),
  };
}
