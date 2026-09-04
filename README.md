# OpenLogic in Pashto — Pakistan

An independent machine translation of the Open Logic Project into Pashto in Arabic script, for a Pakistan curriculum target. Pakistani prose and orthography are primary; Afghan Pashto sources are explicitly labelled regional comparators.

**Work in progress: 73 of 722 source units are translated drafts. The [33-page, 23-unit reader](readers/openlogic-ps-Arab-PK-sets-relations-functions.pdf) contains the complete sets, relations and functions chapters and has passed deterministic guarded build and full visual inspection for the v0.3.0 release. Fifty additional front matter, size-of-sets, arithmetization, infinite-set, propositional syntax-and-semantics, proof-system overview and opening sequent-calculus drafts are included as editable sources. The complete edition remains under production.** This repository does not claim a complete book or human-reviewed translation. See [the translation catalogue](https://github.com/KokunoYumeto/OpenLogic-translations).

Read the currently published [sets-and-relations PDF](readers/openlogic-ps-Arab-PK-sets-relations.pdf), or the earlier [sets-only PDF](readers/openlogic-ps-Arab-PK-sets.pdf). The sets, relations and functions PDF has not yet been accepted or released. Versioned PDF and editable source bundles are available from [GitHub releases](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases) and the [Zenodo edition lineage](https://doi.org/10.5281/zenodo.22307197).

The prepared reader chapters cover sets, set operations, tuples and Cartesian products, Russell's paradox, relations as sets, philosophical reflections, relation properties, equivalence classes, orders, graphs, trees, relation operations, function types, graphs of functions, inverses, composition and partial functions. They include the original examples, exercises, captions and diagrams. The editable Pashto source mirrors upstream file paths in `ps-Arab-PK/`. Separate edition notes and adjacent disclosures explain inherited notation ambiguities and stable source corrections without changing frozen English bytes.

The [expert-review log](EXPERT_REVIEW.md) records all 88 current terminology choices and 46 difficult translation/source decisions with a machine-readable companion at `evidence/EXPERT_REVIEW_LOG.jsonl`. It gives exact locations, checked authorities, honest absence findings, rationale, alternatives, uncertainty and concrete review questions. It is partial at the stated draft coverage and welcomes asynchronous corrections; expert response is not a release gate. [Source corrections](SOURCE_CORRECTIONS.md) separately identify 40 adopted findings: five audited function fixes, ten shared size-of-sets fixes, four additional size-of-sets findings, fourteen arithmetization findings, two infinite-set findings, three propositional-logic findings, and two proof-system findings. The [audit-retraction record](evidence/SOURCE_AUDIT_RETRACTIONS.jsonl) preserves the explicit withdrawal of one false shared alert; no correction was applied for it.

## Source and evidence

`upstream/` preserves the raw English source at revision `9620cc73f9c8e0ad003c514a5d3748f29611c4c0` of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic). All 722 content hashes were verified. `evidence/SOURCE_MANIFEST.jsonl` retains the stable OLP unit IDs and both raw-source and historical Windows-checkout hashes. Different newline representations are provenance, not errors.

Canon includes a native Pashto semantics article by Bushra Iqram at the Pashto Academy, University of Peshawar; native Afghan mathematical logic, set theory and grade-7 mathematics as regional comparators; and Tegey and Robson's reference grammar for grammatical analysis. The evidence indexes distinguish prose, grammar and concept-specific attestation. They record source and inspected-page hashes. Original canon PDFs remain private reference copies and are not redistributed here.

Terminology remains provisional when the consulted evidence does not establish the exact technical sense. In particular, descriptive labels for extensionality and power set are decisions, not claims of a settled Pakistani standard. Canon consultation is recorded per source-aligned paragraph. Native witnesses guide language; the English source governs mathematics.

## Validation and limits

Validation checks source hashes, paragraph alignment, environments, formula bodies, term tokens, references, Unicode and residual ordinary English. Semantic review includes reverse paraphrases and specifically checks membership versus subset, both directions of biconditionals, bounded quantifiers, product cardinality, and uniqueness versus existence. Native glyph joining, diacritics, punctuation and left-to-right mathematical isolation are inspected in actual renders. These checks do not establish native-reader approval or eliminate all translation uncertainty.

English comments and identifiers remain as structural metadata. The proper name `Ruth` inside an original formula is a documented exception. Formula text is translated. The `psOblique` wrapper realizes required Pashto case inflection while retaining the original term token and key.

The current combined renderer follows three actual chapter drivers, includes 23 source units, and produces the accepted 33-page reader. Its conditional references resolve against the chapters present in this partial reader; all translated source branches remain in editable form. The complete size-of-sets draft retains both elementary and abstract alternatives, and the complete arithmetization draft retains both Dedekind-cut and Cauchy-sequence constructions. The infinite-set chapter, the propositional syntax-and-semantics chapter and its proof-system overview are complete as editable drafts; the first five sequent-calculus units now add the chapter driver and its propositional, quantifier and structural rule foundation. These later drafts are not integrated into the current reader. Whole-edition coverage and treatment of the 80 units outside the ordinary reader graph remain outstanding. No complete-reader claim follows from preserving all English source files.

## Rebuild the current reader on Windows

Requires Python 3, XeLaTeX with fontspec, amsmath/amsthm, bidi, TikZ, natbib, hyperref and the Amiri font. From this repository:

```powershell
python tools/build_reader.py
./tools/guard_tex.ps1 -Passes 4 -BuildDirectory ./build/reader -DocumentBases reader
python tools/check_translation.py
```

The output is `build/reader/reader.pdf`. The guard acquires `Global\InterlanguageTeXSlotV1` with one bounded timeout, captures descendants in a Windows job before resuming the engine, holds the slot through all passes and log checks, and releases it in `finally`. When occupied, it starts no TeX process. Fixed `SOURCE_DATE_EPOCH` supports deterministic PDF replay. The earlier `build_chapter.py` script remains available for the sets-only reader.

## Attribution and license

Adapted from the [Open Logic Project](https://openlogicproject.org/), whose contributor attribution and component notices are preserved in `upstream/`. The source text and this translation are available under [Creative Commons Attribution 4.0 International](LICENSE.md); inherited component exceptions remain applicable. This adaptation is machine-generated and independently maintained; upstream endorsement is not implied.
