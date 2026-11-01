// The operator's local calendar date (YYYY-MM-DD). toISOString() alone is
// UTC, which is still "yesterday" for the first hours of an Indian morning.
export function localToday() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}
