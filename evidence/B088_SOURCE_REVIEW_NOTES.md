# B088 source and target review — OLP-0394

- Frozen revision: `9620cc73f9c8e0ad003c514a5d3748f29611c4c0`.
- Source: `content/many-valued-logic/three-valued-logics/lukasiewicz.tex`, 10,066 bytes, SHA-256 `fe499a0fa941ad8d370b2f0346660d76aad7b4aad999a54ea88f79cdacc2641a`.
- Pashto draft SHA-256: `8beb7e5531c998fc1585901b168641754ed89a28084d5cd2e0ff67c47a783553`.
- Pairing: 22 source blocks and 22 target blocks; section ID, definition label, exercise labels and references, environments, term tokens, structural macros and table cells are retained. The three enumerated math changes below are the complete math difference.

The introduction (source lines 13–19) presents the sea-battle motivation as a question about a sentence *today*, rather than asserting that the future event will not occur. The historical quotation (21–35) retains Warsaw, noon on 21 December of the following year, both necessary/impossible counterfactuals, the two ordinary values 0 and 1, and the proposed one-half value. The footnote (37–39) limits the historical sense of “possible” to possible but not necessary. The Pashto renders this fully and distinguishes this third **truth value** from partial-function undefinedness.

Lines 41–75 explain negation, conjunction, and conditional for a future contingent. The target retains the choice `\tf{\lif}(\Undef,\Undef)=\True` specifically to keep `!A \lif !A` a tautology. The four truth tables (77–119) remain unchanged, including the sole designated value `\True`; none of their entries was silently revised. The definition, valuation claim, proposition, three exercises on tautologies, counterexample, entailment exercise, and modal extension (121–229) have been paraphrased back against the source. The closing defect claim (231–240) is kept, with the last source value corrected below.

Three source-confirmed local corrections are disclosed in adjacent Pashto prose; the English archive remains byte-identical:

1. `OLMVL-002`, source 53–55: the displayed conjunction equation repeats `(\False,\Undef)` on both sides. The table at 94–100 includes both symmetric input orders with value `\False`. The target changes only the second pair to `(\Undef,\False)` and explains the repeated source order.
2. `OLMVL-003`, source 172–179: the first exercise formula has one surplus closing parenthesis after `q`, yielding malformed syntax. The target removes that surplus character and notes it.
3. `OLMVL-004`, source 231–240: under `v(p)=\Undef`, the stated value of `\lnot\Diamond(p\land\lnot p)` is `\Undef`. The unchanged tables instead give `p\land\lnot p=\Undef`, `\Diamond(\Undef)=\True`, then `\lnot\True=\False`. The target prints `\False` and notes the source/table conflict. Both values would fail to designate the formula, so the larger non-tautology conclusion is unchanged.

Reverse paraphrases of the draft: (1) a future-contingent statement receives a third value because its present truth or falsity is not settled; (2) conjunction with False is False, while conjunction with True and Undef is Undef; (3) the conditional's Undef/Undef case is deliberately True to preserve reflexivity; (4) a valuation assigning Boolean values to each variable used by a formula reproduces its classical value; (5) some classical tautologies fail in this three-valued matrix, and one displayed classical tautology can even become False; (6) possibility holds unless falsity is settled, necessity holds only if truth is settled; (7) the modal contradiction example exposes the insufficiency of this three-valued extension. Each statement was checked against the corresponding frozen lines, formulas and tables.

This is a bounded owner source review, not a human specialist certification. The 372-unit reader candidate and pagination of this later draft remain separate pending work.
