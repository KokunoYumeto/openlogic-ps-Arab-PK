# OpenLogic in Pashto — Pakistan

The Pashto translation and mathematical review through OLP-0311 were produced by OpenAI Codex — GPT-5.6 Sol, Ultra effort. The B057 evidence replay, Pakistani-Pashto access material, and translation, source corrections and review of OLP-0312 through OLP-0556 were produced by OpenAI Codex — GPT-6 Sol, Ultra effort. The two predicativity-label corrections in OLP-0177 were also produced by OpenAI Codex — GPT-6 Sol, Ultra effort. The accepted OLP-0557–0586 drafts were also produced by OpenAI Codex — GPT-6 Sol, Ultra effort. No human translation or specialist approval is claimed. [د پښتو اصلي معلوماتو پاڼه](README.ps-Arab-PK.md) is the primary access page.

An independent machine translation of the Open Logic Project into Pashto in Arabic script, for a Pakistan curriculum target. Pakistani prose and orthography are primary; Afghan Pashto sources are explicitly labelled regional comparators.

**Work in progress: 586 of 722 source units are translated and structurally verified. The current [420-page cumulative PDF](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.pdf) and [31-chapter reflowable EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.epub) cover the first 321 units. The 265 later accepted editable drafts cover second-order and many-valued logic, normal modal logic, temporal and epistemic logic, intuitionistic logic, material and strict conditionals, and complete sphere semantics for counterfactuals, including the limits of antecedent strengthening, transitivity and contraposition. The set-theory part and iterative-conception chapter are also accepted, including extensionality, Russell’s paradox, predicativity, cumulative stages, urelements and the Frege appendix. The next chapter’s driver, detailed stage principles, Separation, Union and Pairs are accepted; No Last Stage is explicitly an additional premise. The complete Zermelo chapter now also covers Powersets, Infinity, the exact Zminus axiom list, alternative natural-number representations and the bounded closure/intersection appendix. OLSTH-003 retains the source’s arbitrary-witness successor claim with an adjacent premise/scope disclosure; it makes no full-countermodel or independence claim. Source proof gaps and sphere-prose scope corrections remain explicitly disclosed. The remaining 136 units are outside accepted coverage; OLP-0587 is next untranslated. The [corrected v0.7.1 GitHub release](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases/tag/v0.7.1-incompleteness-formula-repair) provides the PDF preview, direct cumulative LaTeX, complete source ZIP, EPUB, validation record and checksums.** This remains an incomplete machine-generated edition without human specialist approval. See [the translation catalogue](https://github.com/KokunoYumeto/OpenLogic-translations).

Read the current [cumulative PDF](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.pdf) or [EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-incompleteness.epub). The previous [computability PDF](readers/openlogic-ps-Arab-PK-cumulative-through-computability.pdf) and [EPUB](readers/openlogic-ps-Arab-PK-cumulative-through-computability.epub), and earlier editions, remain available through [GitHub releases](https://github.com/KokunoYumeto/openlogic-ps-Arab-PK/releases). The [current version DOI](https://doi.org/10.5281/zenodo.22991939) identifies the corrected reader; the [Zenodo edition lineage](https://doi.org/10.5281/zenodo.22307197) preserves earlier records and their reading previews.

The current reader covers foundations; sets, relations and functions; cardinality; propositional and first-order logic; four proof systems and completeness; model theory; recursive functions and computability; Turing machines; arithmetized syntax; and the incompleteness theorems. It preserves examples, exercises, formulas, tables, proof trees, tableaux and diagrams under the frozen upstream default profile. Editable Pashto sources mirror upstream paths in `ps-Arab-PK/`. Adjacent disclosures explain inherited notation ambiguities and source corrections without changing frozen English bytes.

The earlier v0.7.0 PDF printed active `!` metavariables literally on physical pages 413–414. The v0.7.1 PDF corrects them; those pages were visually inspected, and independent three-pass builds agree byte for byte. The repair shifts 108 source-segment page anchors. The v0.7.1 EPUB uses the corrected 785-reference map, passed byte-identical independent replay, and passed EPUBCheck 5.4.0 with zero messages. The earlier release remains available.

The [Pakistani-Pashto expert-review guide](EXPERT_REVIEW.ps-Arab-PK.md) is the primary review route; [English detail](EXPERT_REVIEW.md) is supplementary. The [canonical register](evidence/DECISIONS.json), [full index](evidence/TRANSLATION_DECISIONS_FULL.md), [priority index](evidence/PRIORITY_REVIEW.md), [paired-occurrence CSV](evidence/DECISION_OCCURRENCES.csv), [schema](evidence/translation-decision.schema.json), and [validation receipt](evidence/TRANSLATION_DECISION_QA.json) record 741 decisions and 28,514 exact source/target occurrence pairs. The decision index retains 18,455 exact v0.7.0 reader locators; 10,059 later-draft occurrences remain pending. For the corrected reader, use the [v0.7.1 3,414-segment page map](evidence/V071_READER_OCCURRENCE_PAGES.json), which records 108 shifted anchors. One floating Turing-machine figure has a documented anchor-order exception. The [source corrections](SOURCE_CORRECTIONS.md) record 440 source treatments, including disclosed unresolved gaps; four historical retractions remain documented in [the audit record](evidence/SOURCE_AUDIT_RETRACTIONS.jsonl). Expert feedback is welcome but is not a release gate.

## Source and evidence

`upstream/` preserves the raw English source at revision `9620cc73f9c8e0ad003c514a5d3748f29611c4c0` of [OpenLogicProject/OpenLogic](https://github.com/OpenLogicProject/OpenLogic). All 722 content hashes were verified. `evidence/SOURCE_MANIFEST.jsonl` retains the stable OLP unit IDs and both raw-source and historical Windows-checkout hashes. Different newline representations are provenance, not errors.

Canon includes a native Pashto semantics article by Bushra Iqram at the Pashto Academy, University of Peshawar; native Afghan mathematical logic, set theory and grade-7 mathematics as regional comparators; and Tegey and Robson's reference grammar for grammatical analysis. The evidence indexes distinguish prose, grammar and concept-specific attestation. They record source and inspected-page hashes. Original canon PDFs remain private reference copies and are not redistributed here.

Terminology remains provisional when the consulted evidence does not establish the exact technical sense. In particular, descriptive labels for extensionality and power set are decisions, not claims of a settled Pakistani standard. Canon consultation is recorded per source-aligned paragraph. Native witnesses guide language; the English source governs mathematics.

## Validation and limits

Validation checks source hashes, paragraph alignment, environments, formula bodies, term tokens, references, Unicode and residual ordinary English. Semantic review includes reverse paraphrases and specifically checks membership versus subset, both directions of biconditionals, bounded quantifiers, product cardinality, and uniqueness versus existence. Native glyph joining, diacritics, punctuation and left-to-right mathematical isolation are inspected in actual renders. These checks do not establish native-reader approval or eliminate all translation uncertainty.

English comments and identifiers remain as structural metadata. The proper name `Ruth` inside an original formula is a documented exception. Formula text is translated. The `psOblique` wrapper realizes required Pashto case inflection while retaining the original term token and key.

The current PDF and EPUB follow 31 chapter drivers and cover OLP-0001 through OLP-0321. The accepted PDF has 420 pages and exact page evidence for 3,414 semantic segments. The EPUB contains 19,671 native MathML elements, 31 self-contained SVG figures, 1,335 validated internal links and matching unit/segment anchors. Independent rebuilds are byte-identical; EPUBCheck 5.4.0 reports no messages. Fifty-six wide and reader-width browser captures were automatically checked for overflow, broken images and browser errors, and 14 new-chapter views were visually inspected. The v0.7.0 PDF received a 420-page image survey; the changed v0.7.1 pages were inspected at full resolution. The v0.7.1 source snapshot includes 405 editable drafts, while the reader still covers the first 321 units. The current source-hash rendered gate covers105 units after the OLP-0177 terminology revision; the unchanged published321-unit reader remains historical. The source tree includes OLP-0406–0586 as later accepted drafts; OLP-0587 is next untranslated.

## Rebuild the current reader on Windows

Requires Python 3, XeLaTeX with fontspec, amsmath/amsthm, bidi, TikZ, natbib, hyperref and the Amiri font. From this repository:

```powershell
python tools/build_cumulative_reader.py --through-unit 321 --preamble ./tools/cumulative-reader-preamble-v070.tex --build-dir ./build/reader-v071
./tools/guard_tex.ps1 -Passes 3 -BuildDirectory ./build/reader-v071 -DocumentBases reader
python tools/check_translation.py
```

The direct cumulative LaTeX asset can reproduce the released PDF from inside the complete source ZIP:

```powershell
Copy-Item ./releases/02-openlogic-ps-Arab-PK-cumulative-through-incompleteness-v0.7.1.tex ./releases/reader.tex
./tools/guard_tex.ps1 -Passes 3 -BuildDirectory ./releases -DocumentBases reader
```

The guard acquires `Global\InterlanguageTeXSlotV1` for every TeX pass and log check. Derive and render the 31 EPUB figures before building the reflowable reader:

```powershell
python tools/derive_cumulative_epub_figures.py --output ./build/v071-figures.json
python tools/render_cumulative_epub_figures.py --phase prepare --expected-figures 31 --inventory ./build/v071-figures.json --build-dir ./build/epub-v071-figures
$figureBases = 1..31 | ForEach-Object { 'figure-{0:D3}' -f $_ }
./tools/guard_tex.ps1 -Passes 1 -BuildDirectory ./build/epub-v071-figures -DocumentBases $figureBases
python tools/render_cumulative_epub_figures.py --phase convert --expected-figures 31 --inventory ./build/v071-figures.json --build-dir ./build/epub-v071-figures --output-dir ./build/epub-v071-svg
python tools/build_cumulative_epub.py --through-unit 321 --edition-version 0.7.1 --reference-map ./evidence/V071_EPUB_REFERENCE_MAP.json --build-dir ./build/epub-v071 --figures-dir ./build/epub-v071-svg
python tools/validate_cumulative_epub.py --epub ./build/epub-v071/openlogic-ps-Arab-PK-cumulative-through-incompleteness-v0.7.1.epub --build-record ./build/epub-v071/build-epub.json --alignment ./evidence/ALIGNMENT.jsonl --reference-map ./evidence/V071_EPUB_REFERENCE_MAP.json --output ./build/epub-v071/validation.json
```

The complete source ZIP includes the corrected reference map, figure derivation, builders, styles, diagrams and direct cumulative LaTeX. Compare rebuilt files with the versioned SHA-256 manifest.

## Attribution and license

Adapted from the [Open Logic Project](https://openlogicproject.org/), whose contributor attribution and component notices are preserved in `upstream/`. The source text and this translation are available under [Creative Commons Attribution 4.0 International](LICENSE.md); inherited component exceptions remain applicable. This adaptation is machine-generated and independently maintained; upstream endorsement is not implied.

Ordinal ordering is now accepted through OLP-0551, including well-order induction and full initial-segment comparison. OLSTH-004 corrects the source prose’s domain/range typo beside an explicit disclosure; all formal signatures and formulas remain unchanged. The five following von Neumann, induction, Replacement and order-type units are now also accepted.

Von Neumann ordinals, both transfinite induction forms, the complete Burali-Forti proof, unique-y Replacement, the exact ZFminus axiom list and full ordinal representation are now accepted through OLP-0556. The following eight successor, stage, recursion, Foundation, Z/ZF and rank units are now accepted through OLP-0564. OLSTH-005 adds the disclosed empty-function base case; OLSTH-006 corrects the unbound bound-variable case; OLSTH-007 corrects the own-rank stage index. Frozen English source bytes remain unchanged. Seven further Replacement chapter units, OLP-0565–0571, are now accepted. The extrinsic/intrinsic distinction, LT and Zr strength comparison, limitation-of-size critique, absolute-infinity argument and Reflection Schema are translated with the frozen formulas and references preserved.

The guarded556-unit reader first pass failed at the inherited OLP-0426 TeX brace typo. The generator now repairs that grouping and places the OLP-0061 Pashto full stop inside its existing text argument. Frozen source and accepted translation bytes remain unchanged. The corrected cumulative input is prepared; successful compilation, reproduction and rendered page inspection remain pending. No new PDF release is claimed.

The 564-unit source QA passes 8,365 paired blocks, 5,253 recorded canon uses and 1,761 semantic samples. Two canonical register builds agreed byte for byte on 709 decisions and 27,829 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader and current-source 105-unit visual gate have different scopes.

The 571-unit source QA passes 8,435 paired blocks, 5,299 recorded canon uses and 1,821 semantic samples. Two canonical register builds agree byte for byte on 715 decisions and 27,936 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader and current-source 105-unit visual gate have different scopes.

The Reflection proof appendix OLP-0572 is accepted. Three narrow formula repairs and one prose referent correction are disclosed next to the affected text, with exact source and target locations in expert review.

The 572-unit corpus QA passes 8,454 paired blocks, 5,315 recorded canon uses and 1,850 semantic samples. Two canonical register builds agree byte for byte on 721 decisions and 28,020 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader is historical.

The finite-axiomatizability appendix OLP-0573 is accepted. Its printed assertion that every transitive set satisfies relativized Separation has a finite counterexample, disclosed beside the unchanged source claim and exercise as OLSTH-012. This identifies a gap in the supplied auxiliary proof, not a refutation of the stated theorems.

The 573-unit corpus QA passes 8,466 paired blocks, 5,323 recorded canon uses and 1,867 semantic samples. Two canonical register builds agree byte for byte on 723 decisions and 28,045 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader is historical.

The ordinal-arithmetic chapter driver and introduction OLP-0574–0575 are accepted. The five source imports remain ordered, and the transition from informal omega examples to formal ordinal arithmetic is translated.

The 575-unit corpus QA passes 8,479 paired blocks, 5,327 recorded canon uses and 1,875 semantic samples. Two canonical register builds agree byte for byte on 724 decisions and 28,057 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader is historical.

Ordinal addition OLP-0576 is accepted with tagged-copy construction, reverse lexicographic order, zero/successor/limit recursion, associativity and a noncommutative example. OLSTH-013/014 repair two narrow source formula errors beside explicit Pashto disclosures; frozen English bytes remain unchanged.

The 576-unit corpus QA passes 8,505 paired blocks, 5,350 recorded canon uses and 1,910 semantic samples. Two canonical register builds agree byte for byte on 729 decisions and 28,220 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader is historical.

The accepted OLP-0577–0581 sources cover rank and ordinal infinity, ordinal multiplication and exponentiation, the cardinal chapter driver, and Cantor’s Principle. OLSTH-015 supplies a missing rank-exercise relation; OLSTH-016 reverses finite-function parameters where the source identifies an exponent; OLSTH-017 qualifies the synthetic equivalence to nonzero base and discloses the printed zero-base gap. Frozen English bytes remain unchanged.

The 581-unit corpus QA passes 8,567 paired blocks, 5,393 recorded canon uses and 1,964 semantic samples. Two canonical register builds agree byte for byte on 737 decisions and 28,331 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader is historical.

The accepted OLP-0582–0586 sources cover cardinals as ordinals, the ZFC milestone, cardinal classification, Hume’s Principle, and the cardinal-arithmetic chapter driver. OLSTH-018 discloses and corrects a false source prose gloss that confuses a set with its cardinality; mathematical notation and frozen English bytes are unchanged.

The 586-unit corpus QA passes 8,638 paired blocks, 5,446 recorded canon uses and 2,030 semantic samples. Two canonical register builds agree byte for byte on 741 decisions and 28,514 occurrences. No expanded PDF or EPUB is accepted; the published 321-unit reader is historical.
