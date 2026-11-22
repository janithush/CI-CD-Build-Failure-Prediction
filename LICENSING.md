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

## Combined application candidate

The combined implementation does not expand the explicit MIT file list above. In particular, changes to inherited UI/API/analyzer files and feature-serving code derived from the archival research retain their existing rights and provenance. Newly added combined files are not automatically covered by the four-file grant. No new blanket licence or ownership transfer is made by this integration.

## Legacy portable export

The issue #17 JSON/NPZ export preserves parameters from the inherited fitted model. It is derived material, not a newly MIT-licensed model. The evaluator, export/validation tools, tests and repair documentation do not expand the explicit four-file MIT grant. Shukri and original contributors retain credit and existing rights.
