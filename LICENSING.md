# Licence boundaries

## Inherited project and derived code

Version 1 belongs to Shukri (mhdshukry) and the original contributors. The inspected upstream revision has no licence file. Janith reports verbal permission from Shukri to use and modify the project; this is not a licence grant to other recipients.

No blanket MIT licence is claimed for this repository. All original files, edits to inherited files (including `dashboard/index.html`), upstream-derived training helpers in `research/v2/src/`, archival scientific code, datasets and fitted models remain outside the MIT grant below. Retained credit and provenance do not substitute for permission for uses beyond the owner's grant.

## Independently authored Janith additions

Only these files are offered under `LICENSE-MIT-JANITH.txt`, copyright 2026 Janith Gunathunga:

- `README.md` (new comparison and research documentation)
- `research/v2/README.md` (new reproduction documentation)
- `dashboard/research-v2.html` (new frozen-results interface)
- `research/v2/reproduce.py` (new portable verification/replay/refit entry point)

The entry point imports separate helpers and uses data/models not covered by this grant. Licensing the entry point does not relicense its dependencies. Other third-party dependencies retain their own licences. Files not explicitly listed above are not covered by this MIT grant.
