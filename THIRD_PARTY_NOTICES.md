# Third-Party Notices

## sqlite-dissect (DC3)

- Source: https://github.com/dod-cyber-crime-center/sqlite-dissect
- Vendored at: `vendor/sqlite-dissect`
- License: DC3 SQLite Dissect Open Source License (permissive, attribution required)
- Role: Reader layer, WAL/journal version history, signature carving baseline

## Algorithm references (concept only, reimplemented)

- bring2lite (DFRWS 2019 USA paper): freeblock / unallocated / freelist algorithms
- fqlite (Pawlaszczyk & Hummert 2021): serial-type fingerprint + Boyer-Moore carving
- xsqlite (NFI): cross-check patterns for deleted record recovery
- undark / sqbrite: corrupt DB raw salvage concepts
