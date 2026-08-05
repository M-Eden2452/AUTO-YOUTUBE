# DejaVu Sans - provenance

- **Files:** `DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`
- **Font version:** `Version 2.37` (read from the font's own `name` table,
  nameID 5)
- **Upstream project:** DejaVu fonts, <http://dejavu.sourceforge.net>
- **License:** Bitstream Vera Fonts Copyright + Arev Fonts Copyright, both
  reproduced verbatim in `LICENSE.txt`. Both are permissive: free to use,
  copy, modify and redistribute, including commercially; the only
  restriction is that a modified font must not keep the "Bitstream", "Vera",
  "Tavmjong Bah" or "Arev" names.
- **How these copies were obtained:** copied byte-for-byte from a local
  Windows installation's `%WINDIR%\Fonts\DejaVuSans.ttf` and
  `DejaVuSans-Bold.ttf`, not downloaded from the network. Copyright,
  license and version text above were extracted directly from the font
  files' own OpenType `name` table (nameID 0, 13, 14, 5) so this file
  documents the fonts' own self-declared provenance rather than a
  paraphrase.
- **SHA-256:**
  - `DejaVuSans.ttf`: `7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954`
  - `DejaVuSans-Bold.ttf`: `e6476c1b80502924294eed40894c5b18e06c181444ca953e5334262df9c27724`
- **Why bundled:** `src/production_plan/story_card_short_render.py` renders
  the `story_card_short_v1` preset with `text.font = "DejaVuSans.ttf"`.
  Pillow's `ImageFont.truetype("DejaVuSans.ttf", ...)` resolves a bare
  filename by searching `%WINDIR%\Fonts` on Windows. That directory
  happens to contain DejaVu on this machine but not on the GitHub Actions
  `windows-latest` runner, which silently fell back to Arial and rendered
  the story-card layout with different text metrics, dropping
  `content_occupancy_ratio` below the `>= 0.88` contract. Bundling the
  exact font bytes in the repository makes the render byte-for-byte
  reproducible regardless of what fonts happen to be installed on the
  machine running the test.
