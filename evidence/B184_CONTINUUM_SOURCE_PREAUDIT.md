# B184 source and target preaudit — OLP-0590

Status: complete focused draft, not yet an accepted editable unit. The frozen English source is content/set-theory/card-arithmetic/ch.tex; its manifest SHA-256 is b1bdee185ce2a21eeba54cce52ebec13154b54b77a6652820ad4f7ac61e8b212. The Pakistani Pashto draft has 25 corresponding blocks and preserves all 58 ordered active mathematical spans, identifiers, structural commands, comments, and CRLF line endings. The exact focused receipt is B184_CONTINUUM_DRAFT_QA.json.

The section introduces the aleph and beth recursions, proves each term is a cardinal, states that every infinite cardinal is an aleph, then distinguishes GCH and CH from the theorems of ZFC. It also explains the limits of independence results for questions of truth. Mathematical letters, cardinal inequalities, citations and footnotes are retained.

Two source-local issues are disclosed beside the target passages:

- OLSTH-020, English source lines 35–36, target disclosure line 37: “The rest of the definition of a” has the wrong referent after the simultaneous aleph and beth recursions. The Pashto sentence names the two sequences; the adjacent note identifies the printed wording. No formula is changed.
- OLSTH-021, English proof beginning line 70, target disclosure line 88: the induction hypothesis quantifies over every smaller cardinal, including finite cardinals for which no aleph index has been defined; the claimed base at the first infinite cardinal is not separately handled. The source's displayed formulas and claim remain unchanged. This is a disclosed, unrepaired proof gap, not an assertion of author approval.

The Pakistani prose witness PK-IQRAM-P1-PROSE supports orthography and explanatory style. The rendered Afghan mathematical comparator AF-BUKOVSKY-P133-CANTOR-THEOREM supports the powerset/cardinality setting but does not attest an exact Pakistani term for the continuum hypothesis. AF-NIAZMAN-P178-ORDER was inspected and is about temporal ordering; it is not used as a technical continuum witness. The new terms for continuum, GCH/CH, aleph/beth and cofinality therefore remain explicitly provisional against the frozen source definitions. The original author has not approved the narrow corrections.

Next: register both source notes, term decisions and block-level reverse paraphrases after the B183 canonical replay freezes its shared inputs; then run cumulative 590-unit QA and replay before acceptance.
