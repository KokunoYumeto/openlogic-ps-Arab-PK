# B202 source and target preaudit — OLP-0608

The frozen source is `content/methods/proofs/example-2.tex`, SHA-256
`cbef120cea559b153f4e6b828d2fe7942050d3534e3bb61e642fd467f897aa80`.
The checked target SHA-256 is
`4f62f8cfef3bd1d54369b83fcb074ff5511c042869aa42f3a5e2a924a2b6d3b1`.
The focused checker passes 9 paired blocks, 4 changed blocks and 86 exact
ordered active math spans. Term tokens, comments, identifiers, structural
commands, CRLF and final newline match. Registration and cumulative QA are
still pending.

The proof assumes `A ⊆ C` and proves `A ∪ (C ∖ A) = C` through both
inclusions. The forward inclusion uses cases on membership in `A` or
`C ∖ A`. The reverse inclusion uses excluded middle on `z ∈ A`; in the
negative case it combines `z ∈ C` with `z ∉ A`. The translation retains
the conditional and implicit universal scope, the two inclusions, and the
proof's pedagogical commentary. It does not turn the reverse implication
into an unsupported three-way disjunction.

**OLSTH-034:** Frozen source lines 54–55 print the second inclusion as
`$C \subseteq (A \cup (C \setminus A)$`, with an unmatched outer opening
parenthesis. The target retains the exact formula span at lines 53–54 and
discloses the printed omission at lines 54–56. The frozen source and its
formula are not silently repaired. This is a punctuation/syntax defect,
not a counterexample to the stated set identity.

Canon actually consulted: `PK-IQRAM-P1-PROSE` for Pakistani scholarly
orthography and register; `AF-MOE-P11-SUBSET`, `AF-MOE-P15-UNION`, and
`AF-MOE-P17-DIFFERENCE` as explicitly labelled Afghan regional technical
comparators for subset, union and difference; `AF-NIAZMAN-P8-TRUTH-TABLE`
as a regional witness for negation/truth-value exposition. The actual
frozen English proof governs logical content. These pages do not attest
the exact Pakistani technical expression for excluded middle, which
remains an earlier documented provisional choice.
