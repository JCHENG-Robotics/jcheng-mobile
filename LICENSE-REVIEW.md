# License review — jcheng-mobile

> Status: **pending** as of 2026-11-24.
> The repository's existing `LICENSE` (MIT) is **retained pending this review**.
> It predates the organization rule that no `LICENSE` is added before the review
> is signed off.

## 1. Current facts

| Item | Fact |
|---|---|
| File | `LICENSE`, MIT, copyright line `Copyright (c) 2026 JCHENG Robotics` |
| Origin | Added in the initial commit `ad389e4` (`chore: initialize jcheng-mobile repository`) |
| Organization policy | `.github/docs/license-review.md` — no `LICENSE` in the new repositories until the review is approved |
| Conflict | This file exists while `jcheng-interfaces`, `jcheng-system`, `jcheng-perception`, `jcheng-ops` and `.github` carry none |

## 2. Decision recorded on 2026-11-24

The file is **not removed retroactively**. Removing it would not withdraw the
MIT grant already made to anyone who obtained a copy, and it would create a
period in which the repository's license status is ambiguous.

The review must instead decide, before the ecosystem reaches v1.0:

1. Whether the copyright holder and year are correct
   (`JCHENG Robotics`, 2026) or should match the baseline
   (`Kewei (Jericho) Cheng`) / a contributor policy.
2. Whether MIT is the intended license for this repository and for the
   ecosystem, after the third-party inventory below.
3. If MIT is not the choice, replace the file through a normal PR and record
   the change in `CHANGELOG.md`; do not delete it silently.

Until then this file grants MIT for this repository only. It is **not** a
precedent for adding `LICENSE` files elsewhere while the review is open.

## 3. Third-party inventory (to verify)

| Dependency | Use | Known/probable license | Risk |
|---|---|---|---|
| ROS 2 Humble | Runtime | Apache-2.0 | Low; keep notices |
| Nav2 (`nav2_bringup`, `nav2_mppi_controller`) | Navigation | Apache-2.0 / BSD-3-Clause | Low |
| slam_toolbox | Mapping | BSD-3-Clause | Low |
| RTAB-Map (`rtabmap_odom`) | ICP odometry | BSD-3-Clause | Low |
| CycloneDDS | DDS | EPL-2.0 / EDL | Medium if distributed in an image |
| LSLIDAR M10 driver | Not in this repository (system/hardware layer) | Vendor | Out of scope here |

Model weights and vendor assets are not part of this repository.

## 4. Open questions

- [ ] Confirm the copyright holder and year.
- [ ] Confirm MIT after the third-party compatibility check.
- [ ] Decide whether a `THIRD_PARTY_NOTICES.md` is required for deployed images.
- [ ] Record the ecosystem-wide decision in `.github/docs/license-review.md`
      and the ecosystem acceptance report.

## 5. Related

- [`.github/docs/license-review.md`](https://github.com/JCHENG-Robotics/.github/blob/main/docs/license-review.md)
- [Acceptance report](ACCEPTANCE.md)
- [README](README.md)
