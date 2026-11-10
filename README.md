# Faith-EL Virtual Stylist

Telegram-based virtual try-on assistant for fashion boutiques.

> **Sprint 1 status:** project skeleton and configuration only. No database
> logic, no Telegram handlers, and no image generation are implemented yet.

## Current state (Deliverable 1)

```text
faith-el-virtual-stylist/
├── .env.example          # template — BOT_TOKEN intentionally empty, no secrets
├── .gitignore            # excludes .env, customer photos, DBs, caches
├── README.md
├── config/
│   ├── boutique.yaml     # single boutique; channel.id: null; admins: []
│   └── settings.yaml     # aiogram 3, mock imagegen, privacy & retention policy
├── data/                 # local-only storage (gitignored content)
├── scripts/              # dev/ops helper scripts (later sprints)
├── src/
│   └── faith_el/
│       ├── imagegen/     # mock provider (labelled non-real try-on) — later
│       ├── repositories/ # data access layer — later
│       ├── services/     # business logic — later
│       ├── storage/      # local file management & retention sweep — later
│       ├── telegram/     # aiogram 3 bot layer — later
│       └── utils/        # shared helpers — later
└── tests/
```

## Environment

- Python **3.11+** (development environment currently runs 3.12).
- Linux, terminal access, persistent project files in this repository.
- Free resources only: **no paid APIs, GPU rental, subscriptions or hosting.**
- Telegram framework (planned): **aiogram 3.x**.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml            # Sprint 1 needs only config parsing
cp .env.example .env          # then fill BOT_TOKEN locally — never commit it
```

## Key product & safety rules (encoded in `config/`)

1. **Single boutique** initially (`policy.single_boutique_only: true`).
2. **No real secrets in the repo.** `.env.example` keeps `BOT_TOKEN=` empty;
   the bot must refuse to start without a valid token supplied locally.
3. **Channel monitoring** stays disabled until `channel.id` is set to a valid,
   confirmed ID (`channel.id: null` today; `policy.require_valid_ids_before_enable`).
4. **Admin functions** stay disabled until `admins.telegram_user_ids` contains
   at least one valid ID (currently `[]`).
5. **Consent gate:** customer photos are never downloaded or processed before
   explicit in-chat customer consent (`privacy.require_customer_consent_before_download`).
6. **Retention:** default maximum local photo retention is **7 days**; customers
   can request **immediate deletion** at any time.
7. **Deletion scope:** removing a customer's data covers original photos,
   generated previews **and** associated database records.
8. **Telegram platform limitation:** our controls apply only to *local* copies.
   Telegram itself retains messages/media on its servers per its own policies;
   we cannot guarantee deletion of Telegram-side copies, CDN caches, or content
   already saved/forwarded by others. This is documented in
   `retention.telegram_retention_note`.
9. **No training on customer photos** (`privacy.training_data_prohibited: true`).
10. **Mock image provider:** the initial `imagegen` provider is clearly labelled
    as a **mock** — it does **not** perform genuine virtual try-on, and outputs
    carry the label `"PREVIEW ONLY - mock image, not a real virtual try-on"`.

## Roadmap

- ✅ Sprint 1 / D1: project skeleton + configuration files
- ⏭️ Sprint 1 / D2 (pending approval): config loader & validation utilities
- ⏭️ Later sprints: storage & retention, repositories, mock imagegen, aiogram 3 bot

## License

TBD (private project).
