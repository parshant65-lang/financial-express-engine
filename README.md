# Financial Express High-Throughput Archive Harvester

Autonomous, cloud-based data extraction engine harvesting **9,10,141 articles** across 9,102 pages from Financial Express (`financialexpress.com`) WordPress REST API.

## Multi-Volume Storage Vaults (Private)
1. **[`parshant65-lang/financial-express-vault-1`](https://github.com/parshant65-lang/financial-express-vault-1)**: Pages 1 to 3,000 (~3,00,000 articles)
2. **[`parshant65-lang/financial-express-vault-2`](https://github.com/parshant65-lang/financial-express-vault-2)**: Pages 3,001 to 6,000 (~3,00,000 articles)
3. **[`parshant65-lang/financial-express-vault-3`](https://github.com/parshant65-lang/financial-express-vault-3)**: Pages 6,001 to 9,102 (~3,10,000 articles)

## Features
- **Multi-Threaded**: Concurrently fetches pages via `/wp-json/wp/v2/posts`.
- **Pure Text**: Strips all ads, HTML tags, and boilerplate via `wp-block-paragraph`.
- **Zero Local Footprint**: 100% cloud-powered on GitHub Actions (0 MB Local PC).
- **Auto-Rollover**: Automatically transitions to Volume 2 and Volume 3 as volume limits are reached.
