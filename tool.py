import streamlit as st
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

#imports of io and reportlab are necessary for pdf creation
#import json to import the controls file

#PQuick- nome per ora


#this is the global page configuration 
st.set_page_config(page_title="PQUICK", page_icon="☃︎", layout="wide")
#title
st.title("PQuick")
st.write("This tool was developed to offer guidance for the post-quantum transition for italian organisations")

#this is to inject css into streamlit: better design of buttons. injection through unsafeallow
st.markdown("""
<style>
.stAlert, .stDownloadButton button {
  border-radius: 14px;
}

div[role="radiogroup"] label {
  border-radius: 999px;
  padding: 0.35rem 0.8rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.block-container { padding-top: 2.2rem; }

hr { margin: 0.6rem 0 1.0rem 0; opacity: 0.25; }

[data-testid="stDataFrame"] * { font-size: 0.92rem; }
</style>
""", unsafe_allow_html=True)


#the following part allows to load all the controls contained in the json, uploads as python dictionary
#the expected output is a phase-answer option structure, security control for error (the json might be structured wrongly)
def controlli_caricati():
    with open("controlli_tutti.json", "r", encoding="utf-8") as f:
        return json.load(f)

data = controlli_caricati()
phases = data.get("phases", [])
if not phases:
    st.error("No phases found in controlli_tutti.json")
    st.stop()
answer_options = data.get("answer_options", ["yes", "partial", "no", "na"])
if "responses" not in st.session_state:
    st.session_state.responses = {}

#mantiene dati nella sessione con stsessionstate
    

