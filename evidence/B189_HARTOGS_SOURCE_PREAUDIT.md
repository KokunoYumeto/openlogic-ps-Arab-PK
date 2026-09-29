# B189 source and target preaudit — OLP-0595

The frozen source is content/set-theory/choice/hartogs.tex at SHA-256
ffe4c3f0a800bd7893a39e68d109ca1eb9662b5f29cda42393cbc5777cf557c4.
The Pashto draft is the same relative path under ps-Arab-PK. The focused
B189_HARTOGS_DRAFT_QA.json passes 12 paired blocks, 9 changed blocks and
56 ordered active mathematical spans. Identifiers, environment boundaries,
citations, structural commands, term tokens and CRLF without a final newline
match the frozen source. This is checked staging, not cumulative acceptance.

The section proves Hartogs' lemma in ZF, then the equivalence of
Well-Ordering and comparability of all set cardinalities. The target
preserves the proof's quantifiers, injections, formulas and citation keys.
The rank-minimal representative context is the preceding Tarski–Scott unit.
The previously inspected Pakistani prose page supports orthography and
scholarly exposition only; the Afghan cardinal-comparison page is a
labelled regional comparator. Neither page certifies the exact Pakistani
name for Hartogs' lemma.

OLSTH-023: the source at line 33 says B is a subset of the relation R
while deriving the order type of a member of C. The definition of C
requires B to be a subset of A, and R is a relation on B. The target
retains the printed math at line 37 and discloses the wrong referent at
line 42 without claiming an author-approved repair.

OLSTH-024: the source at lines 80–81 nests a cardinal-equivalence
relation as the first argument of another such relation. This is not a
well-formed statement of the cardinal maximum theorem cited from
card-arithmetic/simp.tex. The target preserves that exact expression
at lines 106–107 and discloses the defect at line 113; it does not invent
a replacement formula.

The source also reuses the outer ordinal's alpha as a variable inside
the relation displayed at line 41. That shadowing deserves expert review;
the target retains the formula exactly and does not assert a separate
repair. Source actions OLSTH-023 and OLSTH-024, specialist terminology,
block-level reverse paraphrases and cumulative QA/replay remain to be
registered before OLP-0595 acceptance. TeX availability does not suspend
translation.
