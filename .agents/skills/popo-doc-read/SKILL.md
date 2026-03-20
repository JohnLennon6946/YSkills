---
name: popo-doc-read
description: Read NetEase Popo documentation pages through the Langbase parse API and return the extracted document text. Use when the user provides a `docs.popo.netease.com` document URL, asks to convert a Popo doc link into a `langbase.netease.com/api/v1/document/parse-popo` URL, or wants the content of a Popo or Lingxi document copied out as plain text.
---

# Popo Doc Read

Convert noisy Popo share links into a normalized `popo_url`, call the Langbase parse endpoint, and return the extracted plain text.

Use the bundled script instead of reconstructing the API URL by hand.

## Workflow

1. Run the script with the Popo URL:

```bash
python3 scripts/read_popo_doc.py '<popo-doc-url>' --show-api-url
```

2. Let the script normalize the URL by:

- accepting a raw `docs.popo.netease.com` link with query parameters or hash fragments
- stripping query parameters and fragment
- preserving only `scheme + host + path`
- building `https://langbase.netease.com/api/v1/document/parse-popo?popo_url=...`

3. Return:

- the normalized Langbase API URL if the user asked for conversion or debugging
- the extracted document text from `data.text_content`

## Behavior

- Prefer the script even if the input already contains many tracking params such as `xyz`, `appVersion`, or `popo_noindicator`.
- Accept a Langbase parse URL too. The script extracts `popo_url`, re-normalizes it, and fetches the document again.
- Return the raw extracted text by default. Summarize only if the user asks for a summary.
- If the API response does not contain text, surface the raw JSON so the user can inspect the failure.

## Script

- Entry point: `scripts/read_popo_doc.py`
- Useful flags:
  - `--show-api-url`: print the normalized Langbase API URL before the content
  - `--json`: print the raw JSON response instead of extracted text
