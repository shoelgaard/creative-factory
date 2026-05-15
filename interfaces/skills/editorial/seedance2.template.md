# Seedance 2.0 prompt template

Seedance prefers shorter, denser motion+style descriptions than Veo. The
`prompt_builder.py` strips the long narrative and emits a compact one-paragraph
brief built from the same brand source + user steer.

Tuning rules:

- Keep total prompt < 100 words. Seedance dilutes when overfed.
- Always say what the camera does, not what it doesn't. ("Slow push-in" beats
  "no whip-pan".)
- Lead with subject + brand-aesthetic anchor (Kinfolk/Frama/Aesop) in the same
  sentence so the model locks tone immediately.
- Seedance defaults to 5-second clips at 1080p (vs Veo's 8s with audio). When
  comparing side-by-side, evaluate them on *texture, motion realism, brand
  fidelity* — not duration parity.
