import { downloadIcs, googleCalendarUrl } from "../lib/calendar";

// Opens Google Calendar with the event filled in (the operator saves it
// there), or downloads it for Outlook / Apple Calendar.
export default function CalendarButtons({ event, label = "Add to Google Calendar" }) {
  if (!event?.date) return null;
  return (
    <span className="cal-buttons">
      <a className="btn btn-ghost btn-sm" href={googleCalendarUrl(event)} target="_blank" rel="noopener noreferrer">
        📅 {label}
      </a>
      <button className="btn btn-ghost btn-sm" title="Download for Outlook or Apple Calendar"
        onClick={() => downloadIcs(event)}>
        .ics
      </button>
    </span>
  );
}
