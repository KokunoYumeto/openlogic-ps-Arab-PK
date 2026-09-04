# OpenLogic in Pashto — Pakistan

An independent machine translation of the Open Logic Project into Pashto in Arabic script, for a Pakistan curriculum target. Pakistani prose and orthography are primary; Afghan Pashto sources are explicitly labelled regional comparators.

**Work in progress: 10 of 722 source units are translated drafts. The first reader contains the complete sets chapter: seven units, comprising one chapter driver and six substantive sections. Three additional front matter and import-driver drafts are included as editable sources. The complete edition remains under production.** This repository does not claim a complete book or human-reviewed translation. See [the translation catalogue](https://github.com/KokunoYumeto/OpenLogic-translations).

Read the [sets chapter PDF](readers/openlogic-ps-Arab-PK-sets.pdf). Versioned PDF and editable source bundles are available from [releases](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases).

The chapter covers extensionality, subsets and power sets, important number domains and sequences, unions and intersections, ordered tuples and Cartesian products, and Russell's paradox. It includes the original examples, exercises, captions and diagrams. The editable Pashto source mirrors upstream file paths in `ps-Arab-PK/`.

## Source and evidence

`upstream/` preserves the raw English source at revision `9620cc73f9c8e0ad003c514a5d3748f29611c4c0` of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic). All 722 content hashes were verified. `evidence/SOURCE_MANIFEST.jsonl` retains the stable OLP unit IDs and both raw-source and historical Windows-checkout hashes. Different newline representations are provenance, not errors.

Canon includes a native Pashto semantics article by Bushra Iqram at the Pashto Academy, University of Peshawar; native Afghan mathematical logic and grade-7 mathematics as regional comparators; and Tegey and Robson's reference grammar for grammatical analysis. The evidence indexes distinguish prose, grammar and concept-specific attestation. They record source and inspected-page hashes. Original canon PDFs remain private reference copies and are not redistributed here.

Terminology remains provisional when the consulted evidence does not establish the exact technical sense. In particular, descriptive labels for extensionality and power set are decisions, not claims of a settled Pakistani standard. Canon consultation is recorded per source-aligned paragraph. Native witnesses guide language; the English source governs mathematics.

## Validation and limits

Validation checks source hashes, paragraph alignment, environments, formula bodies, term tokens, references, Unicode and residual ordinary English. Semantic review includes reverse paraphrases and specifically checks membership versus subset, both directions of biconditionals, bounded quantifiers, product cardinality, and uniqueness versus existence. Native glyph joining, diacritics, punctuation and left-to-right mathematical isolation are inspected in actual renders. These checks do not establish native-reader approval or eliminate all translation uncertainty.

English comments and identifiers remain as structural metadata. The proper name `Ruth` inside an original formula is a documented exception. Formula text is translated. The `psOblique` wrapper realizes required Pashto case inflection while retaining the original term token and key.

This first chapter renderer is scoped to the seven listed units. Whole-edition coverage and treatment of the 80 units outside the ordinary reader graph remain outstanding. No complete-reader claim follows from preserving all English source files.

## Rebuild the chapter on Windows

Requires Python 3, XeLaTeX with fontspec, amsmath/amsthm, bidi, TikZ, hyperref and the Amiri font. From this repository:

```powershell
python tools/build_chapter.py
./tools/guard_tex.ps1 -Passes 2
python tools/check_translation.py
```

The output is `build/sets/sets.pdf`. The guard acquires `Global\InterlanguageTeXSlotV1` with one bounded timeout, captures descendants in a Windows job before resuming the engine, holds the slot through all passes and log checks, and releases it in `finally`. When occupied, it starts no TeX process. Fixed `SOURCE_DATE_EPOCH` supports deterministic PDF replay.

## Attribution and license

Adapted from the [Open Logic Project](https://openlogicproject.org/), whose contributor attribution and component notices are preserved in `upstream/`. The source text and this translation are available under [Creative Commons Attribution 4.0 International](LICENSE.md); inherited component exceptions remain applicable. This adaptation is machine-generated and independently maintained; upstream endorsement is not implied.
