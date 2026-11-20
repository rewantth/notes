# Troubleshooting

Find the message or symptom you are seeing. Each entry says what it means and what to do.

**On this page**

- [The page](#the-page)
- [The update run on GitHub](#the-update-run-on-github)
- [Phone alerts](#phone-alerts)
- [The login step on your computer](#the-login-step-on-your-computer)
- [The results look wrong](#the-results-look-wrong)

---

## The page

### "That isn't the right passphrase."

The passphrase must be exactly the one stored in the `DASHBOARD_PASSPHRASE` secret in GitHub, including capital letters and spaces. Check that Caps Lock is off.

If you changed the secret recently, the page still holds data locked with the old one until the next update. Open the **Actions** tab on GitHub and run **Update dashboard** once, then try again.

If you have forgotten the passphrase, it cannot be recovered. Set a new `DASHBOARD_PASSPHRASE` secret and run the update.

### "The data file is not there yet."

No update has finished successfully, so there is nothing to show. Open the **Actions** tab on GitHub and look at the latest run. A green tick means wait a minute and reload. A red cross means the run failed, so see the next section.

### The page says 404 or "There isn't a GitHub Pages site here."

Pages is not switched on, or it is set to the wrong source. In your repository open **Settings**, then **Pages**, and set **Source** to **GitHub Actions**. Then run the update again. The page address is `https://YOURNAME.github.io/REPOSITORY-NAME/`.

### The page opens, but the data is old

The top of the page says when your inbox was last checked. If that was many hours ago, scheduled runs have stopped. See "Scheduled runs stopped" below.

### It shows no applications at all

The page opened and decrypted, so the lock is fine. Possible reasons:

- Your application emails are in a different Gmail account from the one you logged in with.
- The emails are in Spam or Trash. Those are skipped.
- They are older than 365 days.
- The senders or wording are ones the rules do not recognise. Pick one email and compare it with the rules in [Customizing](CUSTOMIZING.md).

---

## The update run on GitHub

Open the **Actions** tab, click the failed run, then click the red step to see its message.

### "The secret X is not set."

One of the four secrets is missing. Go to **Settings**, then **Secrets and variables**, then **Actions**. You need exactly `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` and `DASHBOARD_PASSPHRASE`. Names must match letter for letter, and the values must have no spaces or quote marks around them.

### `invalid_grant`, "Token has been expired or revoked"

Google no longer accepts your key. The usual cause is that the Google app was still in "Testing" mode, which ends the login after 7 days. Do [Part 7 of the setup guide](SETUP.md#part-7-make-the-login-last). Other causes are removing the app at <https://myaccount.google.com/permissions>, or changing your Google password. In every case, run `get_token.py` again and replace the `GMAIL_REFRESH_TOKEN` secret.

### "Gmail API has not been used in project … or it is disabled"

The Gmail API is not switched on. Open <https://console.cloud.google.com/apis/library/gmail.googleapis.com>, check the right project is selected at the top, and click **Enable**. Then run the update again.

### "Quota exceeded" or `rateLimitExceeded`

Gmail briefly slowed the program down. It already retries on its own. If the run still fails, run it again a few minutes later.

### "Get Pages site failed" or "Not Found" in the Pages step

Pages is not switched on. In **Settings**, then **Pages**, set **Source** to **GitHub Actions**, then run the update again.

### Scheduled runs stopped

GitHub pauses scheduled jobs in a project that has had no activity for 60 days. Open the **Actions** tab, choose **Update dashboard**, and click the button to enable it again. On a fresh fork, scheduled jobs are off until you click "I understand my workflows, go ahead and enable them" on the Actions tab.

### The run succeeded, but nothing changed on the page

Reload with Ctrl+F5 (Cmd+Shift+R on a Mac). Then tap **Refresh** on the page itself. The browser can hold on to an older copy for a few minutes.

---

## Phone alerts

### The test alert never arrives

- Subscribe in the ntfy app **before** sending the test, using exactly the same topic as the `NTFY_TOPIC` secret. One wrong character means a different channel.
- Check the secret is named `NTFY_TOPIC` and the topic is at least 8 characters, using only letters, numbers, `-` and `_`.
- Make sure you ticked **Also send a test phone alert** when you ran the workflow by hand.
- On a phone, check that ntfy is allowed to send notifications and is not restricted in battery settings.

### The alert arrives but makes no sound

The sound is a phone setting, not something this project controls. Check that the phone is not on silent or Do Not Disturb. On Android, open **Settings**, then **Apps**, then **ntfy**, then **Notifications**, and make sure the category for that alert level has a sound and is not set to "Silent". On iPhone, open **Settings**, then **Notifications**, then **ntfy**, and turn **Sounds** on. To give each level a different sound, see [setup, part 8](SETUP.md#part-8-phone-alerts-optional).

### I never get alerts for real emails

Alerts only fire for new screening calls, tests, interviews, offers and rejections, never for confirmations. The very first run after you switch alerts on sends nothing, because there is nothing to compare with yet. Emails more than three days old do not trigger an alert. If a real reply did not trigger one, check that the page lists it. If the page does not show it either, the wording is not recognised yet. See [Customizing](CUSTOMIZING.md).

### Two alerts for the same email

This can happen if a run failed after sending the alert and before publishing, so the next run sees the email as new again. It is harmless.

---

## The login step on your computer

### `python` or `pip` is "not recognised"

On Windows, try `py` instead of `python`, and `py -m pip install -r requirements.txt` instead of `pip install ...`. If neither works, reinstall Python from <https://www.python.org/downloads/> and tick **Add python.exe to PATH** on the first screen. Then open a new terminal window.

### "Error 403: access_denied" or "has not completed the Google verification process"

Your Gmail address is not on the list of test users. In Google Cloud open <https://console.cloud.google.com/auth/audience>, click **Add users** under **Test users**, add your address and click **Save**. Make sure it appears in the list.

### "Google hasn't verified this app"

This is expected. Click **Advanced**, then **Go to job-tracker (unsafe)**. You made the app yourself, so you are the only person who will ever see this screen.

### The browser says "This site can't be reached" or "localhost refused to connect" after you allow access

The helper must still be running in the terminal when you click Allow, and the browser must be on the same computer. Do not close the terminal window. Run `python get_token.py credentials.json` again and use the newest link it prints.

### "No refresh token returned"

Google only hands out the key the first time. Go to <https://myaccount.google.com/permissions>, remove `job-tracker`, then run `get_token.py` again.

### Nothing opens, and no link is printed

Look for a line starting `Please visit this URL`. Copy that whole address into your browser by hand.

### `set-secrets.ps1` says "To get started with GitHub CLI, please run: gh auth login"

The GitHub command-line tool is not signed in. Run `gh auth login`, choose GitHub.com and sign in with your browser, then run the script again. Or skip the script and add the secrets on the GitHub website, as in [Part 5 of the setup guide](SETUP.md#part-5-store-the-key-and-your-passphrase-in-github).

---

## The results look wrong

### A row has an orange "?" after the company

The company or role was guessed from the email, because the usual patterns did not match. Click the **Gmail** link on that row to read the original. If it keeps happening for one sender, add a rule for it. See [Customizing](CUSTOMIZING.md).

### The wrong site is shown

The site comes from the first email's sender address. If an application was made on one site and then answered by the company directly, it stays under the first site. If a site is missing from the list, add it as shown in [Customizing](CUSTOMIZING.md).

### One application appears twice, or two have been merged

Emails are grouped by company name and role. If a company writes its name differently in different emails, or the role is missing from one, they can split. Merging is a matter of improving the name matching in `classify.py`.

### A rejection or an interview invitation was not picked up

The wording was probably one the rules do not know yet. Add a phrase for it. [Customizing](CUSTOMIZING.md) shows how, in about five minutes. Run the tests afterwards to make sure nothing else changed.

### A newsletter or job alert shows up as an application

Add its wording to the noise list in `classify.py`. See [Customizing](CUSTOMIZING.md).
