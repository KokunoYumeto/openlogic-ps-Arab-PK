# B194 preliminary frozen-source audit — OLP-0600

The next frozen unit is content/set-theory/choice/vitali.tex, SHA-256
e9ae48138df4af723de80b69d70d43e2a77f3cc9c0ec680eded3a333c0892b32.
It has 271 source lines. The target is fully drafted and
focused-checked but unaccepted: B194_VITALI_DRAFT_QA.json passes
37 paired blocks, 33 changed blocks, and 135 exact ordered active
math spans. Identifiers, citations, term tokens, structures, and
source newline style match.

Three printed issues have visible Pashto disclosures in the target;
the frozen formulas and identifiers remain exact.

1. Lines 35–77 define `\rotationsgroup` as rotations through *rational
   radian values* in `[0,2\pi)` and claim that this is a group under
   composition and inverse. This set is not closed: the rotations by
   4 and 4 radians belong to the stated set, but their composition
   has angle `8-2\pi`, which is irrational. Similarly `2\pi-r` is
   irrational for nonzero rational `r`, so the printed inverse claim
   fails. The second-half basis claim at lines 69–77 consequently
   fails as printed. Rational *multiples of* `\pi` would be a different
   construction; the target does not silently substitute it for the
   frozen text. Target disclosure OLSTH-029 is at line 68.

2. At frozen source line 159, the proof uses `R_1`, although the only
   first-half rotation group introduced is `\rotationsgroup_1`.
   The target retains the undefined identifier at line 177 and
   discloses the mismatch at line 193 as OLSTH-031.

3. In the measure proof at lines 257–259, `\rho` is quantified over
   `C`, a set of points chosen on the circle, while the expression
   `\funimage{\rho}{C}` requires `\rho` to be a rotation from
   `\rotationsgroup`. The printed quantifier is ill-typed. Preserve
   and disclose it; the target retains both occurrences at lines
   288 and 291 and notes the issue at line 307 as OLSTH-030.

These are draft source-audit observations only. Line-precise
source-correction records, canon and terminology decisions, 37-block
semantic review, dual cumulative QA and canonical replay remain before
acceptance. TeX slot availability never suspends translation.
