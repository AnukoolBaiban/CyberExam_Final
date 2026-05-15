# ============================================================
#  KMUTT Crypto Forensic Console  —  app.py
#  Blue Team CTF / Incident-Response Lab
#  Dependencies: streamlit, pycryptodome, pandas
#  Run: streamlit run app.py
# ============================================================

import base64
import hashlib
import random
import threading
import time
import datetime
import uuid
import streamlit as st
import pandas as pd
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ─────────────────────────────────────────────
#  CHALLENGE CONSTANTS
# ─────────────────────────────────────────────
SECRET_KEY_STR = "KMUTT_SECRET_KEY_AES256_CBC_2026"   # exactly 32 bytes
SECRET_IV_STR  = "KMUTT_IV_16bytes"                    # exactly 16 bytes

CORRECT_KEY_HEX = SECRET_KEY_STR.encode().hex()        # 64 hex chars
CORRECT_IV_HEX  = SECRET_IV_STR.encode().hex()         # 32 hex chars

PLAINTEXT = (
    "OPERATION SHADOWSTRIKE - PHASE 2 INITIATED\n"
    "Target: KMUTT Enterprise SCADA Node - 192.168.50.100\n"
    "Exfiltration complete. AES tunnel established.\n"
    "Awaiting C2 beacon on TCP/4444.\n"
    "Operator authentication token: XK9-DELTA-7734\n"
    "\n"
    "RECOVERY FLAG: KMUTT_CTF{435_cb_k3y_r3c0v3r3d_2026}"
)

FLAG = "KMUTT_CTF{435_cb_k3y_r3c0v3r3d_2026}"


def _compute_ciphertext() -> bytes:
    cipher = AES.new(SECRET_KEY_STR.encode(), AES.MODE_CBC, SECRET_IV_STR.encode())
    return cipher.encrypt(pad(PLAINTEXT.encode(), AES.block_size))


CIPHERTEXT_BYTES = _compute_ciphertext()
CIPHERTEXT_HEX   = CIPHERTEXT_BYTES.hex()
CIPHERTEXT_B64   = base64.b64encode(CIPHERTEXT_BYTES).decode()

# ─────────────────────────────────────────────
#  SESSION STATE INITIALISATION
# ─────────────────────────────────────────────
if "incident_logs" not in st.session_state:
    st.session_state.incident_logs = []
if "keepalive_ts" not in st.session_state:
    st.session_state.keepalive_ts = datetime.datetime.utcnow()
if "simulator_active" not in st.session_state:
    st.session_state.simulator_active = False
if "ping_count" not in st.session_state:
    st.session_state.ping_count = 0

# ─────────────────────────────────────────────
#  BACKGROUND TRAFFIC SIMULATOR
# ─────────────────────────────────────────────
_INCIDENT_TYPES = [
    ("CRITICAL", "AES-256-CBC", "Encrypted C2 beacon detected on TCP/4444"),
    ("HIGH",     "AES-256-CBC", "Data exfiltration payload intercepted"),
    ("HIGH",     "AES-128-ECB", "Suspicious ECB-mode block pattern observed"),
    ("MEDIUM",   "AES-256-CBC", "Heartbeat keep-alive packet from implant"),
    ("MEDIUM",   "RC4",         "Legacy RC4 stream cipher traffic flagged"),
    ("LOW",      "AES-256-CBC", "Encrypted health-check from monitoring agent"),
    ("LOW",      "AES-256-CBC", "Keep-alive simulator heartbeat OK"),
]


def _generate_sim_payload() -> dict:
    """Generate one simulated encrypted incident log entry."""
    severity, cipher, msg = random.choice(_INCIDENT_TYPES)
    dummy_key   = bytes([random.randint(0, 255) for _ in range(32)])
    dummy_iv    = bytes([random.randint(0, 255) for _ in range(16)])
    dummy_plain = f"SIM-{uuid.uuid4().hex[:8].upper()}: {msg}"
    aes = AES.new(dummy_key, AES.MODE_CBC, dummy_iv)
    ct  = aes.encrypt(pad(dummy_plain.encode(), AES.block_size))
    return {
        "id":        str(uuid.uuid4())[:8].upper(),
        "ts":        datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "severity":  severity,
        "cipher":    cipher,
        "msg":       msg,
        "iv_hex":    dummy_iv.hex()[:16] + "...",
        "ct_b64":    base64.b64encode(ct[:12]).decode() + "...",
    }


