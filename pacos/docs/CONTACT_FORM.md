# Contact form → Google Sheet

Visitors can leave their name, email, company and a short message. The form is a
"Hiring, or want to talk?" link under the login card and a "Get in touch" form on
the About page. Each submission is added as a row in a Google Sheet. The form only
appears when `PACOS_CONTACT_SHEET_URL` is set, so local and exe use never shows it.

Each row has these columns: Time (UTC), Name, Email, Company, Message, Ref, Page. Ref
is the `?ref=` tag from the link the visitor came in on (for example `linkedin`), and
Page is `login` or `about`.

## Setup (about 5 minutes)

1. Create a new Google Sheet, for example "PACOS contacts".
2. In the sheet, open **Extensions → Apps Script**, delete the starter code and paste in
   [`contact-form-apps-script.gs`](contact-form-apps-script.gs).
3. Change `SECRET` from `change-me` to a long random string and save.
4. Click **Deploy → New deployment**, choose the type **Web app**, and set:
   - Execute as: **Me**
   - Who has access: **Anyone**

   Click **Deploy**, approve the access request for your own account, then copy the
   **Web app URL** (it ends in `/exec`).
5. On Render, open the service and go to **Environment**. Add:
   - `PACOS_CONTACT_SHEET_URL` = the web app URL
   - `PACOS_CONTACT_SHEET_SECRET` = the same string as `SECRET`

   Save. Render restarts the service.
6. Open the site logged out, click "Hiring, or want to talk?", send a test entry, and
   check that a row appears in the sheet. Delete the test row afterwards.

You can also put the two keys in `pacos/.env` to try the form locally.

## Notes

- "Who has access: Anyone" only means anyone can call the script. The secret stops
  anyone except PACOS from adding rows. Nobody can read the sheet through the
  script, and the sheet stays private to your Google account.
- If you edit the script, use **Deploy → Manage deployments → Edit → New version**
  so the URL stays the same.
- The backend allows 5 messages per visitor every 10 minutes and quietly drops
  entries from bots (a hidden honeypot field).
- If the form says "Couldn't save your details", the script is usually not deployed
  for "Anyone" or the secret doesn't match.
