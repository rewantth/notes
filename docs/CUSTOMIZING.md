# Customizing

This page is for anyone who wants to change how emails are sorted, add a job site, or understand what the code does. Some comfort with Python helps, but every change here is small.

**On this page**

- [How an email becomes a row](#how-an-email-becomes-a-row)
- [Add a job site](#add-a-job-site)
- [Teach it new wording](#teach-it-new-wording)
- [Run the tests](#run-the-tests)
- [Preview the page without Gmail](#preview-the-page-without-gmail)
- [Settings you can change](#settings-you-can-change)
- [The data file](#the-data-file)
- [How the phone alerts work](#how-the-phone-alerts-work)
- [Changing the look](#changing-the-look)
- [Contributing](#contributing)

---

## How an email becomes a row

All the rules are in `classify.py`. Each email goes through these steps in order.

1. **Find the site.** `detect_portal` looks at the sender's address. Known job boards (the `JOB_BOARDS` table) give their own name, such as `linkedin`. Hiring systems like Greenhouse, Lever and Workday, and company addresses, give `company`, which the page shows as "Company website".
2. **Drop the noise.** Job alerts, "N new jobs for you", profile-view notices, newsletters and similar are discarded. The list is `NOISE_SUBJECT`. A message with "your application" in the subject is kept even if it looks noisy.
3. **Decide the stage.** `detect_stage` checks the subject first and then the first 1,800 characters of the body. It tries the stages in this order and takes the first that matches: Offer, Rejected, Assessment, Screening, Interview, In review. A subject that is plainly a confirmation, such as "Thank you for applying", is Applied even when the body mentions interviews. Subjects that are only updates, such as "Your application to X at Y", are decided by the body.
4. **Check it is about a job.** Mail that is not from a job board must mention something job-related (`JOBISH`). That keeps "Your loan application has been received" out.
5. **Find the company and role.** `extract_company_role` tries patterns written for LinkedIn subjects, then general subject patterns, then the body, and finally the sender's name or domain. If the company had to be guessed, the row gets the orange question mark.
6. **Group into applications.** `build_applications` puts emails together by company and role, so a confirmation, a call and a rejection become one row. The row's status is the latest stage, and a final Offer or Rejected sticks. The site shown is the site of the first email.

The rules are ordinary regular expressions in the `_RX` table. Nothing is learned or sent anywhere.

---

## Add a job site

Say you want to add a site called Example Jobs, whose emails come from `example-jobs.com`.

1. In `classify.py`, add a line to `JOB_BOARDS`:

```python
"examplejobs": ("Example Jobs", ["example-jobs.com"]),
```

The first word is an id, then the name to show, then the sender domains.

2. Optional: give it a colour. In `site/index.html`, add to the `PORTALS` list near the top of the script:

```js
examplejobs: { label: "Example Jobs", v: "--p-other" },
```

`--p-other` is a neutral grey. For a colour of its own, add a `--p-examplejobs` value next to the other `--p-` colours at the top of the file, once for the light theme and once for the dark one, and use that name instead. A site that is not listed in the page still works. It just appears in grey.

3. Run the tests (below).

---

## Teach it new wording

Say a company words its rejection as "we have gone in a different direction".

1. In `classify.py`, find the `_RX` table and add a phrase to the right stage. Phrases in each stage are separated by `|`.

```python
"Rejected": re.compile(
    r"unfortunately|regret to (?:inform|tell|let)|...|gone in a different direction",
    re.I,
),
```

2. Add a sample email to `CASES` in `tests/test_classify.py` so the wording keeps working:

```python
(CO, "Your application", "We have gone in a different direction.", "Rejected", "company"),
```

3. Run the tests.

Keep a few things in mind. Stages are tried in order, so a phrase in an earlier stage can hide a later one. Phrases are matched anywhere in the subject or the first part of the body, so avoid very short or common ones. If a phrase is too broad, the tests are where you will notice.

---

## Run the tests

From the project folder:

```
python tests/test_classify.py
python tests/test_alerts.py
```

The first checks the email rules and the second checks the phone alerts. Each prints how many checks passed and shows any that failed. It runs without Gmail and without any account. If you have `pytest` installed, running `pytest` also works.

---

## Preview the page without Gmail

`--demo` fills the page with made-up emails, which are also used by the screenshots.

```
pip install -r requirements.txt
DASHBOARD_PASSPHRASE=demo-passphrase-123 python build_data.py --demo
python -m http.server 8765 --directory site
```

Then open <http://localhost:8765> and use the passphrase above. On Windows PowerShell, set the variable first with `$env:DASHBOARD_PASSPHRASE = "demo-passphrase-123"`.

The demo emails are in `demo_messages()` in `build_data.py`.

---

## Settings you can change

| Setting | Where | What it does |
|---|---|---|
| How often it runs | the `cron` line in `.github/workflows/update.yml` | Default is every 10 minutes. GitHub does not run scheduled jobs more often than every 5 minutes, and often starts them a few minutes late. A run takes about 2 minutes. |
| How far back to look | `LOOKBACK_DAYS` environment variable, set under `env:` on the build step of the workflow | Default 365 days. |
| How many emails at most | `MAX_MESSAGES` in `build_data.py` | Default 1,500. |
| Which emails Gmail returns | `GMAIL_QUERY` in `build_data.py` | A normal Gmail search. Widen it if some replies never reach the rules. |
| Password strength | `PBKDF2_ITERATIONS` in `build_data.py` | Default 600,000. Higher is slower to unlock and harder to guess. |

---

## The data file

`build_data.py` writes `site/data.enc.json`, which is not committed. The workflow builds it fresh each run and publishes it with the page.

Locked with a passphrase, it looks like this:

```json
{ "v": 1, "iter": 600000, "salt": "…", "iv": "…", "ct": "…" }
```

The key comes from PBKDF2 with SHA-256 over the passphrase and a random salt. The text is encrypted with AES-256-GCM. The page repeats the same steps with the browser's built-in `crypto.subtle` to unlock it.

Once unlocked, the contents are:

```json
{
  "generated": "2026-11-19T22:30:00+00:00",
  "demo": false,
  "scanned": 116,
  "applications": [
    {
      "company": "Acme",
      "role": "Security Analyst",
      "portal": "linkedin",
      "portalLabel": "LinkedIn",
      "status": "Interview",
      "applied": "2026-11-01T10:00:00+00:00",
      "updated": "2026-11-12T09:30:00+00:00",
      "emails": 3,
      "review": false,
      "link": "https://mail.google.com/mail/u/0/#all/…",
      "subject": "Interview invitation",
      "history": [ { "date": "…", "stage": "Applied", "subject": "…" } ]
    }
  ]
}
```

Nothing is stored between runs. Each run scans Gmail again, so a better rule fixes old rows too.

---

## How the phone alerts work

The code is in `alerts.py`, called from `build_data.py` just before the data file is written. It does nothing unless the `NTFY_TOPIC` secret is set.

1. It downloads the data file the previous run published, from `https://OWNER.github.io/REPOSITORY/data.enc.json`, and unlocks it with the same passphrase. If that fails, for example on the very first run, it sends nothing.
2. It compares the old and new email histories. An email counts as new when its stage, date and subject were not in the old file.
3. Only Offer, Interview, Assessment, Screening and Rejected count, and only emails from the last 3 days (`MAX_AGE_DAYS`).
4. It counts them by kind and sends one message per level to `https://ntfy.sh/TOPIC`, for example "1 interview invite" at the loud level and "2 rejections" at the quiet level. It never includes company names, roles or subjects. Each notification links to your dashboard. The levels are the `LEVELS` table at the top of `alerts.py`: priority 5 for offers and interviews, 4 for screening calls and tests, 3 for rejections.

Settings: `MAX_AGE_DAYS` and the wording of each kind (`LABELS`) are at the top of `alerts.py`. To use your own ntfy server, set `NTFY_SERVER` next to `NTFY_TOPIC` in the workflow. Run `python tests/test_alerts.py` after changing anything.

---

## Changing the look

`site/index.html` is one file with no outside libraries or fonts. The colours are variables at the top of its `<style>` block, in one set for light and one for dark. The stage colours and the plain-language descriptions are in the `STAGES` list in the script, and the "Do these first" wording is in `FOCUS_TEXT`.

A few numbers near the top of the script are easy to adjust:

| Name | Default | Meaning |
|---|---|---|
| `GHOST_DAYS` | 21 | Days without any email before an application counts as "no reply" |
| the goal | 10 | Weekly application goal. Changed with the + and – buttons on the page and saved on that device |
| `HEARD` and `FORWARD` | stage lists | Which stages count as "heard back" and "moved forward" in the funnel |

The phone-install details are in `site/manifest.webmanifest`, and the icon is `site/icon.svg`.

---

## Contributing

Fixes and new patterns are welcome. Before sending a change:

- Run `python tests/test_classify.py` and make sure everything passes.
- When you add a rule, add a sample email for it to the tests.
- Never put real email text, names or tokens in the tests or in a commit. Use made-up examples.