def trigger_keepalive():
    """Called on each page load / UptimeRobot GET — updates state."""
    st.session_state.keepalive_ts = datetime.datetime.utcnow()
    st.session_state.ping_count   += 1
    entry = _generate_sim_payload()
    st.session_state.incident_logs.insert(0, entry)
    if len(st.session_state.incident_logs) > 50:
        st.session_state.incident_logs = st.session_state.incident_logs[:50]


# Fire keep-alive on every page load
trigger_keepalive()

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="KMUTT Crypto Forensic Console",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  MINIMAL CSS  (light-on-dark, readable)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #0f1923 !important;
    color: #dde6f0 !important;
}

/* ── Header bar ── */
.header-bar {
    background: #112233;
    border-left: 6px solid #1a7fc1;
    border-radius: 6px;
    padding: 20px 28px;
    margin-bottom: 20px;
}
.header-bar h1 {
    color: #e8f4ff;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 4px 0;
    letter-spacing: 1px;
}
.header-bar p {
    color: #8aaec8;
    font-size: 0.95rem;
    margin: 0;
}

/* ── Section card ── */
.info-card {
    background: #112233;
    border: 1px solid #1e3a52;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 16px;
    color: #dde6f0;
    line-height: 1.7;
}
.info-card b  { color: #7ec8e3; }
.info-card code { background: #0a1929; color: #a8d8f0; padding: 2px 6px; border-radius: 3px; font-family: 'JetBrains Mono', monospace; }

/* ── Step list ── */
.step-item {
    padding: 8px 0;
    border-bottom: 1px solid #1e3a52;
    color: #c5d8e8;
    font-size: 0.97rem;
}
.step-num {
    display: inline-block;
    background: #1a7fc1;
    color: #fff;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    line-height: 24px;
    text-align: center;
    font-size: 0.8rem;
    font-weight: 700;
    margin-right: 10px;
}

/* ── Mono / code block ── */
.mono-block {
    font-family: 'JetBrains Mono', monospace;
    background: #080f18;
    color: #a8f0c8;
    padding: 14px 18px;
    border-radius: 6px;
    border-left: 4px solid #1a7fc1;
    word-break: break-all;
    font-size: 0.82rem;
    line-height: 1.8;
    white-space: pre-wrap;
}

/* ── Result banners ── */
.banner-ok {
    background: #0a2618;
    border: 1px solid #2ecc71;
    border-radius: 6px;
    padding: 18px 22px;
    color: #2ecc71;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.8;
}
.banner-fail {
    background: #220a0a;
    border: 1px solid #e74c3c;
    border-radius: 6px;
    padding: 18px 22px;
    color: #e74c3c;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.6;
}

/* ── Flag chip ── */
.flag-box {
    display: inline-block;
    background: #0a2618;
    border: 2px solid #2ecc71;
    border-radius: 6px;
    padding: 10px 22px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    color: #2ecc71;
    letter-spacing: 1px;
    margin-top: 8px;
}

/* ── Tabs ── */
.stTabs [role="tablist"]      { border-bottom: 2px solid #1e3a52; }
.stTabs [role="tab"]          { color: #8aaec8 !important; font-weight: 600; padding: 8px 20px; }
.stTabs [aria-selected="true"]{ color: #e8f4ff !important; border-bottom: 3px solid #1a7fc1 !important; }

/* ── Streamlit inputs ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: #0a1929 !important;
    color: #dde6f0 !important;
    border: 1px solid #1e3a52 !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label { color: #8aaec8 !important; }

/* ── Metric ── */
[data-testid="stMetricValue"] { color: #7ec8e3 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 1.3rem !important; }
[data-testid="stMetricLabel"] { color: #8aaec8 !important; }

/* ── Button ── */
.stButton > button, .stFormSubmitButton > button {
    background: #1a7fc1 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 10px 28px !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: #1565a0 !important;
}

/* ── Expander ── */
.streamlit-expanderHeader { color: #8aaec8 !important; font-weight: 600 !important; }

/* ── Dataframe ── */
.stDataFrame { background: #0a1929 !important; }

/* ── Divider ── */
hr { border-color: #1e3a52 !important; }

/* ── Download button ── */
.stDownloadButton > button {
    background: #163d26 !important;
    color: #2ecc71 !important;
    border: 1px solid #2ecc71 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}

/* ── Warning/Info/Success boxes ── */
.stAlert { border-radius: 6px !important; }

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
  <h1>KMUTT CRYPTO FORENSIC CONSOLE</h1>
  <p>Cybersecurity Blue Team Lab &nbsp;|&nbsp; AES-256-CBC Incident Response &nbsp;|&nbsp; Final Examination 2026</p>
</div>
""", unsafe_allow_html=True)

# Metric row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Threat Level",  "CRITICAL")
c2.metric("Cipher Suite",  "AES-256-CBC")
c3.metric("C2 Port",       "TCP / 4444")
c4.metric("Flag Status",   "1 Available")

st.divider()

# ─────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "  Incident Scenario & Artifacts  ",
    "  Interactive Forensic Console  ",
    "  Walkthrough & Writeup  ",
    "  🟢 Keep-Alive Monitor  ",
])

# ══════════════════════════════════════════════
#  TAB 1 — Scenario
# ══════════════════════════════════════════════
with tab1:
    st.markdown("## Active Incident Report")

    st.markdown("""
<div class="info-card">
<b>INCIDENT-2026-0515 &nbsp;·&nbsp; CLASSIFIED &nbsp;·&nbsp; KMUTT SOC</b><br><br>
<b>Date / Time &nbsp;:</b> 2026-05-15 &nbsp; 20:21 ICT<br>
<b>Affected System :</b> KMUTT Enterprise SCADA Node — <code>192.168.50.100</code><br>
<b>Initial Alert &nbsp;:</b> IDS triggered on anomalous outbound TCP/4444 beacon with encrypted payload.<br>
<b>Threat Actor TTPs :</b> Custom AES-256-CBC encrypted C2 tunnel in HTTP POST to <code>evil-c2.shadowstrike.io</code><br><br>
Your Blue Team has captured a raw memory dump from the compromised host.
The AES key material was recovered from a running Python process using Volatility3.
<b>Mission: decrypt the payload, extract the operator message, and retrieve the flag.</b>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # Objectives
    st.markdown("### Challenge Objectives")
    steps = [
        "Identify the correct cipher algorithm from forensic evidence (AES-256-CBC).",
        "Extract the 32-byte AES key recovered from process memory.",
        "Extract the 16-byte Initialization Vector (IV) from the network capture.",
        "Decrypt the intercepted ciphertext to recover the plaintext C2 message.",
        "Submit the embedded CTF flag found in the decrypted payload.",
    ]
    for i, s in enumerate(steps, 1):
        st.markdown(
            f'<div class="step-item"><span class="step-num">{i}</span>{s}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # I/O Specification
    st.markdown("### Input / Output Specification")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Inputs**")
        st.markdown("""
| Field | Format |
|---|---|
| Ciphertext | Hex string or Base64 |
| IV | 32 hex chars (16 bytes) |
| Key | 64 hex chars (32 bytes) |
| Algorithm | AES-256-CBC |
""")
    with col_b:
        st.markdown("**Expected Output**")
        st.markdown("""
| Output | Description |
|---|---|
| Plaintext | UTF-8 decoded C2 message |
| Flag line | Last line of decrypted text |
| Flag format | `KMUTT_CTF{...}` |
""")

    st.divider()

    # Flag format
    st.markdown("### Flag Format")
    st.markdown('<div class="flag-box">KMUTT_CTF{435_cb_k3y_r3c0v3r3d_2026}</div>', unsafe_allow_html=True)

    st.divider()

    # Evidence download
    st.markdown("### Evidence Artifacts Download")
    st.info("In a live CTF, artifacts would be hosted on GCS or GitHub. For this demo, the evidence package is generated and available below.")

    evidence_text = f"""====================================================
  KMUTT SOC -- EVIDENCE ARTIFACT PACKAGE
  INCIDENT-2026-0515  |  CLASSIFICATION: RESTRICTED
====================================================

[ARTIFACT-01]  Network Capture -- Encrypted C2 Payload
Algorithm    : AES-256-CBC
Ciphertext   : {CIPHERTEXT_HEX}

[ARTIFACT-02]  Memory Forensics -- Key Material (Volatility3 Extract)
AES Key (hex): {CORRECT_KEY_HEX}
IV (hex)     : {CORRECT_IV_HEX}

[ARTIFACT-03]  IDS Alert
Rule         : ET MALWARE Custom AES C2 Beacon TCP/4444
Direction    : OUTBOUND
Proto        : TCP  Src: 192.168.50.100  Dst: evil-c2.shadowstrike.io:4444

[ARTIFACT-04]  Challenge Metadata
Flag Format  : KMUTT_CTF{{...}}
Expected Flag: {FLAG}

====================================================
  Good luck, Blue Teamer.
====================================================""".strip()

    st.download_button(
        label="Download Evidence Package (.txt)",
        data=evidence_text,
        file_name="INCIDENT-2026-0515_Evidence.txt",
        mime="text/plain"
    )

# ══════════════════════════════════════════════
#  TAB 2 — Interactive Forensic Console
# ══════════════════════════════════════════════
with tab2:
    st.markdown("## AES Decryption Forensic Workbench")

    # Reference values expander
    with st.expander("Show Sample Values — Instructor / Quick-Test Reference", expanded=False):
        st.markdown("Copy-paste these values into the form below to verify a correct decryption:")
        st.markdown(f"""
<div class="mono-block">Algorithm     : AES-256-CBC

Ciphertext (Hex):
{CIPHERTEXT_HEX}

Ciphertext (Base64):
{CIPHERTEXT_B64}

IV (Hex, 32 chars):
{CORRECT_IV_HEX}

Key (Hex, 64 chars):
{CORRECT_KEY_HEX}</div>
""", unsafe_allow_html=True)

    st.divider()

    # Decryption form
    with st.form(key="decrypt_form"):
        st.markdown("### Enter Forensic Evidence")

        algo = st.selectbox(
            "Algorithm",
            options=["AES-256-CBC", "AES-128-ECB", "RC4 (Rivest Cipher 4)"],
            index=0,
            help="Select the cipher algorithm identified from forensic analysis."
        )

        ciphertext_input = st.text_area(
            "Ciphertext",
            height=90,
            placeholder="Paste hex string (e.g. 3a9f...) or Base64 encoded ciphertext here...",
            help="Accepts raw hex string or Base64-encoded ciphertext from the network capture."
        )

        col_iv, col_key = st.columns(2)
        with col_iv:
            iv_input = st.text_input(
                "Initialization Vector (IV)",
                placeholder="32 hex chars (16 bytes)...",
                help="IV extracted from packet capture header."
            )
        with col_key:
            key_input = st.text_input(
                "Encryption Key",
                placeholder="64 hex chars (32 bytes)...",
                help="AES-256 key recovered from memory forensics."
            )

        execute_btn = st.form_submit_button("EXECUTE DECRYPT", use_container_width=True)

    # ── Decryption Logic ──
    if execute_btn:
        st.divider()
        st.markdown("### Decryption Output")

        errors = []
        if not ciphertext_input.strip():
            errors.append("Ciphertext field is empty.")
        if not iv_input.strip():
            errors.append("IV field is empty.")
        if not key_input.strip():
            errors.append("Encryption Key field is empty.")

        if errors:
            for e in errors:
                st.markdown(
                    f'<div class="banner-fail">INPUT ERROR: {e}</div>',
                    unsafe_allow_html=True
                )
        else:
            try:
                # Parse ciphertext — hex or base64
                ct_clean = ciphertext_input.strip().replace(" ", "").replace("\n", "")
                try:
                    ct_bytes = bytes.fromhex(ct_clean)
                except ValueError:
                    ct_bytes = base64.b64decode(ct_clean)

                iv_bytes  = bytes.fromhex(iv_input.strip())
                key_bytes = bytes.fromhex(key_input.strip())

                if algo == "AES-256-CBC":
                    if len(key_bytes) != 32:
                        raise ValueError(
                            f"Key must be 32 bytes for AES-256. Got {len(key_bytes)} bytes."
                        )
                    if len(iv_bytes) != 16:
                        raise ValueError(
                            f"IV must be 16 bytes for AES-CBC. Got {len(iv_bytes)} bytes."
                        )

                    cipher    = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
                    plaintext = unpad(cipher.decrypt(ct_bytes), AES.block_size).decode("utf-8")

                    # Success
                    result_html = plaintext.replace("\n", "<br>")
                    st.markdown(f"""
<div class="banner-ok">
DECRYPTION SUCCESSFUL &nbsp;|&nbsp; AES-256-CBC &nbsp;|&nbsp; PKCS#7 Padding OK<br>
{'─'*60}<br>
{result_html}
</div>
""", unsafe_allow_html=True)
                    st.balloons()
                    st.success(f"FLAG CAPTURED: `{FLAG}`")

                elif algo == "AES-128-ECB":
                    raise ValueError(
                        "CryptographicError: AES-128-ECB requires a 16-byte key.\n"
                        "Evidence contains 32-byte key material — algorithm mismatch.\n"
                        "ECB mode also has no IV, inconsistent with the captured packet structure."
                    )
                else:
                    raise ValueError(
                        "CryptographicError: RC4 is a stream cipher and does not use\n"
                        "block padding or a fixed IV. Algorithm selection is inconsistent\n"
                        "with the block-aligned, IV-prefixed structure seen in the PCAP."
                    )

            except (ValueError, KeyError) as exc:
                st.markdown(
                    f'<div class="banner-fail">CRYPTOGRAPHIC ERROR<br><br>{str(exc).replace(chr(10), "<br>")}</div>',
                    unsafe_allow_html=True
                )
            except Exception as exc:
                st.markdown(
                    f'<div class="banner-fail">UNEXPECTED ERROR<br><br>{type(exc).__name__}: {exc}</div>',
                    unsafe_allow_html=True
                )

    st.divider()

    # Key Material Analyser
    st.markdown("### Key Material Analyser")
    probe_key = st.text_input(
        "Paste a hex key to inspect:",
        placeholder="64 hex chars...",
        key="probe_key"
    )
    if probe_key:
        try:
            kb = bytes.fromhex(probe_key.strip())
            st.markdown(f"""
<div class="mono-block">Length  : {len(kb)} bytes ({len(kb)*8} bits)
Unique  : {len(set(kb))} unique byte values
MD5     : {hashlib.md5(kb).hexdigest()}
SHA-256 : {hashlib.sha256(kb).hexdigest()}
UTF-8   : {kb.decode('utf-8', errors='replace')}</div>
""", unsafe_allow_html=True)
            if len(kb) == 32:
                st.success("Valid AES-256 key length (32 bytes)")
            elif len(kb) == 16:
                st.warning("Valid AES-128 key length (16 bytes) — does not match the evidence (32 bytes required).")
            else:
                st.error(f"Invalid key length ({len(kb)} bytes). AES requires 16, 24, or 32 bytes.")
        except Exception:
            st.error("Invalid hex string. Please check your input.")

# ══════════════════════════════════════════════
#  TAB 3 — Walkthrough & Writeup
# ══════════════════════════════════════════════
with tab3:
    st.markdown("## Instructor Walkthrough & Solution Writeup")
    st.warning("INSTRUCTOR USE ONLY — Contains the full solution. Do not share with students before the exam.")

    with st.expander("Step-by-Step Blue Team Analysis Pipeline", expanded=False):
        st.markdown("""
### Phase 1 — Initial Triage

The IDS alert flags anomalous **outbound TCP/4444** traffic with a binary encrypted payload.
Packet inspection reveals:

- Fixed 16-byte header block at payload offset 0 — this is the **IV**.
- Payload length is a multiple of 16 bytes — consistent with an **AES block cipher**.
- No repeated 16-byte blocks — rules out **ECB mode**, confirms **CBC mode**.

---

### Phase 2 — Memory Forensics (Volatility3)

```bash
# List Python processes on the compromised SCADA node
vol.py -f memory.dmp windows.pslist | grep python

# Dump the heap of the suspicious PID (e.g., 4812)
vol.py -f memory.dmp windows.memmap --pid 4812 --dump

# Search for AES key material near known strings
strings pid.4812.dmp | grep -A2 -B2 "KMUTT"
```

The string `KMUTT_SECRET_KEY_AES256_CBC_2026` is found adjacent to a Python
`AES.new()` call frame in heap memory — this is the 32-byte key.

---

### Phase 3 — IV Extraction from PCAP

```python
import pyshark

cap = pyshark.FileCapture('c2_traffic.pcap', display_filter='tcp.port==4444')
pkt = next(iter(cap))
raw = bytes.fromhex(pkt.tcp.payload.replace(':', ''))
iv  = raw[:16]   # First 16 bytes = IV
ct  = raw[16:]   # Remainder     = Ciphertext
print("IV (hex):", iv.hex())
print("CT (hex):", ct.hex())
```

---

### Phase 4 — Programmatic Decryption (Solution Script)

```python
#!/usr/bin/env python3
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

KEY_HEX = "4b4d5554545f5345435245545f4b45595f4145533235365f4342435f32303236"
IV_HEX  = "4b4d5554545f49565f313662797465_73".replace("_", "")
CT_HEX  = "<paste ciphertext hex from evidence package>"

key = bytes.fromhex(KEY_HEX)
iv  = bytes.fromhex(IV_HEX)
ct  = bytes.fromhex(CT_HEX)

cipher    = AES.new(key, AES.MODE_CBC, iv)
plaintext = unpad(cipher.decrypt(ct), AES.block_size).decode()

print("=" * 60)
print("DECRYPTED C2 MESSAGE:")
print("=" * 60)
print(plaintext)
# Last line: RECOVERY FLAG: KMUTT_CTF{435_cb_k3y_r3c0v3r3d_2026}
```

---

### Phase 5 — Why the Distractors Fail

| Algorithm   | Failure Reason |
|-------------|---------------|
| AES-128-ECB | Needs 16-byte key; 32-byte key causes ValueError. ECB has no IV field. |
| RC4         | Stream cipher, no block alignment, no IV — incompatible with PCAP structure. |
| AES-256-CBC | **Correct** — 32-byte key, 16-byte IV, PKCS#7 padding validated successfully. |

---

### Exact Flag
""")
        st.markdown(
            f'<div class="flag-box" style="font-size:1.2rem;">{FLAG}</div>',
            unsafe_allow_html=True
        )

    with st.expander("Grading Rubric", expanded=False):
        rubric = pd.DataFrame({
            "Step": [
                "Algorithm identification (AES-256-CBC)",
                "Key format and length validation (32 bytes)",
                "IV extraction and format (16 bytes)",
                "Correct decryption — no padding error",
                "Flag submission — exact string match",
            ],
            "Points": [20, 20, 20, 20, 20],
            "Criteria": [
                "Must select CBC, not ECB or RC4",
                "64-char hex string required",
                "32-char hex string required",
                "Plaintext matches canonical output",
                "KMUTT_CTF{435_cb_k3y_r3c0v3r3d_2026}",
            ]
        })
        st.dataframe(rubric, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════
#  TAB 4 — Keep-Alive Monitor
# ══════════════════════════════════════════════
with tab4:
    st.markdown("## 🟢 Keep-Alive Traffic Simulator & Monitor")
    st.info(
        "This panel shows the live status of the background keep-alive system. "
        "Every page load (including pings from UptimeRobot or GitHub Actions) "
        "generates a simulated encrypted traffic entry and updates the timestamp below."
    )

    # Status metrics
    ka_ts   = st.session_state.keepalive_ts
    elapsed = (datetime.datetime.utcnow() - ka_ts).seconds
    m1, m2, m3 = st.columns(3)
    m1.metric("Last Keep-Alive",  ka_ts.strftime("%H:%M:%S UTC"))
    m2.metric("Total Pings",       str(st.session_state.ping_count))
    m3.metric("Log Entries",       str(len(st.session_state.incident_logs)))

    st.divider()

    # Manual trigger
    col_btn, col_auto = st.columns([1, 2])
    with col_btn:
        if st.button("⚡ Manual Heartbeat Trigger", use_container_width=True):
            trigger_keepalive()
            st.success("Heartbeat triggered — log updated.")
            st.rerun()
    with col_auto:
        if st.toggle("Auto-refresh every 30 s", key="auto_refresh"):
            time.sleep(30)
            trigger_keepalive()
            st.rerun()

    st.divider()

    # External trigger instructions
    st.markdown("### External Trigger Instructions")
    st.markdown("""
<div class="info-card">
<b>Option A — UptimeRobot (Recommended for Streamlit Cloud)</b><br><br>
1. Create a free account at <code>uptimerobot.com</code><br>
2. Add a new monitor → <b>HTTP(s)</b><br>
3. URL: <code>https://&lt;your-app&gt;.streamlit.app</code><br>
4. Check Interval: <b>10 minutes</b><br>
5. UptimeRobot will GET the page every 10 min, keeping it awake.
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="info-card" style="margin-top:12px;">
<b>Option B — GitHub Actions (cron schedule)</b><br><br>
Create <code>.github/workflows/keepalive.yml</code> in your repo:
</div>
""", unsafe_allow_html=True)

    st.code("""
name: Keep-Alive Ping
on:
  schedule:
    - cron: '*/10 * * * *'   # every 10 minutes
  workflow_dispatch:
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Ping Streamlit App
        run: python cron_job.py --url ${{ secrets.STREAMLIT_APP_URL }}
""", language="yaml")

    st.markdown("""
<div class="info-card" style="margin-top:12px;">
<b>Option C — Local cron (Linux/macOS)</b><br><br>
Add to crontab (<code>crontab -e</code>):<br>
<code>*/10 * * * * cd /path/to/project && python cron_job.py --url https://&lt;your-app&gt;.streamlit.app</code>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # Live Incident Logs panel
    st.markdown("### 📋 Latest Incident Logs (Live Feed)")
    if not st.session_state.incident_logs:
        st.warning("No logs yet — trigger a heartbeat or reload the page.")
    else:
        SEVERITY_COLOR = {"CRITICAL": "#e74c3c", "HIGH": "#e67e22", "MEDIUM": "#f1c40f", "LOW": "#2ecc71"}
        for entry in st.session_state.incident_logs[:15]:
            color = SEVERITY_COLOR.get(entry["severity"], "#8aaec8")
            st.markdown(f"""
<div class="mono-block" style="border-left-color:{color}; margin-bottom:8px; font-size:0.78rem;">
[{entry['ts']}]  ID:{entry['id']}  <span style="color:{color};font-weight:700;">{entry['severity']}</span>  {entry['cipher']}<br>
Event   : {entry['msg']}<br>
IV      : {entry['iv_hex']}  |  CT(b64): {entry['ct_b64']}
</div>
""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📂 Download `cron_job.py`")
    st.info("The companion pinger script is saved as `cron_job.py` in the project root. "
            "Use it with GitHub Actions or run it locally to keep the app alive.")

# ─────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center; color:#4a6a85; font-size:0.82rem; padding:8px 0;">
    KMUTT Crypto Forensic Console &nbsp;|&nbsp; Blue Team CTF Lab &nbsp;|&nbsp;
    King Mongkut's University of Technology Thonburi &nbsp;|&nbsp; 2026<br>
    Built with Python, Streamlit, PyCryptodome &amp; Keep-Alive Simulator
</div>
""", unsafe_allow_html=True)
