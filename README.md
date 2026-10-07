# Hel

The shared data contracts of the **Yggdrasil** meteorite-fall software suite:

- **Gjallerhorn** extracts meteorite radar signatures;
- **Loki** analyses seismo-acoustic evidence;
- **Fenrir** runs the dark-flight analysis.

Hel defines the files they exchange:

| Contract | File | Version |
| --- | --- | --- |
| `hel.event` | `event.json`: what is known about a fall | 1.0 |
| `hel.radar` | `RADAR_*.json`: the selected radar signatures | 1.1 |
| `hel.seismo` | `seismo.json`: Loki's evidence and trajectory | 1.1 |

The rules every contract follows (UTC times, SI units, azimuth and
declination conventions, versioning) are in
[docs/CONVENTIONS.md](docs/CONVENTIONS.md).

## What is here

- `src/hel/`: the contract models (pydantic, the single source of truth), the
  legacy-file upgrader, the validator and the `hel` command.
- `src/hel/schemas/`: JSON Schemas generated from the models.
- `src/hel/types/hel.d.ts`: TypeScript types for the frontends.
- `src/hel/golden/`: example files:
  - `current/`: valid current files;
  - `legacy/`: real legacy files;
  - `upgraded/`: the exact output expected from each legacy file.

## Use

```bash
hel validate event.json RADAR_Fall.json Loki_output/seismo.json
hel upgrade old_event.json --out event.json     # never overwrites the input
```

```python
import hel

loaded = hel.load("event.json")  # upgrades legacy layouts, then validates
loaded.document  # the validated model
loaded.upgrade.changes  # what the upgrader changed, in plain words
```

Apps don't install Hel from this repository. Each app keeps a **pinned copy**
synced from a tagged release, with a CI check that the copy is unedited
(decision D26 in Fenrir's decision log). To change a contract, change it here,
tag a release, and sync each app.

## Development

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-lock.txt
uv pip install --python .venv -e . --no-deps
npm install                       # TypeScript generation
python tools/run_ci.py            # what CI runs
python tools/generate_artifacts.py   # after any model change
```

`tools/survey_falls.py --root PATH` upgrades and validates every contract
file in a folder of falls, without writing anything.

Proprietary; see [LICENSE](LICENSE).
