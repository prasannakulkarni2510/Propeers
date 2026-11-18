// PACOS contact form -> Google Sheet.
// Paste into Extensions > Apps Script of the sheet that should receive rows,
// set SECRET to the same value as PACOS_CONTACT_SHEET_SECRET, then
// Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
// The web app URL goes into PACOS_CONTACT_SHEET_URL. See docs/CONTACT_FORM.md.

const SECRET = "change-me";
const HEADERS = ["Time", "Name", "Email", "Company", "Message", "Ref", "Page"];

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
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  if (sheet.getLastRow() === 0) sheet.appendRow(HEADERS);
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
