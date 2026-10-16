# Hel widget kit

The Yggdrasil suite's shared React components and dark "glass" theme
(H-002; Fenrir D11a). Each app keeps a pinned copy, like the contracts.

## What is here

- `src/widgets.tsx`: the components. Text and headings (`Header`,
  `Subheader`, `Caption`, `Divider`, `Metric`, `StatusPill`), messages
  (`Alert`, `Messages`, `Spinner`, `Toasts`, `Progress`), inputs (`Radio`,
  `Select`, `TextInput`, `NumberInput`, `Slider`, `Checkbox`, `FileDrop`),
  actions and containers (`Button`, `Dialog`, `Tabs`, `Expander`,
  `DataTable`, `Help`).
- `src/inline.tsx`: inline markup for component text (`**bold**`,
  `_italic_`, `` `code` ``, `[links](url)`).
- `src/hel-widgets.css`: theme tokens, the page layout (`.app-layout`,
  `.sidebar`, `.main`) and every component's styles (`hel-` prefix).
- `src/index.ts`: the exports.
- `tests/`: Vitest tests, run by `python tools/run_ci.py`.

Components are controlled: the app keeps each value and passes `value` and
`onChange`. They need `react`, `react-dom` and `lucide-react` (icons).

## Using it in an app

Copy `widgets/src/` from a tagged Hel release into the app (Fenrir:
`frontend/src/hel-widgets/`) with the app's sync tool, which records the tag
and a hash of every file; the app's CI fails if the copy is edited. Change
widgets here, release, and sync. Then:

```ts
import './hel-widgets/hel-widgets.css';
import { Button, NumberInput, Tabs } from './hel-widgets';
```
