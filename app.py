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

import json
from datetime import datetime, date, time
from io import BytesIO
from fpdf import FPDF
from streamlit_js_eval import streamlit_js_eval

STORAGE_KEY = "kf-care-log-records"

# --- Header ---
render_header()

# --- Initialize session state ---
if "daily_records" not in st.session_state:
    st.session_state["daily_records"] = []
if "last_user_name" not in st.session_state:
    st.session_state["last_user_name"] = ""
if "last_recorder_name" not in st.session_state:
    st.session_state["last_recorder_name"] = ""

# --- Load from localStorage ---
if "data_loaded" not in st.session_state:
    stored = streamlit_js_eval(js_expressions=f'localStorage.getItem("{STORAGE_KEY}")')
    if stored and stored != "null":
        try:
            st.session_state["daily_records"] = json.loads(stored)
        except Exception:
            pass
    st.session_state["data_loaded"] = True


def _serialize_records(records):
    """Convert date/time objects to strings for JSON serialization."""
    serialized = []
    for rec in records:
        new_rec = dict(rec)
        if "data" in new_rec:
            new_data = {}
            for k, v in new_rec["data"].items():
                if isinstance(v, date) and not isinstance(v, datetime):
                    new_data[k] = v.strftime("%Y-%m-%d")
                elif isinstance(v, time):
                    new_data[k] = v.strftime("%H:%M")
                elif isinstance(v, datetime):
                    new_data[k] = v.strftime("%Y-%m-%d %H:%M")
                else:
                    new_data[k] = v
            new_rec["data"] = new_data
        serialized.append(new_rec)
    return serialized


def save_to_local_storage():
    """Save daily_records to browser localStorage."""
    serializable = _serialize_records(st.session_state["daily_records"])
    data_json = json.dumps(serializable, ensure_ascii=False)
    streamlit_js_eval(js_expressions=f'localStorage.setItem("{STORAGE_KEY}", {json.dumps(data_json)})')

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


def check_vital_alerts(data: dict) -> list[str]:
    """Check vital signs for abnormal values. Returns list of warning messages."""
    alerts = []
    temp = data.get("body_temp")
    if temp is not None and temp >= 38.0:
        alerts.append(t("alert_high_temp").format(value=temp))

    sys = data.get("blood_pressure_sys")
    if sys is not None and sys >= 180:
        alerts.append(t("alert_high_bp_sys").format(value=int(sys)))

    dia = data.get("blood_pressure_dia")
    if dia is not None and dia >= 110:
        alerts.append(t("alert_high_bp_dia").format(value=int(dia)))

    spo2 = data.get("spo2")
    if spo2 is not None and spo2 <= 93:
        alerts.append(t("alert_low_spo2").format(value=int(spo2)))

    pulse = data.get("pulse")
    if pulse is not None:
        if pulse >= 120:
            alerts.append(t("alert_high_pulse").format(value=int(pulse)))
        elif pulse <= 40:
            alerts.append(t("alert_low_pulse").format(value=int(pulse)))

    return alerts


