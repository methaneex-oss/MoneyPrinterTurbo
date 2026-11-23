# Solo Stack — official product visuals and episode timeline

## What changed

The production pipeline can now identify supported software products explicitly
named in the episode subject, narration or generated material terms. It captures
public product imagery from official vendor pages and turns those genuine source
images into short branded clips that can be inserted into the episode timeline.

Supported official sources currently include:

- ChatGPT — https://chatgpt.com/overview/
- Claude — https://claude.com/product/overview
- Notion — https://www.notion.com/product/features
- Canva — https://www.canva.com/
- Grammarly — https://www.grammarly.com/features
- Zapier — https://zapier.com/press
- Perplexity — https://www.perplexity.ai/
- Cursor — https://www.cursor.com/features
- ClickUp — https://clickup.com/features/ai
- Figma — https://www.figma.com/product/
- Gemini — https://gemini.google.com/
- Google Workspace — https://workspace.google.com/
- Microsoft 365 — https://www.microsoft.com/microsoft-365
- Asana — https://asana.com/product/ai
- Trello — https://trello.com/
- Airtable — https://www.airtable.com/platform
- Slack — https://slack.com/features/ai
- Make — https://www.make.com/en
- n8n — https://n8n.io/
- Loom — https://www.loom.com/
- Descript — https://www.descript.com/
- Calendly — https://calendly.com/features
- HubSpot — https://www.hubspot.com/products/ai
- GitHub Copilot — https://github.com/features/copilot

The product catalogue is deliberately allowlisted. It does not search arbitrary
image sites, download random screenshots, or generate fake application UIs.
Images are taken from the official page's own image elements where possible;
a page screenshot is used only when no suitable image can be extracted.

## Important distinction

These are authentic public product-page visuals, not recordings of an authenticated
customer account or proof that a particular workflow succeeded. The clips are
labelled as official product visuals and carry the source page, source image URL,
capture time and SHA-256 digest in the episode manifest. For a real task
demonstration inside an account-specific workspace, the recording must come from
that actual session; this system does not bypass login, paywalls or access controls.

Product screenshots, logos and page imagery remain subject to each vendor's
terms and applicable copyright law. Public accessibility alone does not grant
unrestricted commercial reuse. Review the relevant usage terms before publishing.

## Colab setup

The notebook installs Playwright and Chromium in the isolated MoneyPrinterTurbo
environment. No paid API is used. On each Solo Stack video task, only products
named by the episode are considered, up to the configured product limit. Capture
failures are non-fatal: existing stock/local media remains available.

The official product visuals are inserted in narration order, and Solo Stack
uses sequential composition to avoid random selection dropping the evidence clips.

## Verification

Unit tests cover product identification, allowlisted official sources and
branded card rendering. These tests do not prove vendor websites remain unchanged
or that every official page permits automated capture. Live Colab browser capture,
the resulting video, visual readability and commercial asset clearance still
require real-runtime review.
