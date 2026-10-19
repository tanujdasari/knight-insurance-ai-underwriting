"""Presentation-only styling for the Knight Insurance underwriting assignment demo."""
import streamlit as st

# Publicly displayed branding reference, loaded remotely; no credentials required.
LOGO_URL = "https://www.thriveim.com/clientuploads/directory/Portfolio_Flourish/knight_insurance/knight-logo.jpg"


def apply_knight_theme() -> None:
    st.markdown('''
<style>
:root {--navy:#062b36;--teal:#0d5964;--lime:#76b942;--cream:#f5f8f7;--ink:#12343e}
.stApp {background:var(--cream);color:var(--ink)}
.block-container {max-width:1280px;padding-top:1rem;padding-bottom:4rem}
header[data-testid="stHeader"] {background:transparent}
.k-nav {display:flex;align-items:center;justify-content:space-between;gap:20px;background:#fff;border:1px solid #e0eae8;border-radius:13px;padding:12px 24px;margin:0 0 15px;box-shadow:0 5px 20px #062b3609}
.k-brand {display:flex;align-items:center;gap:14px;min-width:0}
.k-brand img {height:47px;width:auto;max-width:210px;object-fit:contain}
.k-brand-name {font-size:1.05rem;color:#0d5964;font-weight:800;letter-spacing:.02em}
.k-nav-links {color:#58757b;font-size:.82rem;letter-spacing:.03em;text-align:right}
.k-nav-links strong {color:#0d5964}
.k-hero {display:grid;grid-template-columns:minmax(0,1.1fr) minmax(250px,.9fr);align-items:center;gap:16px;background:linear-gradient(115deg,#062b36 0%,#0b5561 72%,#0f756e 100%);color:white;border-radius:16px;overflow:hidden;padding:33px 35px 26px;margin-bottom:17px;box-shadow:0 12px 30px #062b3626}
.k-eyebrow {color:#b5e28b;letter-spacing:.16em;font-weight:800;font-size:.73rem;text-transform:uppercase;margin-bottom:13px}
.k-hero h1 {color:#fff!important;font-size:clamp(1.8rem,3.2vw,2.9rem);line-height:1.12;margin:0 0 16px;font-weight:800}
.k-hero p {color:#dcecef;font-size:1.02rem;line-height:1.65;max-width:620px;margin:0 0 17px}
.k-pill {display:inline-block;border:1px solid #8db3b5;border-radius:99px;padding:7px 13px;color:#e5f4f0;font-size:.75rem;font-weight:700;letter-spacing:.05em}
.k-art svg {width:100%;max-height:275px;display:block}
.k-value-strip {display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin:0 0 20px}
.k-value {background:#fff;border:1px solid #dfebe8;border-left:4px solid var(--lime);padding:14px 17px;border-radius:9px}
.k-value b {display:block;color:#0a3d48;font-size:.92rem;margin-bottom:3px}
.k-value span {color:#57717a;font-size:.8rem}
.k-section-note {color:#627980;font-size:.87rem;margin-top:-5px;margin-bottom:12px}
.k-footer {padding:18px 5px 0;margin-top:25px;border-top:1px solid #dce7e6;color:#607a80;font-size:.8rem;text-align:center}
[data-testid="stMetric"] {background:white;border:1px solid #dce7e5;border-radius:12px;padding:15px;box-shadow:0 2px 8px #062b3609}
[data-testid="stMetricValue"] {color:#0a4d57}
[data-testid="stExpander"] {background:#fff;border:1px solid #e0eae9;border-radius:11px;overflow:hidden}
[data-testid="stFileUploader"] {background:white;border-radius:12px}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] {background:#0c5964!important;border-color:#0c5964!important;color:#fff!important;border-radius:9px!important;font-weight:750!important}
.stButton button[kind="primary"]:hover {background:#07414b!important}
.stButton button:not([kind="primary"]),.stDownloadButton button {border-radius:9px!important}
h2,h3 {color:#0b4650!important;letter-spacing:-.02em}
hr {border-color:#d9e8e5!important}
@media(max-width:780px){.k-hero{grid-template-columns:1fr;padding:24px}.k-art{display:none}.k-value-strip{grid-template-columns:1fr}.k-nav-links{display:none}.k-nav{padding:12px}}

/* Readability and complete form outlines */
[data-testid="stAppViewContainer"] {background:#f5f8f7;color:#12343e}
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] [data-testid="stCaptionContainer"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > p {
  color:#234c55 !important;
}
[data-testid="stMain"] .k-hero .k-eyebrow {color:#d8f5bb!important}
[data-testid="stMain"] .k-hero h1 {color:#fff!important}
[data-testid="stMain"] .k-hero p {color:#e9f6f6!important}
[data-testid="stMain"] .k-hero .k-pill {color:#fff!important}
[data-testid="stMain"] .k-value b {color:#0a3d48!important}
[data-testid="stMain"] .k-value span {color:#496a71!important}
[data-testid="stMain"] .k-footer {color:#496a71!important}
[data-testid="stMain"] [data-testid="stTextArea"] > div,
[data-testid="stMain"] [data-testid="stTextInput"] > div {
  width:100%; min-width:0; box-sizing:border-box;
}
[data-testid="stMain"] [data-testid="stTextArea"] [data-baseweb="textarea"],
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"] {
  box-sizing:border-box!important;
  width:100%!important;
  border:1.5px solid #829da3!important;
  border-radius:10px!important;
  background:#fff!important;
  overflow:hidden!important;
  box-shadow:none!important;
}
[data-testid="stMain"] textarea,
[data-testid="stMain"] input {
  box-sizing:border-box!important;
  color:#173943!important;
  background:#fff!important;
  -webkit-text-fill-color:#173943!important;
}
[data-testid="stMain"] textarea {
  width:100%!important;
  min-width:0!important;
  display:block!important;
  border-radius:10px!important;
  resize:vertical;
}
[data-testid="stMain"] textarea:disabled {
  color:#344f56!important;
  -webkit-text-fill-color:#344f56!important;
  background:#eef3f2!important;
  opacity:1!important;
}
[data-testid="stMain"] [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
  border-color:#0d5964!important;
  box-shadow:0 0 0 2px #0d596422!important;
}
[data-testid="stMain"] textarea::placeholder,
[data-testid="stMain"] input::placeholder {
  color:#627a81!important;
  -webkit-text-fill-color:#627a81!important;
}
[data-testid="stMain"] [data-testid="stAlert"] p {color:inherit!important}
[data-testid="stMain"] [data-testid="stBaseButton-primary"],
[data-testid="stMain"] button[kind="primary"] {background:#0c5964!important;color:#fff!important}
[data-testid="stMain"] [data-testid="stBaseButton-primary"] p,
[data-testid="stMain"] button[kind="primary"] p {color:#fff!important}
[data-testid="stMain"] [data-testid="stBaseButton-secondary"] {
  background:#fff!important;color:#0a4b55!important;border:1px solid #8da8ac!important
}
[data-testid="stMain"] [data-testid="stBaseButton-secondary"] p {color:#0a4b55!important}


/* Review-summary inline numbers are Streamlit Markdown inline-code elements.
   Give them a high-contrast light background and dark text. */
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p strong,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p b {
  color:#12343e!important;
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p code,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li code {
  display:inline-block!important;
  background-color:#e6f1ee!important;
  color:#103d46!important;
  -webkit-text-fill-color:#103d46!important;
  border:1px solid #b9d0cd!important;
  border-radius:5px!important;
  padding:1px 7px!important;
  font-weight:800!important;
  opacity:1!important;
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p code *,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li code * {
  color:#103d46!important;
  -webkit-text-fill-color:#103d46!important;
}


/* Streamlit success/info/warning/error notices: guaranteed contrast.
   These selectors intentionally cover both older and newer Streamlit markup. */
[data-testid="stMain"] [data-testid="stAlert"],
[data-testid="stMain"] [data-testid="stNotification"],
[data-testid="stMain"] [data-baseweb="notification"] {
  background-color:#ffffff !important;
  color:#143b45 !important;
  -webkit-text-fill-color:#143b45 !important;
  border:1px solid #9db8b8 !important;
  border-left:5px solid #0d5964 !important;
  border-radius:9px !important;
  opacity:1 !important;
}
[data-testid="stMain"] [data-testid="stAlert"] *,
[data-testid="stMain"] [data-testid="stNotification"] *,
[data-testid="stMain"] [data-baseweb="notification"] * {
  color:#143b45 !important;
  -webkit-text-fill-color:#143b45 !important;
  opacity:1 !important;
}
/* Some versions render alert content in a separate wrapper. */
[data-testid="stMain"] [data-testid="stAlertContent"],
[data-testid="stMain"] [data-testid="stAlertContent"] p,
[data-testid="stMain"] [data-testid="stAlertContent"] span {
  color:#143b45 !important;
  -webkit-text-fill-color:#143b45 !important;
}
/* Button text for human override action */
[data-testid="stMain"] button[kind="secondary"] p,
[data-testid="stMain"] [data-testid="stBaseButton-secondary"] p {
  color:#0a4b55 !important;
  -webkit-text-fill-color:#0a4b55 !important;
}


/* Human override submit: force a readable high-contrast button in all Streamlit versions. */
[data-testid="stMain"] [data-testid="stForm"] button,
[data-testid="stMain"] [data-testid="stFormSubmitButton"] button,
[data-testid="stMain"] .stFormSubmitButton button {
  background-color:#0b5964 !important;
  border:2px solid #0b5964 !important;
  color:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
  opacity:1 !important;
}
[data-testid="stMain"] [data-testid="stForm"] button *,
[data-testid="stMain"] [data-testid="stFormSubmitButton"] button *,
[data-testid="stMain"] .stFormSubmitButton button * {
  color:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
  opacity:1 !important;
}
[data-testid="stMain"] [data-testid="stFormSubmitButton"] button:hover,
[data-testid="stMain"] .stFormSubmitButton button:hover {
  background-color:#073e48 !important;
  border-color:#073e48 !important;
}

</style>
''', unsafe_allow_html=True)


