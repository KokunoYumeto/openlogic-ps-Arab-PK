# OpenLogic in Pashto — Pakistan

An independent machine translation of the Open Logic Project into Pashto in Arabic script, for a Pakistan curriculum target. Pakistani prose and orthography are primary; Afghan Pashto sources are explicitly labelled regional comparators.

**Work in progress: 255 of 722 source units are translated and structurally verified. The current [326-page cumulative PDF](readers/openlogic-ps-Arab-PK-cumulative-through-computability.pdf) and matching [25-chapter reflowable EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-computability.epub) contain all translated material from the project front matter through computability and the introductory Turing-machine representations. The [v0.6.0 GitHub release](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases/tag/v0.6.0-computability) provides the accepted PDF first as the human-readable preview, followed by direct cumulative LaTeX, the exact tagged source archive, EPUB, validation evidence and checksums. The complete 722-unit edition remains under production.** This repository does not claim a complete book or human-reviewed translation. See [the translation catalogue](https://github.com/KokunoYumeto/OpenLogic-translations).

Read the current [cumulative PDF](readers/openlogic-ps-Arab-PK-cumulative-through-computability.pdf) or [EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-computability.epub). The earlier [proof-systems and completeness PDF](readers/openlogic-ps-Arab-PK-proof-systems-completeness.pdf) and [EPUB](readers/openlogic-ps-Arab-PK-proof-systems-completeness.epub), [proof-systems PDF](readers/openlogic-ps-Arab-PK-proof-systems.pdf), [sets, relations and functions PDF](readers/openlogic-ps-Arab-PK-sets-relations-functions.pdf), [sets-and-relations PDF](readers/openlogic-ps-Arab-PK-sets-relations.pdf), and [sets-only PDF](readers/openlogic-ps-Arab-PK-sets.pdf) remain available. Versioned assets are preserved in [GitHub releases](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases) and the [Zenodo edition lineage](https://doi.org/10.5281/zenodo.22307197).

The current reader covers foundations; sets, relations and functions; cardinality and infinite sets; propositional and first-order logic; all four proof systems and completeness; model theory; recursive functions and computability; and introductory Turing-machine representations. It preserves the original examples, exercises, formulas, tables, proof trees, tableaux and diagrams under the frozen upstream default profile. The editable Pashto source mirrors upstream paths in `ps-Arab-PK/`. Separate adjacent disclosures explain inherited notation ambiguities and stable source corrections without changing frozen English bytes.

The [expert-review log](EXPERT_REVIEW.md) records all 143 current terminology choices and 198 difficult translation/source decisions. [Start with the canonical review guide](evidence/START_HERE.md), then use the [full decision index](evidence/TRANSLATION_DECISIONS_FULL.md), [priority review](evidence/PRIORITY_REVIEW.md), UTF-8-BOM [paired-occurrence CSV](evidence/DECISION_OCCURRENCES.csv), [canonical machine register](evidence/DECISIONS.json), [normative schema](evidence/translation-decision.schema.json), and [validation receipt](evidence/TRANSLATION_DECISION_QA.json). The package contains 341 decisions and 15,360 exact paired source/target occurrences under the shared OpenLogic schema. Of those occurrences, 14,810 have accepted reader pages derived from 2,683 exact start/end label pairs; 550 profile-excluded occurrences remain explicitly pending. Every decision states the source sense, exact evidence, chosen rendering, ps-Arab-PK/Arab identity, rationale and checked sources, alternatives, confidence and a plain review question. The index is partial at the stated draft coverage and welcomes asynchronous corrections; expert response is not a release gate. The earlier expanded projections remain available for compatibility. [Source corrections](SOURCE_CORRECTIONS.md) separately identify 192 adopted findings. The [audit-retraction record](evidence/SOURCE_AUDIT_RETRACTIONS.jsonl) preserves the explicit withdrawals of OLSIZ-011 and OLINF-002; neither appears as an active correction.

## Source and evidence

`upstream/` preserves the raw English source at revision `9620cc73f9c8e0ad003c514a5d3748f29611c4c0` of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic). All 722 content hashes were verified. `evidence/SOURCE_MANIFEST.jsonl` retains the stable OLP unit IDs and both raw-source and historical Windows-checkout hashes. Different newline representations are provenance, not errors.

Canon includes a native Pashto semantics article by Bushra Iqram at the Pashto Academy, University of Peshawar; native Afghan mathematical logic, set theory and grade-7 mathematics as regional comparators; and Tegey and Robson's reference grammar for grammatical analysis. The evidence indexes distinguish prose, grammar and concept-specific attestation. They record source and inspected-page hashes. Original canon PDFs remain private reference copies and are not redistributed here.

Terminology remains provisional when the consulted evidence does not establish the exact technical sense. In particular, descriptive labels for extensionality and power set are decisions, not claims of a settled Pakistani standard. Canon consultation is recorded per source-aligned paragraph. Native witnesses guide language; the English source governs mathematics.

## Validation and limits

Validation checks source hashes, paragraph alignment, environments, formula bodies, term tokens, references, Unicode and residual ordinary English. Semantic review includes reverse paraphrases and specifically checks membership versus subset, both directions of biconditionals, bounded quantifiers, product cardinality, and uniqueness versus existence. Native glyph joining, diacritics, punctuation and left-to-right mathematical isolation are inspected in actual renders. These checks do not establish native-reader approval or eliminate all translation uncertainty.

English comments and identifiers remain as structural metadata. The proper name `Ruth` inside an original formula is a documented exception. Formula text is translated. The `psOblique` wrapper realizes required Pashto case inflection while retaining the original term token and key.

The current PDF and EPUB follow 25 actual chapter drivers and include OLP-0001 through OLP-0255. The accepted PDF has 326 pages and exact start/end labels for 2,683 semantic segments. The EPUB contains 15,376 native MathML elements, 20 self-contained SVG figures, 1,045 validated internal links, 255 source-unit anchors and the same 2,683 paired segment anchors. Independent cold rebuilds are byte-identical, EPUBCheck 5.4.0 reports no messages, and 42 representative wide and reader-width browser captures have no clipping, overflow, broken images, console errors or page errors. All 326 PDF pages were inspected, with full-resolution checks across the main formal systems, diagrams, tables, Turing-machine figures and bibliography. OLP-0256 is next. No complete-reader claim follows from preserving all English source files.

## Rebuild the current reader on Windows

Requires Python 3, XeLaTeX with fontspec, amsmath/amsthm, bidi, TikZ, natbib, hyperref and the Amiri font. From this repository:

```powershell
python tools/build_cumulative_reader.py --build-dir ./build/reader-cumulative
./tools/guard_tex.ps1 -Passes 3 -BuildDirectory ./build/reader-cumulative -DocumentBases reader
python tools/check_translation.py
```

The PDF output is `build/reader-cumulative/reader.pdf`. The guard acquires `Global\InterlanguageTeXSlotV1` with one bounded timeout, captures descendants in a Windows job before resuming the engine, holds the slot through all passes and log checks, and releases it in `finally`. Fixed `SOURCE_DATE_EPOCH` supports deterministic replay.

The EPUB builder consumes the accepted output of the two-phase figure workflow documented by `tools/render_cumulative_epub_figures.py`:

```powershell
python tools/build_cumulative_epub.py --build-dir ./build/epub-cumulative --figures-dir ./build/epub-cumulative-figures --output ./build/epub-cumulative/openlogic-ps-Arab-PK-cumulative-through-computability.epub
python tools/validate_cumulative_epub.py --epub ./build/epub-cumulative/openlogic-ps-Arab-PK-cumulative-through-computability.epub --build-record ./build/epub-cumulative/build-epub.json --alignment ./evidence/ALIGNMENT.jsonl --reference-map ./evidence/CUMULATIVE_EPUB_REFERENCE_MAP.json --output ./build/epub-cumulative/independent-validation.json
```

The [EPUB acceptance record](evidence/EPUB_DELIVERY_ACCEPTANCE.json) documents deterministic replay, EPUBCheck results, structural and link counts, visual QA and the conversion defects found and repaired during acceptance. The [direct LaTeX validation record](evidence/DIRECT_TEX_VALIDATION.json) records three guarded passes per edition and exact reproduction of every accepted public PDF hash.

## Attribution and license

Adapted from the [Open Logic Project](https://openlogicproject.org/), whose contributor attribution and component notices are preserved in `upstream/`. The source text and this translation are available under [Creative Commons Attribution 4.0 International](LICENSE.md); inherited component exceptions remain applicable. This adaptation is machine-generated and independently maintained; upstream endorsement is not implied.
