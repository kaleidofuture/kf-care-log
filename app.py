"""KF-CareLog — 介護記録をテンプレートで効率化し、PDFで出力するアプリ。"""

import streamlit as st

st.set_page_config(
    page_title="KF-CareLog",
    page_icon="🏥",
    layout="centered",
)

from components.header import render_header
from components.footer import render_footer
from components.i18n import t

from datetime import datetime, date, time
from io import BytesIO
from fpdf import FPDF

# --- Header ---
render_header()

# --- Template definitions ---
TEMPLATES = {
    "vital": {
        "fields": [
            {"key": "user_name", "type": "text"},
            {"key": "recorder_name", "type": "text"},
            {"key": "record_date", "type": "date"},
            {"key": "record_time", "type": "time"},
            {"key": "body_temp", "type": "number", "min": 34.0, "max": 42.0, "step": 0.1, "default": 36.5},
            {"key": "blood_pressure_sys", "type": "number", "min": 60, "max": 250, "step": 1, "default": 120},
            {"key": "blood_pressure_dia", "type": "number", "min": 30, "max": 150, "step": 1, "default": 80},
            {"key": "pulse", "type": "number", "min": 30, "max": 200, "step": 1, "default": 72},
            {"key": "spo2", "type": "number", "min": 70, "max": 100, "step": 1, "default": 98},
            {"key": "notes", "type": "textarea"},
        ],
    },
    "meal": {
        "fields": [
            {"key": "user_name", "type": "text"},
            {"key": "recorder_name", "type": "text"},
            {"key": "record_date", "type": "date"},
            {"key": "meal_type", "type": "select", "options_key": "meal_type_options"},
            {"key": "main_dish_intake", "type": "select", "options_key": "intake_options"},
            {"key": "side_dish_intake", "type": "select", "options_key": "intake_options"},
            {"key": "soup_intake", "type": "select", "options_key": "intake_options"},
            {"key": "rice_intake", "type": "select", "options_key": "intake_options"},
            {"key": "water_ml", "type": "number", "min": 0, "max": 2000, "step": 50, "default": 200},
            {"key": "notes", "type": "textarea"},
        ],
    },
    "excretion": {
        "fields": [
            {"key": "user_name", "type": "text"},
            {"key": "recorder_name", "type": "text"},
            {"key": "record_date", "type": "date"},
            {"key": "record_time", "type": "time"},
            {"key": "excretion_type", "type": "select", "options_key": "excretion_type_options"},
            {"key": "amount", "type": "select", "options_key": "amount_options"},
            {"key": "condition", "type": "select", "options_key": "condition_options"},
            {"key": "assistance", "type": "select", "options_key": "assistance_options"},
            {"key": "notes", "type": "textarea"},
        ],
    },
    "activity": {
        "fields": [
            {"key": "user_name", "type": "text"},
            {"key": "recorder_name", "type": "text"},
            {"key": "record_date", "type": "date"},
            {"key": "activity_type", "type": "select", "options_key": "activity_type_options"},
            {"key": "start_time", "type": "time"},
            {"key": "end_time", "type": "time"},
            {"key": "participation", "type": "select", "options_key": "participation_options"},
            {"key": "mood", "type": "select", "options_key": "mood_options"},
            {"key": "notes", "type": "textarea"},
        ],
    },
}


def get_select_options(options_key: str) -> list[str]:
    """Get localized select options."""
    raw = t(options_key)
    if isinstance(raw, list):
        return raw
    return [s.strip() for s in raw.split(",")]


