# Visual Rendering Policy

These rules apply to normal preview and final renders across video modes.

- Do not add generated montage labels, counters, arrows, debug text, job IDs, provider names, file paths, or application branding inside the video.
- Render only one intentional subtitle layer. Prefer one ASS subtitle burn-in layer for final videos.
- Treat `on_screen_text` fields as planning notes unless a mode explicitly enables a reviewed graphics workflow.
- Do not use generated motion placeholders, flat color cards, primitive diagrams, or fake visual stand-ins in normal preview/final renders.
- Placeholder visuals are allowed only in explicit debug modes such as `--debug-placeholders`.
- Do not trust provider tags alone. Visually review downloaded sources when the scene requires a concrete subject or action.
- Reject off-topic visual results even when they were returned by a relevant search query.
- If a relevant visual source cannot be found, mark the scene as `needs_assets`, write the missing scene report, and do not call the output finished.
- Do not silently fallback to unrelated clips just to fill the timeline.
