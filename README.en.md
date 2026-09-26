# OpenLogic in Pashto — Pakistan

The Pashto translation and mathematical review through OLP-0311 were produced by OpenAI Codex — GPT-5.6 Sol, Ultra effort. The B057 evidence replay, Pakistani-Pashto access material, and translation, source corrections and review of OLP-0312 through OLP-0369 were produced by OpenAI Codex — GPT-6 Sol, Ultra effort. No human translation or specialist approval is claimed. [د پښتو اصلي معلوماتو پاڼه](README.ps-Arab-PK.md) is the primary access page.

An independent machine translation of the Open Logic Project into Pashto in Arabic script, for a Pakistan curriculum target. Pakistani prose and orthography are primary; Afghan Pashto sources are explicitly labelled regional comparators.

**Work in progress: 369 of 722 source units are translated and structurally verified. The current [420-page cumulative PDF](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.pdf) and matching [31-chapter reflowable EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.epub) cover the first 321 units, from the foundations through computability, arithmetized syntax, and the Gödel and Rosser incompleteness theorems. Forty-eight later units remain editable verified drafts through second-order logic and the lambda-calculus Church--Rosser parallel beta-reduction section; 353 units still need translation. The [v0.7.0 GitHub release](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases/tag/v0.7.0-incompleteness) provides the PDF preview, direct cumulative LaTeX, complete source ZIP, EPUB, validation record and checksums.** This remains an incomplete, machine-generated edition without human specialist approval. See [the translation catalogue](https://github.com/KokunoYumeto/OpenLogic-translations).

Read the current [cumulative PDF](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.pdf) or [EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.epub). The previous [computability PDF](readers/openlogic-ps-Arab-PK-cumulative-through-computability.pdf) and [EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-computability.epub), and earlier editions, remain available through [GitHub releases](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases). The [current version DOI](https://doi.org/10.5281/zenodo.22971283) identifies this release; the [Zenodo edition lineage](https://doi.org/10.5281/zenodo.22307197) preserves versioned records.

The current reader covers foundations; sets, relations and functions; cardinality; propositional and first-order logic; four proof systems and completeness; model theory; recursive functions and computability; Turing machines; arithmetized syntax; and the incompleteness theorems. It preserves examples, exercises, formulas, tables, proof trees, tableaux and diagrams under the frozen upstream default profile. Editable Pashto sources mirror upstream paths in `ps-Arab-PK/`. Adjacent disclosures explain inherited notation ambiguities and source corrections without changing frozen English bytes.

The [Pakistani-Pashto expert-review guide](EXPERT_REVIEW.ps-Arab-PK.md) is the primary review route; [English detail](EXPERT_REVIEW.md) is supplementary. The [canonical register](evidence/DECISIONS.json), [full index](evidence/TRANSLATION_DECISIONS_FULL.md), [priority index](evidence/PRIORITY_REVIEW.md), [paired-occurrence CSV](evidence/DECISION_OCCURRENCES.csv), [schema](evidence/translation-decision.schema.json), and [validation receipt](evidence/TRANSLATION_DECISION_QA.json) record 496 decisions and 20,258 exact source/target occurrence pairs. The accepted 3,414-segment page map supplies 18,455 exact reader locators; 1,803 remain pending. One floating Turing-machine figure has a documented anchor-order exception in [the page map](evidence/READER_OCCURRENCE_PAGES.json). The [source corrections](SOURCE_CORRECTIONS.md) record 297 adopted actions; four historical retractions remain documented in [the audit record](evidence/SOURCE_AUDIT_RETRACTIONS.jsonl). Expert feedback is welcome but is not a release gate.

## Source and evidence

`upstream/` preserves the raw English source at revision `9620cc73f9c8e0ad003c514a5d3748f29611c4c0` of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic). All 722 content hashes were verified. `evidence/SOURCE_MANIFEST.jsonl` retains the stable OLP unit IDs and both raw-source and historical Windows-checkout hashes. Different newline representations are provenance, not errors.

Canon includes a native Pashto semantics article by Bushra Iqram at the Pashto Academy, University of Peshawar; native Afghan mathematical logic, set theory and grade-7 mathematics as regional comparators; and Tegey and Robson's reference grammar for grammatical analysis. The evidence indexes distinguish prose, grammar and concept-specific attestation. They record source and inspected-page hashes. Original canon PDFs remain private reference copies and are not redistributed here.

Terminology remains provisional when the consulted evidence does not establish the exact technical sense. In particular, descriptive labels for extensionality and power set are decisions, not claims of a settled Pakistani standard. Canon consultation is recorded per source-aligned paragraph. Native witnesses guide language; the English source governs mathematics.

## Validation and limits

Validation checks source hashes, paragraph alignment, environments, formula bodies, term tokens, references, Unicode and residual ordinary English. Semantic review includes reverse paraphrases and specifically checks membership versus subset, both directions of biconditionals, bounded quantifiers, product cardinality, and uniqueness versus existence. Native glyph joining, diacritics, punctuation and left-to-right mathematical isolation are inspected in actual renders. These checks do not establish native-reader approval or eliminate all translation uncertainty.

English comments and identifiers remain as structural metadata. The proper name `Ruth` inside an original formula is a documented exception. Formula text is translated. The `psOblique` wrapper realizes required Pashto case inflection while retaining the original term token and key.

The current PDF and EPUB follow 31 chapter drivers and cover OLP-0001 through OLP-0321. The accepted PDF has 420 pages and exact page evidence for 3,414 semantic segments. The EPUB contains 19,671 native MathML elements, 31 self-contained SVG figures, 1,335 validated internal links and matching unit/segment anchors. Independent rebuilds are byte-identical; EPUBCheck 5.4.0 reports no messages. Fifty-six wide and reader-width browser captures were automatically checked for overflow, broken images and browser errors, and 14 new-chapter views were visually inspected. All 420 PDF pages received an image survey with selected full-resolution checks. The 369 editable drafts remain in the working tree; OLP-0370 is next. The published v0.7.0 source snapshot stops at OLP-0362; the last seven drafts are not yet in a reader release.

## Rebuild the current reader on Windows

Requires Python 3, XeLaTeX with fontspec, amsmath/amsthm, bidi, TikZ, natbib, hyperref and the Amiri font. From this repository:

```powershell
python tools/build_cumulative_reader.py --through-unit 321 --preamble ./tools/cumulative-reader-preamble-v070.tex --build-dir ./build/reader-v070
./tools/guard_tex.ps1 -Passes 3 -BuildDirectory ./build/reader-v070 -DocumentBases reader
python tools/check_translation.py
```

The direct cumulative LaTeX asset can reproduce the released PDF from inside the complete source ZIP:

```powershell
Copy-Item ./releases/02-openlogic-ps-Arab-PK-cumulative-through-incompleteness-v0.7.0.tex ./releases/reader.tex
./tools/guard_tex.ps1 -Passes 3 -BuildDirectory ./releases -DocumentBases reader
```

The guard acquires `Global\InterlanguageTeXSlotV1` for every TeX pass and log check. Derive and render the 31 EPUB figures before building the reflowable reader:

```powershell
python tools/derive_cumulative_epub_figures.py --output ./build/v070-figures.json
python tools/render_cumulative_epub_figures.py --phase prepare --expected-figures 31 --inventory ./build/v070-figures.json --build-dir ./build/epub-v070-figures
$figureBases = 1..31 | ForEach-Object { 'figure-{0:D3}' -f $_ }
./tools/guard_tex.ps1 -Passes 1 -BuildDirectory ./build/epub-v070-figures -DocumentBases $figureBases
python tools/render_cumulative_epub_figures.py --phase convert --expected-figures 31 --inventory ./build/v070-figures.json --build-dir ./build/epub-v070-figures --output-dir ./build/epub-v070-svg
python tools/build_cumulative_epub.py --through-unit 321 --reference-map ./evidence/V070_EPUB_REFERENCE_MAP.json --build-dir ./build/epub-v070 --figures-dir ./build/epub-v070-svg
python tools/validate_cumulative_epub.py --epub ./build/epub-v070/openlogic-ps-Arab-PK-cumulative-through-incompleteness-v0.7.0.epub --build-record ./build/epub-v070/build-epub.json --alignment ./evidence/ALIGNMENT.jsonl --reference-map ./evidence/V070_EPUB_REFERENCE_MAP.json --output ./build/epub-v070/validation.json
```

The complete source ZIP includes the accepted reference map, figure derivation, builders, styles, diagrams and direct cumulative LaTeX. Compare rebuilt files with the versioned SHA-256 manifest.

## Attribution and license

Adapted from the [Open Logic Project](https://openlogicproject.org/), whose contributor attribution and component notices are preserved in `upstream/`. The source text and this translation are available under [Creative Commons Attribution 4.0 International](LICENSE.md); inherited component exceptions remain applicable. This adaptation is machine-generated and independently maintained; upstream endorsement is not implied.
