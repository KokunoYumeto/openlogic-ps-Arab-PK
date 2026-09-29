# B190 source and target preaudit — OLP-0596

The frozen source is content/set-theory/choice/wellorderingproblem.tex,
SHA-256 9ca7bb6570d323e7caebb910c975827a9411c1bbe2b4dabd6d41f9ebe2f04fa4.
The target at the same relative path under ps-Arab-PK is fully drafted
and focused-checked in B190_WELLORDERING_CHOICE_DRAFT_QA.json: 18 paired
blocks, 15 changed blocks, 45 exact ordered active math spans, identical
identifiers, comments, citations, environments, term tokens and CRLF
without a final newline. It is staging only; no cumulative acceptance
or render is claimed.

The chapter defines a choice function on the nonempty members of its
domain and proves the equivalence of Choice and Well-Ordering over ZF.
The source's Cantor quotation and bibliographic locators are preserved
and translated. The set-theory choice term remains انتخاب as used in
the preceding milestone and Choice introduction; the earlier general
term ټاکنه is recorded as a variant for later terminology review.

OLSTH-025: source line 61 states that once the first stopping stage is
reached, g(delta) is set to A for every delta no greater than alpha.
That overwrites earlier chosen element values and conflicts with the
following injectivity claim. The target keeps the printed formula at
line 73 and discloses the unresolved stopping-rule error at line 80.

OLSTH-026: source line 52 initializes g(0)=f(A), although for empty A
the Choice function on nonempty subsets has empty domain. The printed
proof has not handled this edge case. The target keeps the formula at
line 64 and discloses the missing base case at line 85.

The rendered Pakistani scholarly prose witness is used only for
orthography and exposition. The Afghan cardinal-comparison witness
is a labelled regional comparator, not exact Pakistani specialist
attestation. Register the two source actions, consultation record and
block semantics, then run independent cumulative QA and decision
replay before acceptance. TeX availability does not suspend this work.
