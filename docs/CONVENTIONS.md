# Hel Conventions

These rules are normative for every Hel contract. Each field's own description
(in the models, the generated JSON Schemas and the TypeScript types) gives its
units and reference direction; this page states the rules once.

## Contracts and versions

| Contract | File | Written by | Read by | Version |
| --- | --- | --- | --- | --- |
| `hel.event` | `event.json` | the analyst, tools | Fenrir, Loki | 1.0 |
| `hel.radar` | `RADAR_*.json` | Gjallerhorn | Fenrir | 1.2 |
| `hel.seismo` | `Loki_output/seismo.json` | Loki | Fenrir | 1.1 |
| `hel.results` | `results.json` (a Fenrir run's outputs) | Fenrir | Fenrir's frontend, other apps | 1.0 |

- Every file begins with `"contract": "hel.<name>"` and
  `"contract_version": "MAJOR.MINOR"`.
- **MINOR** versions only add optional fields. **MAJOR** versions change
  anything else: a rename, a new required field, a changed unit or meaning,
  or a removal.
- **Readers** accept any MINOR version of their MAJOR version and keep fields
  they don't know (`hel validate` lists them as warnings). They reject other
  MAJOR versions.
- **Producers** validate before saving and write the newest version their
  pinned Hel defines.
- **Absent means not recorded.** An optional field is left out when there is
  no value, rather than written as `null`. (`null` is still accepted when
  reading, and means the same thing.)

## Units and frames

- **Time:** ISO 8601, UTC, ending in `Z`, e.g. `2003-03-27T05:50:26.4Z`. A time
  with no zone is invalid; `hel upgrade` converts legacy zone-less times and
  records that it treated them as UTC.
- **SI units**, with the unit in the field name: `_m`, `_mps` (m/s), `_kg`,
  `_kg_m3`, `_s`, `_deg`, `_db`, `_dbz`, `_dbm`, `_hz`, `_pct`. A few
  established legacy radar names keep their original form (D26); their
  descriptions state the units:
  - `pixel_altitude` and `pixel_distance` are metres;
  - `sweep_elevation` and `pixel_azimuth` are degrees;
  - each radar product's unit is in `hel.radar.PRODUCTS`.
- **Position:** latitude and longitude in decimal degrees, WGS84.
  Longitude is in [-180, 180].
- **Altitude:** metres above mean sea level, except in `hel.results`, where
  every altitude is metres above the **WGS84 ellipsoid** (Fenrir D28: computed
  in ellipsoidal height, shown to people above mean sea level, as hand-held
  GPS units show it).
- **Mass:** kilograms (`_kg`). Displays show grams below 1000 g (Fenrir D28).
- **Azimuth:** degrees clockwise from true north. For a fireball or fragment,
  it is the **direction of travel**, not the radiant direction, which differs
  by 180°.
- **Declination:** the trajectory's angle **below horizontal**, in degrees:
  0 is horizontal and 90 is vertical.
- **Radar elevation:** a sweep's `sweep_elevation` is the antenna angle
  above horizontal. It is unrelated to a trajectory's declination.
- **Radial velocity:** positive is away from the radar.

## Radar product names

Every network's products use one canonical name (`hel.radar.PRODUCTS`):

| Product | Unit |
| --- | --- |
| `reflectivity` | dBZ |
| `velocity` | m/s (positive away from the radar) |
| `spectrum_width` | m/s |
| `differential_reflectivity` | dB |
| `correlation_coefficient` | dimensionless |
| `differential_phase` | degrees |
| `clutter_filter_power_removed` | dB |

`hel upgrade` renames the known aliases (`cross_correlation_ratio`,
`corr_coeff`, `diff_reflectivity`, `diff_phase`).

## Detection floor

A sweep's weakest detectable reflectivity at range R (km) is:

    floor(R) = detection_floor_dbz_at_1km + 20·log10(R)
    detection_floor_dbz_at_1km = calibration_constant_dbz0 + snr_threshold_db

This was verified against the weakest observed echoes on KBMX and KIWA to
within about 1–2 dB (Fenrir D21a, D21b).

## Upgrading legacy files

`hel upgrade` (or `hel.load`, which upgrades in memory) converts every legacy
layout found in the recovered-falls archive:
- events: the `terminus` and `luminous_end` layouts, and the
  spreadsheet-style labels;
- radar: the legacy export and its oldest layout;
- seismo: Loki's own version 1.1.0.

The upgrader never edits a file in place. It keeps unknown fields, and it
reports every change in plain words. Nothing is dropped silently.

## Changing a contract

1. Change the model in `src/hel`, with a description that gives units and
   reference direction for every field.
2. Bump `CONTRACT_VERSION` (MINOR or MAJOR, as above) and add a line to the
   module's version history.
3. Run `python tools/generate_artifacts.py`, then update the golden files and
   tests.
4. Tag a Hel release. Each app then syncs its pinned copy.
