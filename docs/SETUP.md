# Setup guide

This guide gets Job Hunt running for your Gmail. You do not need to know how to code. You will click through a few websites and copy and paste some text. Allow 30 to 45 minutes. You only do it once.

Each part ends with a **Checkpoint**, which is what you should see before moving on. If a checkpoint does not match, stop there and look in [Troubleshooting](TROUBLESHOOTING.md).

**Parts**

1. [Make your own copy on GitHub](#part-1-make-your-own-copy-on-github)
2. [Put the files on your computer](#part-2-put-the-files-on-your-computer)
3. [Give the program read-only access to Gmail](#part-3-give-the-program-read-only-access-to-gmail)
4. [Log in once to get a key](#part-4-log-in-once-to-get-a-key)
5. [Store the key and your passphrase in GitHub](#part-5-store-the-key-and-your-passphrase-in-github)
6. [Run it for the first time](#part-6-run-it-for-the-first-time)
7. [Make the login last](#part-7-make-the-login-last)
8. [Phone alerts (optional)](#part-8-phone-alerts-optional)
9. [Afterwards](#afterwards)
10. [Words used in this guide](#words-used-in-this-guide)

Nothing here costs money. At no point do you need to enter a card number. Google Cloud may show a banner about free credits or a free trial. Ignore it every time.

---

## Part 1: Make your own copy on GitHub

GitHub is the website that will run the program for you and host the page.

1. Go to <https://github.com> and create a free account if you do not have one. Remember your username. This guide writes it as `YOURNAME`.
2. Open this project's page on GitHub and click **Fork** at the top right, then **Create fork**. A fork is your own copy. Keep the name `job-tracker`. You now have `github.com/YOURNAME/job-tracker`.
3. Click the **Actions** tab in your copy. GitHub switches off automatic jobs on copies, so you will see a green button saying something like "I understand my workflows, go ahead and enable them". Click it.
4. Click **Settings**, then **Pages** in the left menu. Under **Build and deployment**, set **Source** to **GitHub Actions**.

**Checkpoint:** the Pages settings show "GitHub Actions" as the source.

---

## Part 2: Put the files on your computer

You need the files on one computer for a single login step in Part 4.

1. On your copy's main page, click the green **Code** button, then **Download ZIP**.
2. Unzip it somewhere easy to find, such as your Documents folder. You will get a folder named `job-tracker-main`.
3. Install Python if you do not have it. Go to <https://www.python.org/downloads/>, download the latest version, and run the installer. **On Windows, tick "Add python.exe to PATH" on the first screen.** This matters.
4. Open a terminal inside the folder. A terminal is a window where you type commands.
   - **Windows:** open the folder in File Explorer, click the address bar at the top, type `powershell` and press Enter.
   - **Mac:** open the Terminal app, type `cd ` (with a space), drag the folder into the window and press Enter.
5. Type this and press Enter. It installs the small helpers the program uses.

```
pip install -r requirements.txt
```

You will see a lot of text scroll past. A note saying a newer version of pip is available is harmless.

**Checkpoint:** the command finished and you can type again, with no red "ERROR" at the end. If Windows says `pip` is not recognised, close the window, reinstall Python with the PATH box ticked, and try again.

---

## Part 3: Give the program read-only access to Gmail

Google needs you to create a small "app" so it knows who is asking for your mail. It is free and it is yours. Only you will ever use it.

1. Go to <https://console.cloud.google.com/> and sign in with **the Gmail account that receives your job emails**. Accept the terms if it asks.
2. At the top of the page, click the project picker (it may say "Select a project"), then **New project**. Name it `job-tracker` and click **Create**. Wait a few seconds, then make sure `job-tracker` is the selected project.
3. Open <https://console.cloud.google.com/apis/library/gmail.googleapis.com> and click **Enable**.
4. Open <https://console.cloud.google.com/auth/overview> and click **Get started**. Fill it in as follows.
   - **App information:** the name is `job-tracker`. For the support email, pick your address from the list.
   - **Audience:** choose **External**.
   - **Contact information:** type your email address.
   - **Finish:** tick the box to agree, click **Continue**, then **Create**.
5. In the left menu click **Audience**. Under **Test users**, click **Add users**, type your Gmail address and click **Save**. If nothing seems to happen, click Save once more. Your address should appear in the list.
6. In the left menu click **Clients**, then **Create client**. For **Application type** choose **Desktop app**, and click **Create**.
7. A box appears with a **Download JSON** button. **Click it straight away.** Google shows the secret only once. If you close the box without downloading, delete that client and create another.
8. Rename the downloaded file to `credentials.json` and move it into the folder from Part 2.

**Checkpoint:** `credentials.json` sits in the same folder as `get_token.py`.

Keep this file private. Never put it on GitHub, in an email or in a chat.

---

## Part 4: Log in once to get a key

This step proves to Google that it really is you, once, and gives the program a key it can keep using.

1. In the terminal from Part 2, type this and press Enter. If Windows says `python` is not recognised, try `py` in its place.

```
python get_token.py credentials.json
```

2. The program prints a long web address that starts with `https://accounts.google.com`. If a browser window does not open by itself, copy the address into a browser.
3. Choose your Google account.
4. Google will say **"Google hasn't verified this app."** That is normal, because you made the app yourself. Click **Advanced**, then **Go to job-tracker (unsafe)**.
5. Google lists what the app can do. It should say **view your email messages and settings**, which is read-only. Click **Continue** or **Allow**.
6. The browser shows that the sign-in is complete, and the terminal prints "Done".

**Checkpoint:** a new file called `github-secrets.txt` appeared in the folder. It holds three lines that start with `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` and `GMAIL_REFRESH_TOKEN`. Treat it like a password.

---

## Part 5: Store the key and your passphrase in GitHub

GitHub has a locked cabinet called Secrets. The program takes the values out of it while it runs, and nobody can read them back.

**Choose your passphrase first.** It is what unlocks your dashboard, and it can be anything you like. Make it long. Four or five unrelated words work well and are easy to remember. Do not reuse a password from elsewhere. If you lose it, you can set a new one, but you cannot recover the old one.

Now add four secrets.

1. Open your copy on GitHub and go to **Settings**, then **Secrets and variables**, then **Actions**.
2. Click **New repository secret**.
3. Open `github-secrets.txt` in Notepad or any text editor. Each line looks like `NAME=value`. The **name** is what comes before the first `=` sign and the **value** is everything after it.
4. Add the first secret. Type the name in **Name** and paste the value in **Secret**, with no extra spaces or quote marks. Click **Add secret**.
5. Repeat for the other two lines from the file.
6. Add a fourth secret. The name is `DASHBOARD_PASSPHRASE` and the value is your passphrase.

| Name | Value |
|---|---|
| `GMAIL_CLIENT_ID` | from `github-secrets.txt` |
| `GMAIL_CLIENT_SECRET` | from `github-secrets.txt` |
| `GMAIL_REFRESH_TOKEN` | from `github-secrets.txt` |
| `DASHBOARD_PASSPHRASE` | the passphrase you chose |

**Checkpoint:** the page lists four secrets with exactly these names. The names must match letter for letter.

Then delete `github-secrets.txt`. Keep `credentials.json` for now, because Part 7 uses it again.

*Windows shortcut:* if you have the GitHub command-line tool (`gh`) signed in, `set-secrets.ps1` does steps 2 to 6 for you and asks you to type your passphrase. Run `powershell -ExecutionPolicy Bypass -File .\set-secrets.ps1`.

---

## Part 6: Run it for the first time

1. In your copy on GitHub, click **Actions**.
2. Click **Update dashboard** in the left list, then **Run workflow**, then the green **Run workflow** button.
3. Wait about two minutes and refresh. A green tick means it worked. A red cross means something is wrong. Click the run to see why, and check [Troubleshooting](TROUBLESHOOTING.md).
4. Open `https://YOURNAME.github.io/job-tracker/` in your browser. Type your passphrase.

**Checkpoint:** you see your own applications. If the page says the data file is not there yet, wait a minute and try again.

From now on it updates by itself about every 10 minutes. GitHub sometimes starts a run several minutes late, so allow 10 to 20 minutes for news to appear. It is not instant, because Gmail does not tell GitHub when mail arrives. To refresh sooner, run the workflow by hand as above.

---

## Part 7: Make the login last

There is one more step that is easy to skip and costly to skip. While your Google app is in "Testing" mode, Google ends the login after **7 days**. The page would then quietly stop updating. To prevent that, you move the app to "In production" and log in again. This is still only for you.

1. On GitHub, open your copy's file `site/privacy.html` and click the pencil icon to edit it. Near the bottom, change the contact link so it points at your own project, and save ("Commit changes"). This is the privacy page Google asks for.
2. In Google Cloud open <https://console.cloud.google.com/auth/branding>. Fill in these fields, using your own GitHub name:
   - **Application home page:** `https://YOURNAME.github.io/job-tracker/`
   - **Application privacy policy link:** `https://YOURNAME.github.io/job-tracker/privacy.html`
   - **Authorized domains:** click **Add domain** and type `YOURNAME.github.io`
3. Click **Save**.
4. Open **Audience** in the left menu, click **Publish app**, and confirm. The status changes to **In production**. Google's wording says the app is "available to any user with a Google Account". Nobody else has your login file, so only you can use it.
5. Do Part 4 again to get a fresh key: run `python get_token.py credentials.json` and click through as before. The old key was made while the app was in Testing, so it would still expire.
6. Open the new `github-secrets.txt`, and in GitHub replace the secret `GMAIL_REFRESH_TOKEN` with the new value. Open the secret, click **Update**, paste, save. The other two values stay the same.
7. Delete `github-secrets.txt` again. Then run the workflow once more (Part 6, steps 1 and 2).

**Checkpoint:** the Audience page in Google Cloud says "In production", and the new run has a green tick.

If Google refuses the `github.io` domain, the project still works. You will need to repeat Part 4 and update `GMAIL_REFRESH_TOKEN` once a week.

---

## Part 8: Phone alerts (optional)

The page updates about every 10 minutes, but you only see it when you open it. Alerts buzz your phone when something that matters arrives: a recruiter call, a test, an interview, an offer, or a rejection. Plain confirmations never trigger one.

Alerts use **ntfy**, a free notification service that needs no account. Please know what it sees. Each alert is a short line such as "1 interview invite, 1 rejection". It never contains a company name or any email text, so you open the page to see which one. ntfy still learns that something arrived and when. If you would rather not use an outside service, skip this part. Everything else works without it.

1. Install the free **ntfy** app on your phone (Google Play, the App Store or F-Droid).
2. Choose a topic name. A topic is the private channel your phone listens to, and anyone who knows its name can read the alerts, so make it long and random. Something like `jobhunt-` followed by 32 random letters and numbers is right. Do not use your name or anything guessable.
3. In the ntfy app, tap **+**, choose **Subscribe to topic**, type the topic name and subscribe.
4. In GitHub, open **Settings**, then **Secrets and variables**, then **Actions**, and add a secret named `NTFY_TOPIC` with the topic name as its value.
5. Send a test. Open the **Actions** tab, click **Update dashboard**, click **Run workflow**, tick **Also send a test phone alert**, and run it. Within a couple of minutes your phone should show **three** test alerts: "loud", "medium" and "quiet". They are there so you can choose a sound for each kind (see below).

*Windows shortcut:* if the GitHub command-line tool (`gh`) is signed in, `setup-alerts.ps1` makes a random topic, stores the secret and offers to send the test. Run `powershell -ExecutionPolicy Bypass -File .\setup-alerts.ps1`.

**Checkpoint:** the three test alerts arrived on your phone. Tapping one opens your dashboard.

**Give each kind its own sound.** Alerts come in three levels:

| Level | What it is for |
|---|---|
| Loud | Interview invites and offers |
| Medium | Recruiter call requests and tests |
| Quiet | Rejections |

On an **Android** phone, each level is a separate notification category, so each can have its own sound. Open the phone's **Settings**, then **Apps**, then **ntfy**, then **Notifications**. You will see categories named after the priority levels, which appear after the first alert of each level arrives (the three test alerts create them). Tap one, tap **Sound**, and pick a tone. Choose something distinctive for the loud level. For that level you can also switch on "Override Do Not Disturb" so interview invites still ring at night.

On an **iPhone**, ntfy uses one sound for everything. You can turn it on or off under **Settings**, then **Notifications**, then **ntfy**, but you can't pick a different tone for each kind. The loudest level still stands out with its title: "Job Hunt: interview or offer".

How it behaves:

- Each run compares itself with the previous one, so you get an alert only for emails that are new. The first run after you switch alerts on sends nothing.
- Emails older than three days never trigger an alert, so a rule change cannot flood you with old news.
- If your passphrase changes, the next run cannot compare and sends nothing. The one after that works normally.
- To stop alerts, delete the `NTFY_TOPIC` secret.

---

## Afterwards

**Add it to your phone's home screen.** Open the page in your phone's browser, open the browser menu or the share button, and choose "Add to Home Screen". Tick "Remember me on this device" on the lock screen so you do not retype the passphrase.

**Change your passphrase.** Replace the `DASHBOARD_PASSPHRASE` secret in GitHub, run the workflow once, then use **Lock** on the page and enter the new one.

**Stop it.** Remove the app at <https://myaccount.google.com/permissions>, disable the workflow under the Actions tab, and delete the GitHub project. To remove everything, also delete the Google Cloud project from <https://console.cloud.google.com/cloud-resource-manager>.

---

## Words used in this guide

**Repository (repo).** A project's folder on GitHub.

**Fork.** Your own copy of someone else's repository.

**GitHub Actions.** GitHub's service for running a program automatically on a schedule. The "workflow" is the instruction sheet it follows, kept in `.github/workflows/update.yml`.

**GitHub Pages.** GitHub's free hosting for a web page.

**Secret.** A value stored in GitHub that programs can use but nobody can read.

**Token (refresh token).** A long string that proves to Google that you allowed the program to read your mail. It is what `get_token.py` fetches.

**Passphrase.** The phrase you choose to lock and unlock the dashboard.

**Terminal.** A window where you type commands. On Windows it is called PowerShell.

**OAuth.** The name for the "Allow this app to read your mail" screen Google shows. You never give the program your Google password.
