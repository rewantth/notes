# Security

This project reads your mailbox, so it is built to expose as little as possible. This page says what is protected, what is not, and what you should do yourself.

## What is protected

| Asset | How it is protected |
|---|---|
| Your list of applications | Encrypted with AES-256-GCM before it is published. The key comes from your passphrase through PBKDF2-SHA-256 with 1,000,000 rounds. The browser decrypts it locally. |
| Your Gmail access | A read-only OAuth refresh token stored only as a GitHub Actions secret. It cannot send, delete or change mail. It is exposed only to the single build step that needs it. |
| The published page | A strict Content Security Policy is added at build time. Only the page's own script, identified by its hash, may run. Injected scripts and inline handlers are refused, and the page may only contact its own site. |
| Your passphrase in the browser | Never stored. "Keep me unlocked" saves only a non-extractable key (a key the browser can use but nobody can read back, not even this page's own code), and Lock deletes it. |
| The build pipeline | Every GitHub Action is pinned to an exact commit, every Python package to an exact version, and the workflow starts with no permissions and grants each job only what it needs. |
| Logs | The program prints nothing about your applications, because logs of public repositories are public. |
| Phone alerts | Optional. They carry only a count such as "1 interview invite", never a name or email text. |

## What is not protected

- **The code is public** (it is also under the MIT licence, so anyone may copy it). Public code has no secrets in it, so that is safe by design, but it can be read and reused.
- **The encrypted data file is public.** Anyone can download it. They can then try passphrases on their own computer without limit. Only a long, random passphrase stops that. A short or guessable one can fall.
- **A page that is public can be seen by anyone who knows the address.** They see only a lock screen.
- **Metadata:** GitHub can see when the workflow runs, and ntfy (if you use alerts) sees that an alert was sent and when.
- **A stolen account is the biggest risk.** Someone who gets into your GitHub or Google account is past all of this.

## What you should do

1. Turn on two-step verification for GitHub and Google, with a passkey or an authenticator app.
2. Use a passphrase of four or five random words that you use nowhere else.
3. Keep `credentials.json` and `github-secrets.txt` off cloud drives and delete `github-secrets.txt` after setup.
4. If you ever suspect a leak: remove the app at <https://myaccount.google.com/permissions>, delete the three Gmail secrets, and change `DASHBOARD_PASSPHRASE`.
5. Review the pull requests from Dependabot before accepting them. They update pinned versions.

## Reporting a problem

Please use GitHub's **private vulnerability reporting** on this repository (the Security tab, then "Report a vulnerability"), and do not open a public issue for a security problem. Please do not include real emails, tokens or passphrases in a report.

## Checking it yourself

`python tests/test_security.py` verifies the main claims above: the policy, the encryption, the pinned dependencies, and that nothing in the page can run injected code or store your passphrase.
