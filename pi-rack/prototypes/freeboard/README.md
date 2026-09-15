# Freeboard — prototype

*Freeboard is the margin between the waterline and the deck. At zero you are not sinking
— you just have no reserve, and the next wave comes aboard.*

```bash
python freeboard.py
```

```bash
python freeboard.py --job-gb 450
```

Standard library only. Reads free space and writes nothing. Exits non-zero when the job
does not fit, so it works as a scheduled check.

---

## The measurement that prompted it

Twelve real wedding jobs on `K:\Weddings` were measured on 2026-08-28:
**median 278 GB, mean 399 GB, largest 2,452 GB.**

Against that, the three volumes that actually hold client work:

| Volume | Free | In jobs |
|---|---|---|
| `K:` M1 | 46.7 GB | 0.17 |
| `L:` Video Work | 151.8 GB | 0.55 |
| `V:` easystore | 20.1 GB | 0.07 |
| **combined** | **218.6 GB** | **0.79** |

**Verdict on the real machine today: WILL NOT FIT.** Not on any one of them, and not
across all three.

Meanwhile `O:` has 10.7 TB free, `M:` has 5.5 TB and `H:` has 5.2 TB. So the machine is
not out of disk — it is out of disk **where the work is filed**, which is why the
shortage stays invisible until a card will not offload at a venue at midnight.

## Why this is not "a disk space alert"

Every monitoring tool in existence can tell you a volume is 99% full. That is not the
question. The question is **"will Saturday's job fit in the place it actually goes?"**,
and answering it needs three things a generic alert does not have:

1. **What a job costs**, measured from real jobs rather than guessed.
2. **Which volumes count.** `O:` having 10.7 TB free is irrelevant if client work is
   never filed there. Room in the wrong place is not headroom.
3. **A verdict, not a percentage.** `99.6%` is a number you learn to ignore. *"The next
   wedding does not fit"* is not.

## Deliberate limits

- **It moves nothing and deletes nothing, ever.** Freeing space means deciding what to
  archive, which is a judgement about client work. This only says the judgement is due.
- **No trend line.** There is no history to extrapolate from, and inventing a fill date
  from a single sample would be worse than saying nothing. If it ever runs on a
  schedule it can keep history and *then* earn the right to predict.
- **`WORKING_LABELS` is a policy, not a discovery.** It encodes which volumes hold
  client work. If the filing convention changes, that set changes.
- The job-size constants are **observations with a date on them**, not laws. Re-measure
  and update them.

## What turning this into the real thing looks like

Roughly two evenings, not two weeks:

- Run it on a schedule and keep the history, so it can say *"you have about five weeks
  of headroom at your current rate"* — which is the version that actually changes
  behaviour.
- Publish to MQTT so Home Assistant owns the alerting, since the broker and the
  notification path already exist.
- Warn on the **Wednesday before a booked Saturday**, from the calendar, rather than
  whenever someone remembers to run it. That is the difference between a report and a
  save.
- Take the job size from the *actual* booking (a two-shooter full day is not a median
  job) instead of a default.

That schedule-and-remember part is the only bit that genuinely wants an always-on box.
Everything above runs fine as a script today.
