# Privacy

Claude Usage Lens is designed as a local-first usage calculator.

## What the app uploads

The static `app.html` calculator does not upload imported usage files to a server. File parsing, cost estimation, charting, and report export run in the browser.

## What users should not paste

Do not paste Anthropic Admin API keys, Claude account credentials, private conversation content, customer data, secrets, or proprietary logs into public issue trackers or shared screenshots.

## Imported data

Imported ccusage JSON and usage export JSON may contain:

- project paths
- session identifiers
- model names
- timestamps
- token counts
- cost estimates
- machine labels

Users should review exported reports before sharing them.

## Third-party scripts

The static app currently loads Chart.js from jsDelivr. The original personal dashboard also loads Three.js and Chart.js from public CDNs. For fully offline operation, vendor these scripts into the repository and load them locally.

## No warranty

The calculator is provided as-is. Cost estimates depend on public pricing data, exported token fields, and model mapping. Treat results as estimates unless reconciled against official billing records.
