// PACOS contact form and short-link visits -> Google Sheet.
// Paste into Extensions > Apps Script of the sheet that should receive rows,
// set SECRET to the same value as PACOS_CONTACT_SHEET_SECRET, then
// Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
// The web app URL goes into PACOS_CONTACT_SHEET_URL. See docs/CONTACT_FORM.md.
//
// Contact form entries go to the first tab. Clicks on the short links
// (/in, /ig, /r) go to a tab called "Visits", created on the first click.

const SECRET = "change-me";
const CONTACT_HEADERS = ["Time", "Name", "Email", "Company", "Message", "Ref", "Page"];
const VISIT_HEADERS = ["Time", "Source", "Device", "Referrer"];

function doPost(e) {
  let data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return reply({ ok: false, error: "bad json" });
  }
  if (SECRET && data.secret !== SECRET) {
    return reply({ ok: false, error: "forbidden" });
  }
  const book = SpreadsheetApp.getActiveSpreadsheet();
  if (data.kind === "visit") {
    const visits = book.getSheetByName("Visits") || book.insertSheet("Visits");
    if (visits.getLastRow() === 0) visits.appendRow(VISIT_HEADERS);
    visits.appendRow([data.time, data.source, data.device, data.referrer].map(safe));
    return reply({ ok: true });
  }
  const sheet = book.getSheets()[0];
  if (sheet.getLastRow() === 0) sheet.appendRow(CONTACT_HEADERS);
  sheet.appendRow([
    data.time, data.name, data.email, data.company, data.message, data.ref, data.page,
  ].map(safe));
  return reply({ ok: true });
}

// A value starting with = + - @ would run as a formula; store it as text.
function safe(v) {
  const s = String(v == null ? "" : v);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
