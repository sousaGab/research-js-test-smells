# Third-Party Notices

The MIT License in [`LICENSE`](LICENSE) covers **only the original research code
authored in this repository** — the refactoring pipeline, the smell selector UI, the
analysis scripts, and the accompanying documentation.

This repository also vendors third-party software and research data that is **not**
covered by that license. Each retains its own license and copyright, as distributed by
its original authors.

## Study subjects — `repositories/`

This directory contains snapshots of open-source JavaScript projects used as the study
corpus. They are included so the experiments can be reproduced against the exact code
that was analyzed. Each project keeps its original `LICENSE` file in its own directory.

Distribution of licenses across the corpus:

| License | Projects |
|---|---|
| MIT | 15 |
| Apache-2.0 | 3 |
| MIT-style copyright notice | 4 |

Projects include, among others: `bootstrap-vue-dev`, `commander.js`, `falcor`,
`filepond`, `formidable`, `github-readme-stats`, `html-webpack-plugin`, `inferno`,
`javascript-algorithms`, `jscodeshift`, `list.js`, `luxon`, `nock`, `react-grid-layout`,
`redux-offline`, `rickshaw`, `serverless-express`, `svgo`, `vanilla-lazyload`,
`why-did-you-render`, `winston`.

Refer to `repositories/<project>/LICENSE` for the authoritative terms of each.

## Detection tools — `smell_detection_tools/`

| Tool | Notes |
|---|---|
| `steel` | Third-party test smell detector; see `smell_detection_tools/steel/LICENSE` |
| `snutsjs` | Third-party test smell detector; retains its original license |

## Derived data

Outputs under `smells_detected/` and `tests_output/` are derived from the study subjects
above. Anyone redistributing that data should observe the license of the corresponding
upstream project.