def render_knight_header() -> None:
    st.markdown(f'''
<div class="k-nav">
  <div class="k-brand"><img src="{LOGO_URL}" alt="Knight Insurance Group logo" onerror="this.style.display='none'" /><div class="k-brand-name">KNIGHT INSURANCE GROUP</div></div>
  <div class="k-nav-links"><strong>UNDERWRITING OPERATIONS</strong> &nbsp; | &nbsp; Commercial Auto &nbsp; | &nbsp; AI Review</div>
</div>
<div class="k-hero">
 <div>
  <div class="k-eyebrow">Innovation &nbsp; • &nbsp; Efficiency &nbsp; • &nbsp; Stability</div>
  <h1>Commercial Auto<br/>Submission Review</h1>
  <p>Smarter submission intake. Clearer evidence. Confident human decisions. Review insurance documents, identify underwriting exceptions, and prepare broker follow-ups in one workspace.</p>
  <span class="k-pill">AI-ASSISTED WORKFLOW &nbsp;·&nbsp; HUMAN REVIEW REQUIRED</span>
 </div>
 <div class="k-art" aria-label="Illustration of a commercial vehicle and document checks">
 <svg viewBox="0 0 470 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Commercial auto and review documents">
  <defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffffff" stop-opacity=".18"/><stop offset="1" stop-color="#8ac66b" stop-opacity=".09"/></linearGradient></defs>
  <circle cx="255" cy="153" r="141" fill="url(#a)" stroke="#9ac3b7" stroke-opacity=".35"/>
  <circle cx="255" cy="153" r="111" fill="none" stroke="#b1d6ca" stroke-opacity=".26" stroke-dasharray="5 10"/>
  <rect x="108" y="71" width="192" height="164" rx="13" fill="#f9ffff"/>
  <rect x="128" y="93" width="92" height="9" rx="4" fill="#0b5c65"/>
  <rect x="128" y="116" width="139" height="7" rx="3" fill="#b9d5d5"/>
  <rect x="128" y="133" width="121" height="7" rx="3" fill="#b9d5d5"/>
  <rect x="128" y="150" width="128" height="7" rx="3" fill="#b9d5d5"/>
  <circle cx="143" cy="188" r="12" fill="#76b942"/><path d="m137 188 5 5 9-11" fill="none" stroke="white" stroke-width="3" stroke-linecap="round"/>
  <rect x="164" y="183" width="100" height="8" rx="4" fill="#9ac9b0"/>
  <rect x="228" y="170" width="160" height="68" rx="11" fill="#76b942"/>
  <rect x="250" y="181" width="88" height="35" rx="4" fill="#e3f0f0"/>
  <path d="M388 191h22l27 30v17h-49z" fill="#e4f2ec"/>
  <path d="M398 199h10l16 17h-26z" fill="#0d5964"/>
  <circle cx="267" cy="240" r="20" fill="#0a333d" stroke="#d6eee6" stroke-width="6"/>
  <circle cx="398" cy="240" r="20" fill="#0a333d" stroke="#d6eee6" stroke-width="6"/>
  <path d="M197 264h238" stroke="#b7d2c8" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>
  <circle cx="359" cy="83" r="31" fill="#76b942"/><path d="m345 84 10 10 19-24" fill="none" stroke="white" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
 </svg>
 </div>
</div>
<div class="k-value-strip">
 <div class="k-value"><b>Evidence-first extraction</b><span>Trace values to their original documents.</span></div>
 <div class="k-value"><b>Transparent rule evaluation</b><span>Review five deterministic underwriting checks.</span></div>
 <div class="k-value"><b>Underwriter in control</b><span>Correct, audit, and draft without auto-sending.</span></div>
</div>
''', unsafe_allow_html=True)


def render_knight_footer() -> None:
    st.markdown('''<div class="k-footer">Knight Insurance Group-inspired visual design · Human underwriting review required</div>''', unsafe_allow_html=True)
