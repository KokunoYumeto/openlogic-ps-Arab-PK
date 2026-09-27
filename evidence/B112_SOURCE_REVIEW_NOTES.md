# OLP-0422 source review — frames

- Frozen `content/normal-modal-logic/frame-definability/frames.tex`, revision `9620cc73f9c8e0ad003c514a5d3748f29611c4c0`, 1,795 bytes, SHA-256 `2dab4bab23543be815492a62159b5e44069c50f55fee06e8a866446634a75b39`.
- The opening definition requires a **nonempty** world set W and a binary relation R on W. A based-on model adds any valuation V. The Pashto draft retains the quantifier over valuations and does not conflate a frame with one model.
- The two validity definitions distinguish truth of A in every model based on one frame from truth in every frame of a class. The following paragraph explicitly contrasts schema truth in a single model with frame validity, and states the T/reflexivity correspondence in both directions.
- The remark identifies a class of frames with the class of **all models based on any member frame**. It then restricts globally valid formulas or schemas to any frame class. Empty classes are not silently excluded.
- The draft `ps-Arab-PK/content/normal-modal-logic/frame-definability/frames.tex` passes 12/12 paired-block, formula, identifier, structure and token parity in `B112_STAGING_QA_OLP-0422.json`, and an independent `qa_range.py --start 422 --end 422` check has no failures. This is a staging draft; B112 cumulative acceptance is pending.