# to ensure the field is treated as a list from the json
def ensure_list(x):
    """Se per sbaglio un campo fosse stringa invece che lista, lo rende lista."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

#this is to get the recommendation associated to each of the answer of the questionnaire
def get_recommendation(control, answer):
    actions = control.get("actions", {})
    return actions.get(answer, "")
#makes everything a list
def flatten_controls(phases):
    rows = []
    for ph in phases:
        phase_name = ph.get("name", "")
        phase_id = ph.get("id", phase_name)
        for c in ph.get("controls", []):
            rows.append({
                "phase_id": phase_id,
                "phase_name": phase_name,
                "control": c
            })
    return rows

# this section contains the scoring logic of the tool
def compute_scores(phases, responses):
    all_controls = flatten_controls(phases)
#here it takes the sum of point for each phase, then considers the non applicable response as null, then it makes a line for each
    phase_sum = {}
    phase_app = {}
    summary_rows = []
#lo scoring è fatto che viene in percentuale, dalla media ponderata. per controllo implementato è 2, per parizale è 1 e per nullo o sconosciuto è 0. 
#poi si calcola il punteggio massimo per la fase e poi lo score percentuale dalla media ponderata
    for item in all_controls:
        phase_name = item["phase_name"]
        c = item["control"]
        cid = c.get("id", "UNKNOWN")

        answer = responses.get(cid, "no")
        score_value = {"yes": 2, "partial": 1, "no": 0, "na": 0}.get(answer, 0)

        if phase_name not in phase_sum:
            phase_sum[phase_name] = 0
            phase_app[phase_name] = 0

        phase_sum[phase_name] += score_value
        if answer != "na":
            phase_app[phase_name] += 1

        rec = get_recommendation(c, answer)

        summary_rows.append({
            "id": cid,
            "phase": phase_name,
            "answer": answer,
            "score": score_value,
            "recommendation": rec
        })
#qui c'è scoring delle fasi e totale
    phase_scores_pct = {}
    for ph_name in phase_sum:
        denom = 2 * phase_app[ph_name]
        phase_scores_pct[ph_name] = 0 if denom == 0 else (phase_sum[ph_name] / denom) * 100

    total_sum = sum(phase_sum.values())
    total_app = sum(phase_app.values())
    total_denom = 2 * total_app
    total_score_pct = 0 if total_denom == 0 else (total_sum / total_denom) * 100

    return phase_scores_pct, total_score_pct, summary_rows

#questo generale in pdf con: score, score per phaase, recommendations and appendix with the controls
def build_pdf(
    phase_scores_pct,
    total_score_pct,
    summary_rows,
    tool_name="PQuick"
):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x_margin = 2 * cm
    y = height - 2 * cm
#boh questo serviva per dividere in automatico le pagine
    def line(text, dy=14):
        nonlocal y
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
        c.drawString(x_margin, y, text)
        y -= dy

    # title
    c.setFont("Helvetica-Bold", 18)
    line(f"{tool_name} – Post-Quantum Readiness Report", 24)

    c.setFont("Helvetica", 10)
    line(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 20)

    # score total
    c.setFont("Helvetica-Bold", 14)
    line("Overall score", 20)

    c.setFont("Helvetica", 12)
    line(f"Total score: {total_score_pct:.1f} %", 18)

    # score by phase
    c.setFont("Helvetica-Bold", 14)
    line("Score by phase", 20)

    c.setFont("Helvetica", 11)
    for phase, score in phase_scores_pct.items():
        line(f"- {phase}: {score:.1f} %", 14)

    # priority recommendations go here
    c.setFont("Helvetica-Bold", 14)
    line("Priority recommendations", 20)

    priority = [r for r in summary_rows if r["answer"] in ("no", "partial")]
    priority.sort(key=lambda r: 0 if r["answer"] == "no" else 1)

    if not priority:
        c.setFont("Helvetica", 11)
        line("No priority recommendations identified.", 14)
    else:
        c.setFont("Helvetica", 11)
        for r in priority:
            tag = "NO" if r["answer"] == "no" else "PARTIAL"
            line(f"[{tag}] {r['id']} ({r['phase']}):", 14)
            line(f"  {r['recommendation']}", 14)

    # optional appendix
    c.showPage()
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    line("Appendix – All controls", 20)

    c.setFont("Helvetica", 10)
    for r in summary_rows:
        line(f"{r['id']} ({r['phase']}) – {r['answer'].upper()} – score {r['score']}", 12)

    c.save()
    buffer.seek(0)
    return buffer

# here the boring UI part
tabs = st.tabs(["Assessment", "Overview & Export"])  

with tabs[0]:

    phase_names = [p["name"] for p in phases]

# default: prima fase se non c'è nulla salvato
    default_name = st.session_state.get("selected_phase_name", phase_names[0])
    default_index = phase_names.index(default_name) if default_name in phase_names else 0

    selected_name = st.selectbox(
        "Phase",
        phase_names,
        index=default_index,
        key="selected_phase_name"
    )

    selected_phase = next(p for p in phases if p["name"] == selected_name)


    st.subheader(f"{selected_phase['name']}")
    st.caption(selected_phase.get("description", ""))

    controls = selected_phase.get("controls", [])

    # Rendering controlli
    for control in controls:
        control_id = control.get("id", "UNKNOWN")

        question = control.get("question", "")
        

        st.markdown("---")
        st.markdown(f"### {control_id}")
        st.write(question)

        # Meta info
        owners = ensure_list(control.get("owner"))
        refs = ensure_list(control.get("reference"))
        horizon = control.get("horizon", "")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Owner**")
            st.write(", ".join(owners) if owners else "-")
        with col2:
            st.markdown("**Horizon**")
            st.write(horizon if horizon else "-")
        with col3:
            st.markdown("**Reference**")
            st.write(", ".join(refs) if refs else "-")

        # Evidence che si espande se ci clicchi
        evidence = ensure_list(control.get("evidence"))
        with st.expander("Evidence required"):
            if evidence:
                for e in evidence:
                    st.write(f"• {e}")
            else:
                st.write("-")

        # Answer radio (salvata in session_state.responses)
        radio_key = f"answer_{control_id}"
        placeholder = "— Select —"
        ui_options = [placeholder] + answer_options

        # valore precedente (se esiste), altrimenti placeholder
        saved = st.session_state.responses.get(control_id)
        default_ui = saved if saved in answer_options else placeholder
        default_index = ui_options.index(default_ui)

        answer_ui = st.radio(
            "Answer",
            options=ui_options,
            index=default_index,
            key=radio_key,
            horizontal=True,
        )

        # salva SOLO se l'utente ha scelto una risposta vera
        if answer_ui != placeholder:
            st.session_state.responses[control_id] = answer_ui
        else:
            # se torna su placeholder, rimuovi la risposta salvata
            st.session_state.responses.pop(control_id, None)

        answer = st.session_state.responses.get(control_id)

        if answer is None:
            st.info("No answer selected yet.")
        else:
            rec = get_recommendation(control, answer)
            if rec:
                st.info(f"**Recommendation ({answer})**: {rec}")
            else:
                st.warning("No recommendation found for this answer (check actions in JSON).")
with tabs[1]:
    st.subheader("Dashboard")

    phase_scores_pct, total_score_pct, summary_rows = compute_scores(phases, st.session_state.responses)
    section = st.selectbox(
        "What do you want to see?",
        [
            "Overview",
            "Priority recommendations",
            "Controls summary",
            "Export"
        ]
    )
    df_controls = pd.DataFrame(summary_rows)[["id", "phase", "answer", "score", "recommendation"]]
    if section == "Overview":
        st.metric("Total score (%)", f"{total_score_pct:.1f}")

        st.markdown("### Score by phase")
        df_phase = pd.DataFrame([
            {"phase": ph, "score_pct": round(score, 1)}
            for ph, score in phase_scores_pct.items()
        ]).sort_values("phase")

        st.dataframe(
            df_phase,
            hide_index=True,
            height=220,
            width="stretch"
        )
    # KPI in alto

    # Tabella score per fase
    #st.markdown("### Score by phase")
    #df_phase = pd.DataFrame([
        #{"phase": ph, "score_pct": round(score, 1)}
      #  for ph, score in phase_scores_pct.items()
    #]).sort_values("phase")

    #st.dataframe(
    #df_phase,
# hide_index=True,
  #  height=220,
   # width="stretch"
#)

    # Tabella riepilogo controlli
    elif section == "Controls summary":
        st.markdown("### Controls summary")
        df_controls = pd.DataFrame(summary_rows)

        # ordine colonne più leggibile
        df_controls = df_controls[["id", "phase", "answer", "score", "recommendation"]]

        st.dataframe(
            df_controls,
            hide_index=True,
            height=420,
            width="stretch"
        )
    elif section == "Export":
        st.markdown("### Export")

        csv_bytes = df_controls.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="⬇ Download CSV (controls summary)",
            data=csv_bytes,
            file_name="pquick_controls_summary.csv",
            mime="text/csv",
        )
    
    #qui la parte relativa all'export, in vari formati cosi se è un informatico prende json e se è compliance prende pdf
    # A) JSON semplice: solo risposte
        responses_json_str = json.dumps(st.session_state.responses, indent=2, ensure_ascii=False)

        st.download_button(
            label="⬇ Download JSON (responses only)",
            data=responses_json_str.encode("utf-8"),
            file_name="pquick_responses.json",
            mime="application/json",
        )

    # B) JSON ricco: include summary_rows + score totale/per fase
        export_payload = {
            "tool": data.get("tool", "PQuick"),
            "schema_version": data.get("schema_version", "unknown"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_score_pct": round(float(total_score_pct), 2),
            "phase_scores_pct": {k: round(float(v), 2) for k, v in phase_scores_pct.items()},
            "responses": st.session_state.responses,
            "controls_summary": summary_rows,
        }
        export_json_str = json.dumps(export_payload, indent=2, ensure_ascii=False)

        st.download_button(
            label="⬇ Download JSON (full export)",
            data=export_json_str.encode("utf-8"),
            file_name="pquick_full_export.json",
            mime="application/json",
        )

        st.markdown("### PDF Report")

        pdf_buffer = build_pdf(
            phase_scores_pct=phase_scores_pct,
            total_score_pct=total_score_pct,
            summary_rows=summary_rows,
            tool_name=data.get("tool", "PQuick")
        )

        st.download_button(
            label="⬇ Download PDF report",
            data=pdf_buffer,
            file_name="pquick_report.pdf",
            mime="application/pdf",
        )
    # Raccomandazioni prioritarie (no prima, poi partial)
    elif section == "Priority recommendations":
        st.markdown("### Priority recommendations (NO first, then PARTIAL)")

        priority = [r for r in summary_rows if r["answer"] in ("no", "partial")]
        # ordina: no prima di partial
        priority.sort(key=lambda r: 0 if r["answer"] == "no" else 1)

        if not priority:
            st.success("No priority recommendations (no NO/PARTIAL found).")
        else:
        # raggruppo per fase
            by_phase = {}
            for r in priority:
                ph = r["phase"]
                by_phase.setdefault(ph, []).append(r)

        # stampo fase per fase
        for ph, items in by_phase.items():
            st.markdown(f"### {ph}")

            for r in items:
                if r["answer"] == "no":
                    st.error(f"**{r['id']}** — {r['recommendation']}")
                else:
                    st.warning(f"**{r['id']}** — {r['recommendation']}")
