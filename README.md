# KF-CareLog

> 介護記録をテンプレートで効率化し、PDFで出力するアプリ。

## The Problem

Care workers spend up to 40% of their shift on documentation — handwriting records, transcribing data, and organizing paperwork. This app streamlines the process with structured templates.

## How It Works

1. Select a record template (Vitals, Meal, Excretion, Activity)
2. Fill in the form with resident data
3. Generate and download a standardized PDF record sheet

## Libraries Used

- **fpdf2** — PDF generation with Unicode/Japanese font support
- **Jinja2** — Template engine (reserved for future template customization)

## Development

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Hosted on [Hugging Face Spaces](https://huggingface.co/spaces/mitoi/kf-care-log).

---

Part of the [KaleidoFuture AI-Driven Development Research](https://kaleidofuture.com) — proving that everyday problems can be solved with existing libraries, no AI model required.