def render_form(template_key: str) -> dict | None:
    """Render form fields for the selected template and return data dict."""
    template = TEMPLATES[template_key]
    data = {}

    with st.form(key=f"form_{template_key}"):
        st.subheader(t(f"template_{template_key}"))

        for field in template["fields"]:
            label = t(f"field_{field['key']}")

            if field["type"] == "text":
                data[field["key"]] = st.text_input(label, key=field["key"])
            elif field["type"] == "textarea":
                data[field["key"]] = st.text_area(label, key=field["key"], height=100)
            elif field["type"] == "number":
                data[field["key"]] = st.number_input(
                    label,
                    min_value=float(field["min"]),
                    max_value=float(field["max"]),
                    value=float(field.get("default", field["min"])),
                    step=float(field["step"]),
                    key=field["key"],
                )
            elif field["type"] == "date":
                data[field["key"]] = st.date_input(label, value=date.today(), key=field["key"])
            elif field["type"] == "time":
                data[field["key"]] = st.time_input(label, value=datetime.now().time(), key=field["key"])
            elif field["type"] == "select":
                options = get_select_options(field["options_key"])
                data[field["key"]] = st.selectbox(label, options, key=field["key"])

        submitted = st.form_submit_button(t("generate_pdf"), type="primary")

    if submitted:
        if not data.get("user_name"):
            st.warning(t("user_name_required"))
            return None
        return data
    return None


def generate_pdf(template_key: str, data: dict) -> bytes:
    """Generate a PDF care record from template and form data."""
    pdf = FPDF()
    pdf.add_page()

    # Add Japanese font
    font_path = None
    import os
    # Try to use bundled font or system font
    local_font = os.path.join(os.path.dirname(__file__), "NotoSansJP-Regular.ttf")
    if os.path.exists(local_font):
        font_path = local_font
    else:
        # Fallback: try common system paths
        candidates = [
            "C:/Windows/Fonts/msgothic.ttc",
            "C:/Windows/Fonts/YuGothR.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Regular.otf",
        ]
        for c in candidates:
            if os.path.exists(c):
                font_path = c
                break

    if font_path:
        pdf.add_font("JP", "", font_path, uni=True)
        pdf.set_font("JP", size=12)
        font_name = "JP"
    else:
        pdf.set_font("Helvetica", size=12)
        font_name = "Helvetica"

    # Title
    title = t(f"template_{template_key}")
    pdf.set_font(font_name, size=18)
    pdf.cell(0, 15, title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Record fields
    pdf.set_font(font_name, size=12)
    template = TEMPLATES[template_key]

    for field in template["fields"]:
        label = t(f"field_{field['key']}")
        value = data.get(field["key"], "")

        if isinstance(value, date):
            value = value.strftime("%Y-%m-%d")
        elif isinstance(value, time):
            value = value.strftime("%H:%M")
        else:
            value = str(value)

        # Label
        pdf.set_font(font_name, size=10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, label, new_x="LMARGIN", new_y="NEXT")

        # Value
        pdf.set_font(font_name, size=12)
        pdf.set_text_color(0, 0, 0)
        if field["type"] == "textarea":
            pdf.multi_cell(0, 7, value if value else "-")
        else:
            pdf.cell(0, 8, value if value else "-", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Footer
    pdf.ln(10)
    pdf.set_font(font_name, size=8)
    pdf.set_text_color(150, 150, 150)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.cell(0, 5, f"{t('generated_at')}: {generated_at}", new_x="LMARGIN", new_y="NEXT", align="R")

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


# --- Main Content ---
st.markdown(f"### {t('select_template')}")

template_options = {
    "vital": t("template_vital"),
    "meal": t("template_meal"),
    "excretion": t("template_excretion"),
    "activity": t("template_activity"),
}

selected = st.selectbox(
    t("template_label"),
    options=list(template_options.keys()),
    format_func=lambda k: template_options[k],
)

st.markdown("---")

form_data = render_form(selected)

if form_data is not None:
    with st.spinner(t("processing")):
        pdf_bytes = generate_pdf(selected, form_data)

    st.success(t("pdf_ready"))

    # Preview data
    with st.expander(t("preview_data")):
        template = TEMPLATES[selected]
        for field in template["fields"]:
            label = t(f"field_{field['key']}")
            value = form_data.get(field["key"], "")
            if isinstance(value, (date, time)):
                value = value.strftime("%Y-%m-%d") if isinstance(value, date) else value.strftime("%H:%M")
            st.text(f"{label}: {value}")

    filename = f"care_record_{selected}_{date.today().strftime('%Y%m%d')}.pdf"
    st.download_button(
        label=t("download_pdf"),
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        type="primary",
    )

# --- Footer ---
render_footer(libraries=["fpdf2", "Jinja2"])
