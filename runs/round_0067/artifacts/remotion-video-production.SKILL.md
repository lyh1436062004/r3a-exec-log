---
name: remotion-video-production
description: Orchestrate production of real MP4 assets with Remotion from a media brief or presentation slide plan. Use when Humanize PPT requests a remotion-clip media slot, when a user asks for a programmatic Remotion video, or when a rendered video file must be produced and validated.
---

# Remotion Video Production

Use `remotion-best-practices` while writing Remotion code. Load `remotion-video-toolkit` when the work needs captions, charts, 3D, reusable templates, or an automated rendering pipeline.

For each requested media slot:

1. Read the slot contract, including `asset_path`, dimensions, duration, visual intent, and loop behavior.
2. Create or reuse a Remotion project outside the installed Skill directories.
3. Implement deterministic frame-driven animation and keep all assets at stable local paths.
4. Render a real MP4 to the exact requested `asset_path`; do not substitute a prompt, storyboard, placeholder, GIF, or HTML preview.
5. Verify that the MP4 exists, is non-empty, has the intended duration and dimensions, and can be decoded.
6. Report the output path and verification result.
