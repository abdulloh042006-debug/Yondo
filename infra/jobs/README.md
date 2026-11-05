# Scheduled maintenance jobs

`python -m yondo_api.jobs` (from `apps/api`, with the API's environment) runs, in order:

1. **Booking expiry** — bookings still `pending` or `accepted` (i.e. never paid/confirmed) whose start time has
   passed become `expired`; their slot is released (owner rule 2026-10-23).
2. **Account erasure** — accounts whose deletion request is due are de-identified, so personal data is gone
   within the 30 days promised in the Privacy policy (requests become due after 29 days).

It is idempotent and safe to run often. **Run it at least hourly** (daily is the bare minimum for the
30-day promise). Output: `bookings_expired=N accounts_erased=N skipped_open_bookings=N`; exit code 1 means
an account was skipped because it still has open bookings — an operator must resolve that booking.

Files here:

| File | Use |
|---|---|
| `yondo-jobs.service` + `yondo-jobs.timer` | systemd (recommended): `systemctl enable --now yondo-jobs.timer` |
| `yondo-jobs.cron` | crontab alternative |

Paths (`/opt/yondo`, `/etc/yondo/api.env`, user `yondo`) are placeholders: there is no production host yet.
Photo objects of erased accounts are deleted only when the job process has an object-storage adapter; the
production storage adapter is not implemented yet (rows are tombstoned and keys logged).

Admins can also run the same erasure from the console (`/admin/deletions`); booking expiry additionally
happens on the spot when someone tries to accept or pay an overdue booking.
