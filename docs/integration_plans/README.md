# Integration Plans

Centralized documentation for all new vertical integrations on RayCarWash.

## Plan Index

| # | File | Area | Status |
|---|---|---|---|---|
| 00 | [00-user.md](./00-user.md) | User model — shared profile, Address model | Planning |
| 01 | [01-profiles.md](./01-profiles.md) | Multi-Profile System (Detailer + Mechanic) | Planning |
| 02 | [02-detailing.md](./02-detailing.md) | Detailing vertical — services, combos, pricing | Planning |
| 03 | [03-mechanic.md](./03-mechanic.md) | Basic mechanic vertical — oil, brakes, tires | Planning |
| 04 | [04-vehicles.md](./04-vehicles.md) | Vehicle catalog + user vehicles | Planning |

## Dependency Order

```
00-user.md  (User + Address foundation)
  └── 01-profiles.md  (1:N profiles, provider_type)
        ├── 02-detailing.md  (Detailer vertical)
        ├── 03-mechanic.md   (Mechanic vertical)
        └── 04-vehicles.md   (Vehicle catalog — standalone)
```

Each plan depends on all lower-numbered plans. Implement in order.

## Convention

- All code, comments, and documentation in English
- One plan per vertical or cross-cutting concern
- Plans numbered by implementation order
- Cross-domain plans (like billing) get their own number when started

## Cross-References

- **Master Index**: See [`docs/INDEX.md`](../INDEX.md) for the complete plan manifest, status tracking, and audit traceability matrix.
- **Operational Plans**: Infrastructure, CI/CD, observability, and hardening plans live in [`docs/plans/`](../plans/). Plan 08-hardening resolves audit P0/P1 findings that precede integration work.
- **Technical Audit**: [`docs/audit/`](../audit/) documents ~60 findings across architecture, tests, infra, web, and DB schema.