def render_form(template_key: str) -> dict | None:
    """Render form fields for the selected template and return data dict."""
    template = TEMPLATES[template_key]
    data = {}

    # Quick preset button (outside form, for vital template)
    if template_key == "vital":
        st.caption(t("quick_preset_help"))
        if st.button(t("quick_preset_standard"), key="preset_standard"):
            st.session_state["preset_body_temp"] = 36.5
            st.session_state["preset_bp_sys"] = 120.0
            st.session_state["preset_bp_dia"] = 80.0
            st.session_state["preset_pulse"] = 72.0
            st.session_state["preset_spo2"] = 98.0
            st.rerun()

    with st.form(key=f"form_{template_key}"):
        st.subheader(t(f"template_{template_key}"))

        for field in template["fields"]:
            label = t(f"field_{field['key']}")

            if field["type"] == "text":
                # Pre-fill user_name and recorder_name from session
                default_val = ""
                if field["key"] == "user_name":
                    default_val = st.session_state.get("last_user_name", "")
                elif field["key"] == "recorder_name":
                    default_val = st.session_state.get("last_recorder_name", "")
                data[field["key"]] = st.text_input(label, value=default_val, key=field["key"])
            elif field["type"] == "textarea":
                data[field["key"]] = st.text_area(label, key=field["key"], height=100)
            elif field["type"] == "number":
                # Check for preset values
                preset_key_map = {
                    "body_temp": "preset_body_temp",
                    "blood_pressure_sys": "preset_bp_sys",
                    "blood_pressure_dia": "preset_bp_dia",
                    "pulse": "preset_pulse",
                    "spo2": "preset_spo2",
                }
                preset_key = preset_key_map.get(field["key"])
                default_val = float(field.get("default", field["min"]))
                if preset_key and preset_key in st.session_state:
                    default_val = float(st.session_state[preset_key])

                data[field["key"]] = st.number_input(
                    label,
                    min_value=float(field["min"]),
                    max_value=float(field["max"]),
                    value=default_val,
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

        # Remember names for next form
        st.session_state["last_user_name"] = data.get("user_name", "")
        st.session_state["last_recorder_name"] = data.get("recorder_name", "")

        # Clear preset values after use
        for pk in ["preset_body_temp", "preset_bp_sys", "preset_bp_dia", "preset_pulse", "preset_spo2"]:
            st.session_state.pop(pk, None)

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


def generate_daily_summary_pdf(records: list[dict]) -> bytes:
    """Generate a PDF summarizing all records of the day."""
    pdf = FPDF()
    pdf.add_page()

    import os
    font_path = None
    local_font = os.path.join(os.path.dirname(__file__), "NotoSansJP-Regular.ttf")
    if os.path.exists(local_font):
        font_path = local_font
    else:
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
        font_name = "JP"
    else:
        font_name = "Helvetica"

    # Title
    pdf.set_font(font_name, size=18)
    today_str = date.today().strftime("%Y-%m-%d")
    pdf.cell(0, 15, f"{t('daily_summary_title')} ({today_str})", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    for idx, record in enumerate(records, 1):
        template_key = record["template_key"]
        data = record["data"]
        template = TEMPLATES[template_key]

        # Record header
        pdf.set_font(font_name, size=14)
        pdf.set_text_color(0, 0, 150)
        pdf.cell(0, 10, f"#{idx} {t(f'template_{template_key}')}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        # Fields
        for field in template["fields"]:
            label = t(f"field_{field['key']}")
            value = data.get(field["key"], "")
            if isinstance(value, date):
                value = value.strftime("%Y-%m-%d")
            elif isinstance(value, time):
                value = value.strftime("%H:%M")
            else:
                value = str(value)

            pdf.set_font(font_name, size=9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(50, 6, label, new_x="RIGHT", new_y="TOP")
            pdf.set_font(font_name, size=10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, value if value else "-", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)

        # Check if we need a new page
        if pdf.get_y() > 250 and idx < len(records):
            pdf.add_page()

    # Footer
    pdf.ln(10)
    pdf.set_font(font_name, size=8)
    pdf.set_text_color(150, 150, 150)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.cell(0, 5, f"{t('generated_at')}: {generated_at}  |  {t('daily_summary_count').format(count=len(records))}",
             new_x="LMARGIN", new_y="NEXT", align="R")

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
    # Check for vital alerts
    if selected == "vital":
        alerts = check_vital_alerts(form_data)
        for alert in alerts:
            st.warning(f"⚠️ {alert}")

    with st.spinner(t("processing")):
        pdf_bytes = generate_pdf(selected, form_data)

    st.success(t("pdf_ready"))

    # Store record in daily records
    st.session_state["daily_records"].append({
        "template_key": selected,
        "data": form_data,
        "timestamp": datetime.now().strftime("%H:%M"),
    })
    save_to_local_storage()

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

# --- Daily Summary Section ---
st.markdown("---")
daily_records = st.session_state.get("daily_records", [])
if daily_records:
    st.markdown(f"### {t('daily_summary_section')}")
    st.info(t("daily_summary_info").format(count=len(daily_records)))

    with st.expander(t("daily_summary_preview")):
        for idx, rec in enumerate(daily_records, 1):
            tkey = rec["template_key"]
            ts = rec["timestamp"]
            uname = rec["data"].get("user_name", "-")
            st.caption(f"#{idx} [{ts}] {t(f'template_{tkey}')} - {uname}")

    if st.button(t("generate_daily_pdf"), type="secondary"):
        with st.spinner(t("processing")):
            summary_pdf = generate_daily_summary_pdf(daily_records)
        st.download_button(
            label=t("download_daily_pdf"),
            data=summary_pdf,
            file_name=f"daily_summary_{date.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            key="download_daily_summary",
        )

# --- Footer ---
render_footer(libraries=["fpdf2", "Jinja2"], repo_name="kf-care-log")
