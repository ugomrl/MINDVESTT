# -*- coding: utf-8 -*-
"""
███  MINDVEST — application complète en un seul fichier  ███
Assistant patrimonial intelligent + chatbot IA (Claude) pour jeunes actifs.

▶ Lancer :   streamlit run mindvest_app.py
▶ Dépendances :
     pip install streamlit anthropic plotly pandas requests streamlit-option-menu

⚠️  SÉCURITÉ : ta clé API est écrite EN DUR ci-dessous (ANTHROPIC_API_KEY).
    Ce fichier ne doit JAMAIS être poussé sur GitHub tel quel (voir .gitignore).
    Pour un déploiement public, préfère st.secrets / variable d'environnement.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ═══════════════════════════════════════════════════════════════════════
#  🔑 CONFIGURATION — CLÉ API EN DUR (remplace la valeur ci-dessous)
# ═══════════════════════════════════════════════════════════════════════
ANTHROPIC_API_KEY = "sk-ant-..."          # ⬅️⬅️⬅️  COLLE TA CLÉ ANTHROPIC ICI
MODEL = "claude-opus-4-8"                   # modèle le plus capable (ou "claude-haiku-4-5" pour réduire les coûts)
MAX_TOKENS = 1500
FREE_MONTHLY_LIMIT = 5                      # messages chatbot / mois en plan gratuit

_PLACEHOLDER = "sk-ant-..."


def api_key() -> str | None:
    """Clé effective : constante en dur, sinon secrets Streamlit, sinon variable d'env."""
    if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != _PLACEHOLDER:
        return ANTHROPIC_API_KEY
    try:
        if st.secrets.get("ANTHROPIC_API_KEY"):
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


# ═══════════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM — palette + CSS
# ═══════════════════════════════════════════════════════════════════════
PRIMARY_BLUE = "#0F4C8B"
DARK_BLUE = "#0A2E52"
GOLD = "#D4A574"
LIGHT_GOLD = "#E8D4C4"
BG_LIGHT = "#F8F9FB"
TEXT_PRIMARY = "#2C3E50"
TEXT_SECONDARY = "#6B7280"
SUCCESS_GREEN = "#10B981"
WARNING_ORANGE = "#F97316"
ERROR_RED = "#EF4444"
CHART_COLORS = [PRIMARY_BLUE, GOLD, SUCCESS_GREEN, WARNING_ORANGE, ERROR_RED, "#94A3B8"]

st.set_page_config(page_title="MINDVEST", page_icon="🧠", layout="wide",
                   initial_sidebar_state="expanded")

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', -apple-system, sans-serif; }
.stApp { background-color: #F8F9FB; }
#MainMenu, header[data-testid="stHeader"], footer { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1150px; }

[data-testid="stSidebar"] { background-color: #0A2E52; border-right: none; }
[data-testid="stSidebar"] * { color: #E5E7EB; }
[data-testid="stSidebar"] .stButton > button { background:#D4A574; color:#0A2E52; font-weight:700; border:none; }
[data-testid="stSidebar"] .stButton > button:hover { background:#C9975F; color:#0A2E52; }

.mv-logo { display:flex; align-items:center; gap:10px; font-weight:800; font-size:22px;
           letter-spacing:0.5px; color:#D4A574; margin:4px 0 18px 0; }
.mv-premium-card { background:linear-gradient(135deg,#0F4C8B,#0A2E52); border:1px solid #D4A574;
           border-radius:12px; padding:16px; margin-top:10px; text-align:center; }
.mv-premium-card .title { color:#D4A574; font-weight:700; font-size:15px; }
.mv-premium-card .sub { color:#E5E7EB; font-size:12px; margin-top:4px; }

.mv-h1 { font-size:30px; font-weight:800; color:#0F4C8B; letter-spacing:-0.5px; margin:0 0 4px 0; }
.mv-sub { color:#6B7280; font-size:14px; margin-bottom:20px; }

.mv-card { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:12px; padding:20px;
           margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.mv-header-card { background:linear-gradient(135deg,#0F4C8B,#0A2E52); border-radius:14px;
           padding:22px 24px; margin-bottom:22px; color:#FFF; box-shadow:0 10px 25px rgba(15,76,139,0.15); }
.mv-header-card h1 { color:#FFF; font-size:24px; font-weight:800; margin:0; }
.mv-header-card p { color:#E8D4C4; font-size:13px; margin:6px 0 0 0; }

.mv-kpi { background:linear-gradient(135deg,#F8F9FB,#FFFFFF); border:1px solid #E5E7EB;
          border-left:4px solid #D4A574; border-radius:10px; padding:16px; height:100%; }
.mv-kpi .icon { font-size:24px; }
.mv-kpi .label { color:#6B7280; font-size:12px; font-weight:500; margin-top:4px; }
.mv-kpi .value { color:#0F4C8B; font-size:22px; font-weight:800; line-height:1.1; }

.mv-step { background:#FFF; border:1px solid #E5E7EB; border-left:4px solid #0F4C8B;
           border-radius:12px; padding:18px 20px; margin-bottom:14px; box-shadow:0 2px 4px rgba(0,0,0,0.05); }
.mv-step.crit { border-left-color:#EF4444; } .mv-step.warn { border-left-color:#F97316; }
.mv-step.ok { border-left-color:#10B981; } .mv-step.soon { border-left-color:#0F4C8B; }
.mv-step h3 { font-size:16px; font-weight:700; color:#0A2E52; margin:0 0 6px 0; }

.mv-badge { display:inline-block; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600; margin-right:6px; }
.mv-badge.crit { background:rgba(239,68,68,0.12); color:#EF4444; }
.mv-badge.warn { background:rgba(249,115,22,0.12); color:#F97316; }
.mv-badge.ok { background:rgba(16,185,129,0.12); color:#10B981; }
.mv-badge.soon { background:rgba(15,76,139,0.12); color:#0F4C8B; }

.mv-progress { background:#E5E7EB; height:8px; border-radius:4px; overflow:hidden; margin:8px 0; }
.mv-progress > span { display:block; height:100%; background:linear-gradient(90deg,#0F4C8B,#D4A574); }

.mv-scenario { background:linear-gradient(135deg,#FFF,#F8F9FB); border:1px solid #E5E7EB;
           border-radius:12px; padding:18px; margin:12px 0; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.mv-scenario.pos { border-left:4px solid #10B981; } .mv-scenario.neg { border-left:4px solid #EF4444; }
.mv-line { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #EEF1F5; font-size:14px; }
.mv-line .v-pos { color:#10B981; font-weight:600; } .mv-line .v-neg { color:#EF4444; font-weight:600; }
.mv-line.total { background:rgba(15,76,139,0.06); border-radius:6px; padding:10px 8px; border:none; font-weight:800; color:#0F4C8B; margin-top:6px; }

.mv-info { background:linear-gradient(90deg,rgba(15,76,139,0.05),rgba(212,165,116,0.06)); border:1px solid #D4A574;
           border-left:4px solid #D4A574; border-radius:8px; padding:12px 14px; font-size:13px; color:#2C3E50; margin:10px 0; }
.mv-news { border-left:4px solid #10B981; } .mv-news.mid { border-left-color:#F97316; } .mv-news.low { border-left-color:#9CA3AF; }
.mv-news .title { font-weight:700; color:#0F4C8B; font-size:15px; }
.mv-news .meta { color:#6B7280; font-size:12px; margin:4px 0 8px 0; }

.mv-bubble-user { background:#0F4C8B; color:#FFF; border-radius:16px 16px 4px 16px; padding:12px 16px;
           margin:8px 0 8px auto; max-width:78%; width:fit-content; font-size:14px; line-height:1.55; }
.mv-bubble-bot { background:#FFF; color:#2C3E50; border:1px solid #E5E7EB; border-radius:16px 16px 16px 4px;
           padding:12px 16px; margin:8px auto 8px 0; max-width:82%; width:fit-content; font-size:14px; line-height:1.6; }

.stButton > button { border-radius:8px; font-weight:600; border:1px solid #E5E7EB; transition:all 0.15s ease; }
.stButton > button[kind="primary"] { background:#0F4C8B; border:none; color:#FFF; }
.stButton > button[kind="primary"]:hover { background:#0A2E52; box-shadow:0 8px 18px rgba(15,76,139,0.18); transform:translateY(-1px); }
[data-testid="stMetricValue"] { color:#0F4C8B; font-weight:800; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ── Thème SOMBRE (fond noir, texte clair) — superposé au style clair ci-dessus ──
_DARK_CSS = """
<style>
.stApp { background-color:#0A0E17 !important; }
.stApp, .stMarkdown, .stMarkdown p, .stMarkdown li,
[data-testid="stCaptionContainer"], .stApp label { color:#E5E7EB !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color:#F3F4F6 !important; }
.mv-card, .mv-kpi, .mv-step, .mv-scenario {
  background:#141B29 !important; border-color:#263145 !important; color:#E5E7EB !important; }
.mv-h1, .mv-step h3, .mv-kpi .value, .mv-news .title, .mv-line.total { color:#EAD8BE !important; }
.mv-sub, .mv-kpi .label, .mv-news .meta { color:#9AA4B2 !important; }
.mv-line { border-bottom-color:#263145 !important; }
.mv-info { background:rgba(212,165,116,0.08) !important; color:#E5E7EB !important; }
.mv-bubble-bot { background:#1B2434 !important; color:#E5E7EB !important; border-color:#263145 !important; }
.mv-progress { background:#263145 !important; }
.stButton > button { background:#1B2434 !important; color:#E5E7EB !important; border-color:#2A3347 !important; }
.stButton > button[kind="primary"] { background:#0F4C8B !important; color:#FFFFFF !important; }
[data-testid="stMetricValue"] { color:#EAD8BE !important; }
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
[data-testid="stChatInput"] textarea { background:#141B29 !important; color:#E5E7EB !important; }
</style>
"""
st.markdown(_DARK_CSS, unsafe_allow_html=True)


# ── Helpers UI ──────────────────────────────────────────────────────────
def eur(value: float) -> str:
    try:
        return f"{value:,.0f} €".replace(",", " ")
    except (ValueError, TypeError):
        return "— €"


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="mv-header-card"><h1>{icon} {title}</h1>{sub}</div>', unsafe_allow_html=True)


def kpi_card(icon: str, label: str, value: str) -> str:
    return (f'<div class="mv-kpi"><div class="icon">{icon}</div>'
            f'<div class="value">{value}</div><div class="label">{label}</div></div>')


def progress_bar(pct: float) -> str:
    pct = max(0.0, min(100.0, pct))
    return f'<div class="mv-progress"><span style="width:{pct:.0f}%"></span></div>'


def info_box(text: str, icon: str = "💡") -> None:
    st.markdown(f'<div class="mv-info">{icon} {text}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES (SQLite)
# ═══════════════════════════════════════════════════════════════════════
DB_PATH = Path(__file__).resolve().parent / "mindvest.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY, name TEXT, profile_json TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, role TEXT, content TEXT, created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, stars INTEGER, created_at TEXT)""")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_profile() -> dict[str, Any]:
    return {
        "name": None, "age": None, "salaire_net": None, "charges_fixes": None, "dettes": None,
        "objectifs_1an": [], "objectifs_5ans": [], "objectifs_10ans": [],
        "profil_risque": 5, "esg": False, "situation_immo": None, "projet_immo": None,
        "budget_immo": None, "patrimoine": [], "plan": "gratuit", "premium_until": None,
        "onboarded": False, "created_at": None,
    }


def get_user(email: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:
        return None
    profile = default_profile()
    profile.update(json.loads(row["profile_json"] or "{}"))
    profile["name"] = row["name"]
    profile["created_at"] = row["created_at"]
    profile["email"] = email
    return profile


def create_user(email: str) -> dict[str, Any]:
    existing = get_user(email)
    if existing:
        return existing
    profile = default_profile()
    created = _now()
    with _conn() as c:
        c.execute("INSERT INTO users (email, name, profile_json, created_at) VALUES (?,?,?,?)",
                  (email, None, json.dumps(profile), created))
    profile["created_at"] = created
    profile["email"] = email
    return profile


def save_profile(email: str, profile: dict[str, Any]) -> None:
    to_store = {k: v for k, v in profile.items() if k not in ("email", "created_at")}
    with _conn() as c:
        c.execute("UPDATE users SET name = ?, profile_json = ? WHERE email = ?",
                  (profile.get("name"), json.dumps(to_store), email))


def add_chat_message(email: str, role: str, content: str) -> None:
    with _conn() as c:
        c.execute("INSERT INTO chat_messages (email, role, content, created_at) VALUES (?,?,?,?)",
                  (email, role, content, _now()))


def load_chat_history(email: str, limit: int = 100) -> list[dict[str, str]]:
    with _conn() as c:
        rows = c.execute("SELECT role, content FROM chat_messages WHERE email = ? ORDER BY id ASC LIMIT ?",
                         (email, limit)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def clear_chat(email: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM chat_messages WHERE email = ?", (email,))


def count_messages_this_month(email: str) -> int:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    with _conn() as c:
        row = c.execute("SELECT COUNT(*) AS n FROM chat_messages WHERE email = ? AND role = 'user' AND created_at >= ?",
                        (email, start)).fetchone()
    return int(row["n"])


def save_rating(email: str, stars: int) -> None:
    with _conn() as c:
        c.execute("INSERT INTO ratings (email, stars, created_at) VALUES (?,?,?)", (email, stars, _now()))


# ═══════════════════════════════════════════════════════════════════════
#  MOTEUR FINANCIER (estimations pédagogiques — pas un conseil en invest.)
# ═══════════════════════════════════════════════════════════════════════
CATEGORIES = ["Immobilier", "PEA", "Assurance-Vie", "Livrets", "Actions", "Crypto", "Autres"]
LIQUID_CATEGORIES = {"Livrets"}


def marge_mensuelle(profile: dict[str, Any]) -> float:
    return max(0.0, float(profile.get("salaire_net") or 0) - float(profile.get("charges_fixes") or 0))


def patrimoine_total(assets: list[dict[str, Any]]) -> float:
    return float(sum((a.get("montant") or 0) for a in assets))


def repartition(assets: list[dict[str, Any]]) -> dict[str, float]:
    agg: dict[str, float] = {}
    for a in assets:
        cat = a.get("categorie") or "Autres"
        agg[cat] = agg.get(cat, 0.0) + float(a.get("montant") or 0)
    return {k: v for k, v in agg.items() if v > 0}


def epargne_precaution_actuelle(assets: list[dict[str, Any]]) -> float:
    return float(sum((a.get("montant") or 0) for a in assets if a.get("categorie") in LIQUID_CATEGORIES))


def diversification_score(assets: list[dict[str, Any]]) -> int:
    rep = repartition(assets)
    total = sum(rep.values())
    if total <= 0 or len(rep) <= 1:
        return 0 if total <= 0 else 25
    shares = [v / total for v in rep.values()]
    hhi = sum(s * s for s in shares)
    n = len(shares)
    best = 1.0 / n
    score = (1 - hhi) / (1 - best) * 100 if n > 1 else 0
    return int(max(0, min(100, round(score))))


def rendement_moyen_pondere(assets: list[dict[str, Any]]) -> float:
    total = patrimoine_total(assets)
    if total <= 0:
        return 0.0
    return sum((a.get("montant") or 0) * (a.get("perf") or 0) for a in assets) / total


def risk_label(score: int) -> str:
    return ["Très prudent", "Très prudent", "Très prudent", "Prudent", "Prudent",
            "Modéré", "Modéré", "Dynamique", "Dynamique", "Offensif", "Offensif"][max(0, min(10, score))]


def allocation_cible(score: int) -> tuple[int, int]:
    actions = int(max(20, min(90, round(20 + score * 7))))
    return actions, 100 - actions


def rendement_attendu(score: int) -> float:
    return 0.02 + (score / 10.0) * 0.06


def mensualite(capital: float, taux_annuel: float, annees: int) -> float:
    if capital <= 0:
        return 0.0
    n = annees * 12
    r = taux_annuel / 12.0
    if r == 0:
        return capital / n
    return capital * r / (1 - (1 + r) ** (-n))


def simulation_credit(prix: float, apport: float, taux: float, annees: int,
                      assurance_taux: float = 0.0045) -> dict[str, float]:
    emprunt = max(0.0, prix - apport)
    m = mensualite(emprunt, taux, annees)
    assurance_mens = emprunt * assurance_taux / 12.0
    n = annees * 12
    total_rembourse = m * n
    return {
        "emprunt": emprunt, "mensualite": m, "assurance_mensuelle": assurance_mens,
        "mensualite_totale": m + assurance_mens, "cout_interets": total_rembourse - emprunt,
        "total_rembourse": total_rembourse, "assurance_totale": assurance_mens * n,
    }


def taux_endettement(mensualite_totale: float, salaire_net: float) -> float:
    return mensualite_totale / salaire_net * 100.0 if salaire_net else 0.0


def diagnostic_precaution(actuel: float, charges_fixes: float, mensualite_epargne: float = 200.0) -> dict[str, Any]:
    cible = 3 * (charges_fixes or 0)
    manque = max(0.0, cible - actuel)
    if cible <= 0:
        statut = "inconnu"
    elif actuel >= cible:
        statut = "ok"
    elif actuel >= 0.5 * cible:
        statut = "en_cours"
    else:
        statut = "critique"
    mois = math.ceil(manque / mensualite_epargne) if mensualite_epargne > 0 and manque > 0 else 0
    pct = (actuel / cible * 100.0) if cible > 0 else 0.0
    return {"cible": cible, "actuel": actuel, "manque": manque, "statut": statut,
            "mois_pour_completer": mois, "pct": min(100.0, pct)}


def strategie(profile: dict[str, Any]) -> dict[str, Any]:
    assets = profile.get("patrimoine", [])
    charges = profile.get("charges_fixes") or 0
    marge = marge_mensuelle(profile)
    score = profile.get("profil_risque", 5)
    precaution = epargne_precaution_actuelle(assets)
    diag = diagnostic_precaution(precaution, charges)

    step_precaution = {
        "titre": "Épargne de précaution",
        "statut": {"critique": "crit", "en_cours": "warn", "ok": "ok"}.get(diag["statut"], "soon"),
        "badge": {"critique": "🔴 Critique", "en_cours": "⚠️ En cours", "ok": "✅ Constituée"}.get(diag["statut"], "À évaluer"),
        "diag": diag,
    }

    projet = profile.get("projet_immo")
    budget = profile.get("budget_immo") or 0
    step_immo = None
    if projet and projet != "Non" and budget > 0:
        apport_cible = budget * 0.20
        apport_actuel = min(apport_cible, precaution * 0.5)
        urgent = projet in ("2-5 ans", "<2 ans")
        step_immo = {
            "titre": "Projet immobilier", "statut": "warn" if urgent else "soon",
            "badge": ("🟠 Important" if urgent else "🔵 À venir"), "budget": budget,
            "apport_cible": apport_cible, "apport_actuel": apport_actuel,
            "manque": max(0.0, apport_cible - apport_actuel),
            "pct": (apport_actuel / apport_cible * 100.0) if apport_cible else 0.0, "horizon": projet,
        }

    actions, oblig = allocation_cible(score)
    step_invest = {"titre": "Structure d'investissement", "statut": "ok", "badge": "🟢 Après la précaution",
                   "actions_pct": actions, "obligations_pct": oblig, "esg": profile.get("esg", False),
                   "risk_label": risk_label(score)}

    reste = marge
    alloc = {}
    if diag["statut"] in ("critique", "en_cours"):
        p = min(reste, 200.0); alloc["Épargne précaution"] = p; reste -= p
    if step_immo and step_immo["manque"] > 0:
        p = min(reste, max(0.0, reste * 0.6)); alloc["Apport immobilier"] = round(p); reste -= p
    invest = min(reste, max(0.0, reste * 0.75))
    if invest > 0:
        alloc["Investissement PEA/AV"] = round(invest); reste -= invest
    if reste > 0:
        alloc["Réserve flexible"] = round(reste)

    return {"marge": marge, "precaution": step_precaution, "immo": step_immo,
            "invest": step_invest, "alloc": {"titre": "Répartition mensuelle", "marge": marge, "allocation": alloc}}


def projection(profile: dict[str, Any], annees: int = 10, invest_mensuel: float | None = None) -> dict[str, list[float]]:
    assets = profile.get("patrimoine", [])
    rep = repartition(assets)
    immo = rep.get("Immobilier", 0.0)
    financier = patrimoine_total(assets) - immo
    r_fin = rendement_attendu(profile.get("profil_risque", 5))
    r_immo = 0.035
    if invest_mensuel is None:
        invest_mensuel = strategie(profile)["alloc"]["allocation"].get("Investissement PEA/AV", 0.0)
    xs = list(range(annees + 1))
    total, part_immo, part_fin = [], [], []
    fin, im = financier, immo
    for _ in xs:
        total.append(fin + im); part_fin.append(fin); part_immo.append(im)
        fin = fin * (1 + r_fin) + invest_mensuel * 12
        im = im * (1 + r_immo)
    return {"annees": xs, "total": total, "financier": part_fin, "immobilier": part_immo}


# ═══════════════════════════════════════════════════════════════════════
#  DONNÉES DE MARCHÉ — taux (BCE en direct + repli démo) & actualités
# ═══════════════════════════════════════════════════════════════════════
_SEED_RATES = {"taux_bce": 2.25, "inflation": 1.9, "livret_a": 2.40, "ldds": 2.40,
               "livret_boost": 3.00, "credit_immo_20ans": 3.20, "prix_m2_france": 3200,
               "source": "Données de démonstration"}


@st.cache_data(ttl=60 * 60 * 6)
def get_rates() -> dict[str, Any]:
    rates = dict(_SEED_RATES)
    rates["updated_at"] = date.today().isoformat()
    try:
        url = ("https://data-api.ecb.europa.eu/service/data/FM/"
               "D.U2.EUR.4F.KR.DFR.LEV?lastNObservations=1&format=csvdata")
        resp = requests.get(url, timeout=4)
        if resp.ok and resp.text:
            value = float(resp.text.strip().splitlines()[-1].split(",")[-1])
            rates["taux_bce"] = round(value, 2)
            rates["source"] = "BCE (data-api.ecb.europa.eu) — en direct"
    except Exception:
        pass
    return rates


def livrets(rates: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    r = rates or get_rates()
    data = [
        {"medaille": "🥇", "nom": "Livret bancaire boosté", "taux": r["livret_boost"],
         "avantages": "Meilleur taux, accès immédiat", "inconvenients": "Taux promo temporaire", "cta": "Ouvrir un compte"},
        {"medaille": "🥈", "nom": "LDDS", "taux": r["ldds"],
         "avantages": "Intérêts exonérés d'impôt", "inconvenients": "Plafond 12 000 €", "cta": "Demander à sa banque"},
        {"medaille": "🥉", "nom": "Livret A", "taux": r["livret_a"],
         "avantages": "Garanti par l'État, plafond 22 950 €", "inconvenients": "Taux modéré", "cta": "Souvent déjà ouvert"},
    ]
    return sorted(data, key=lambda x: x["taux"], reverse=True)


def credit_banques(rates: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    r = rates or get_rates()
    base = r["credit_immo_20ans"]
    grille = [("Banque en ligne A", base, 2200), ("Banque en ligne B", base + 0.10, 2400),
              ("Grande banque C", base + 0.30, 3000), ("Réseau mutualiste D", base + 0.40, 2800),
              ("Grande banque E", base + 0.50, 3200)]
    return [{"banque": n, "taux": round(t, 2), "frais": f} for n, t, f in grille]


_NEWS = [
    {"cat": "Taux/Crédit", "icon": "📉", "titre": "La BCE stabilise ses taux — impact sur les crédits immobiliers",
     "resume": "Les taux directeurs restent stables ce trimestre. Les taux de crédit immobilier pourraient se détendre "
               "légèrement, bon moment pour renégocier son assurance emprunteur.", "source": "BCE — taux directeurs",
     "quand": "Il y a 2 h", "url": "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html"},
    {"cat": "Immobilier", "icon": "🏠", "titre": "Prix immobiliers : reprise modérée dans les grandes métropoles",
     "resume": "Après deux ans de correction, les prix repartent doucement (+1 à 2 % sur un an). Les acheteurs avec apport "
               "gardent un pouvoir de négociation.", "source": "Notaires de France",
     "quand": "Hier", "url": "https://www.notaires.fr/fr/immobilier-fiscalite/prix-et-tendances-de-limmobilier"},
    {"cat": "Investissement", "icon": "📈", "titre": "ETF Monde : les versements programmés séduisent les jeunes actifs",
     "resume": "Investir une somme fixe chaque mois sur un ETF diversifié lisse le risque d'entrée. La régularité prime "
               "sur le timing de marché.", "source": "La Finance Pour Tous",
     "quand": "Il y a 1 j", "url": "https://www.lafinancepourtous.com/outils/dossiers/les-etf-ou-trackers/"},
    {"cat": "ESG", "icon": "🌱", "titre": "Labels ISR : comment repérer un fonds réellement responsable",
     "resume": "Tous les fonds 'verts' ne se valent pas. Vérifier le label ISR/Greenfin et la composition réelle du "
               "portefeuille avant d'investir.", "source": "Label ISR (officiel)",
     "quand": "Il y a 2 j", "url": "https://www.lelabelisr.fr/"},
    {"cat": "Économie", "icon": "💶", "titre": "Inflation sous contrôle : ce que ça change pour ton épargne",
     "resume": "Avec une inflation proche de 2 %, les livrets réglementés protègent mieux le pouvoir d'achat qu'en 2023, "
               "mais restent insuffisants sur le long terme.", "source": "La Finance Pour Tous",
     "quand": "Il y a 3 j", "url": "https://www.lafinancepourtous.com/decryptages/politiques-economiques/theories-economiques/inflation/"},
    {"cat": "Crypto", "icon": "🪙", "titre": "Cryptoactifs : la part raisonnable dans un patrimoine diversifié",
     "resume": "Très volatils, les cryptoactifs sont à cantonner à une petite poche (souvent < 5 %) que l'on peut accepter "
               "de voir fortement varier.", "source": "AMF — épargnants",
     "quand": "Il y a 4 j", "url": "https://www.amf-france.org/fr/espace-epargnants/proteger-son-epargne/les-crypto-actifs"},
]
CATEGORIES_NEWS = ["Tout", "Immobilier", "Taux/Crédit", "Investissement", "Économie", "ESG", "Crypto"]


def _pertinence(article: dict[str, Any], profile: dict[str, Any]) -> int:
    score = 5
    cat = article["cat"]
    projet = profile.get("projet_immo")
    risque = profile.get("profil_risque", 5)
    if cat in ("Immobilier", "Taux/Crédit") and projet and projet != "Non":
        score += 3
    if cat == "ESG" and profile.get("esg"):
        score += 3
    if cat == "Investissement" and risque >= 5:
        score += 2
    if cat == "Crypto":
        score += 2 if risque >= 8 else (-2 if risque < 4 else 0)
    return max(1, min(10, score))


def get_news(profile: dict[str, Any], categorie: str = "Tout") -> list[dict[str, Any]]:
    items = []
    for a in _NEWS:
        if categorie != "Tout" and a["cat"] != categorie:
            continue
        art = dict(a); art["pertinence"] = _pertinence(a, profile); items.append(art)
    return sorted(items, key=lambda x: x["pertinence"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════
#  CHATBOT — Claude (API Anthropic)
# ═══════════════════════════════════════════════════════════════════════
def chatbot_configured() -> bool:
    return bool(api_key())


@st.cache_resource(show_spinner=False)
def _anthropic_client(key: str):
    # La clé est un argument : si elle change (secrets mis à jour), le cache
    # se régénère automatiquement au lieu de garder un client périmé.
    from anthropic import Anthropic
    return Anthropic(api_key=key)


def build_system_prompt(profile: dict[str, Any], rates: dict[str, Any]) -> str:
    marge = marge_mensuelle(profile)
    actions, oblig = allocation_cible(profile.get("profil_risque", 5))
    patrimoine = profile.get("patrimoine", [])
    contexte = {
        "prenom_nom": profile.get("name"), "age": profile.get("age"),
        "salaire_net_mensuel": profile.get("salaire_net"), "charges_fixes_mensuelles": profile.get("charges_fixes"),
        "marge_disponible_mensuelle": marge, "profil_risque_sur_10": profile.get("profil_risque"),
        "profil_risque_libelle": risk_label(profile.get("profil_risque", 5)),
        "allocation_cible": f"{actions}% actions / {oblig}% obligations-fonds euros",
        "preference_esg": profile.get("esg"), "situation_immobiliere": profile.get("situation_immo"),
        "projet_immobilier": profile.get("projet_immo"), "budget_immobilier": profile.get("budget_immo"),
        "patrimoine": patrimoine, "patrimoine_total": patrimoine_total(patrimoine),
    }
    taux = {"taux_bce": rates.get("taux_bce"), "inflation": rates.get("inflation"),
            "livret_a": rates.get("livret_a"), "meilleur_livret": rates.get("livret_boost"),
            "credit_immo_20ans": rates.get("credit_immo_20ans"), "prix_m2_france": rates.get("prix_m2_france")}
    return f"""Tu es MINDVEST, un assistant patrimonial expert en finances personnelles françaises, \
spécialisé pour les jeunes actifs (20-45 ans).

CONTEXTE UTILISATEUR (chiffres réels, à utiliser dans tes réponses) :
{json.dumps(contexte, ensure_ascii=False, indent=2)}

TAUX ET DONNÉES DE MARCHÉ DU JOUR :
{json.dumps(taux, ensure_ascii=False, indent=2)}

RÈGLES :
1. Personnalise au maximum avec SES chiffres (marge, patrimoine, projet immo).
2. Cite des ordres de grandeur et fais des calculs concrets.
3. CONFORMITÉ : ne donne jamais de recommandation d'achat d'un produit précis ; explique les \
mécanismes, les enveloppes (PEA, assurance-vie), avantages/risques, et laisse l'utilisateur décider.
4. Pédagogie : réponses claires, structurées, sans jargon non expliqué.
5. Termine par 1 à 3 prochaines étapes actionnables.
6. Rappelle si pertinent que tu ne remplaces pas un conseiller agréé.
7. Réponds en français, ton chaleureux mais précis. Reste sous ~400 mots sauf demande de détail."""


def stream_reply(messages: list[dict[str, str]], profile: dict[str, Any], rates: dict[str, Any]) -> Iterator[str]:
    client = _anthropic_client(api_key())
    with client.messages.stream(model=MODEL, max_tokens=MAX_TOKENS,
                                system=build_system_prompt(profile, rates), messages=messages) as stream:
        for text in stream.text_stream:
            yield text


# ═══════════════════════════════════════════════════════════════════════
#  AUTHENTIFICATION (connexion par email)
# ═══════════════════════════════════════════════════════════════════════
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login(email: str) -> None:
    email = email.strip().lower()
    st.session_state.email = email
    st.session_state.profile = get_user(email) or create_user(email)


def logout() -> None:
    for key in ("email", "profile", "chat_history", "onboard_step", "nav"):
        st.session_state.pop(key, None)


def show_login() -> None:
    st.markdown(f"""
    <div style="text-align:center; margin-top:6vh;">
      <div style="font-size:52px;">🧠💎</div>
      <div style="font-size:34px; font-weight:800; color:{PRIMARY_BLUE}; letter-spacing:2px;">MINDVEST</div>
      <div style="color:{TEXT_SECONDARY}; font-size:16px; margin-top:8px;">Ton assistant patrimonial intelligent</div>
      <div style="color:{TEXT_SECONDARY}; font-size:14px;">Gère ton patrimoine comme un expert</div>
    </div>""", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        with st.container(border=True):
            st.markdown("#### Connecte-toi avec ton email")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="tape ton email…", label_visibility="collapsed")
                submitted = st.form_submit_button("Continuer  →", type="primary", use_container_width=True)
            if submitted:
                if _EMAIL_RE.match(email.strip()):
                    login(email); st.rerun()
                else:
                    st.error("❌ Merci d'entrer une adresse email valide.")
            st.caption("Ton profil est enregistré localement et lié à cet email.")


# ═══════════════════════════════════════════════════════════════════════
#  ONBOARDING (5 étapes)
# ═══════════════════════════════════════════════════════════════════════
TOTAL_STEPS = 5
OBJ_1AN = ["Épargne de précaution", "Commencer à investir", "Rembourser une dette", "Rien de particulier"]
OBJ_5ANS = ["Acheter un bien immobilier", "Portefeuille investi", "Diminuer mes dettes", "Préparer ma retraite"]
OBJ_10ANS = ["Retraite confortable", "Patrimoine diversifié", "Placements ESG", "Indépendance financière"]


def onboarding() -> None:
    p = st.session_state.profile
    step = st.session_state.get("onboard_step", 1)

    st.markdown(f"<div style='font-size:26px;font-weight:800;color:{PRIMARY_BLUE};'>Bienvenue sur MINDVEST 🧠💎</div>",
                unsafe_allow_html=True)
    st.markdown(f"<div style='color:{GOLD};font-weight:600;'>Étape {step}/{TOTAL_STEPS}</div>", unsafe_allow_html=True)
    st.markdown(progress_bar(step / TOTAL_STEPS * 100), unsafe_allow_html=True)
    st.write("")

    with st.container(border=True):
        if step == 1:
            st.markdown("### Qui es-tu ?")
            p["name"] = st.text_input("Prénom & nom", value=p.get("name") or "", placeholder="tape ton nom complet…") or None
            p["age"] = st.slider("Âge", 18, 70, value=int(p.get("age") or 30))
        elif step == 2:
            st.markdown("### Ta situation financière")
            p["salaire_net"] = st.number_input("💰 Salaire NET mensuel (€)", 0, step=100, value=int(p.get("salaire_net") or 0))
            p["charges_fixes"] = st.number_input("🏠 Charges fixes mensuelles (€)", 0, step=50, value=int(p.get("charges_fixes") or 0))
            p["dettes"] = st.number_input("📊 Dettes en cours (€, 0 si aucune)", 0, step=100, value=int(p.get("dettes") or 0))
            if marge_mensuelle(p) > 0:
                st.success(f"✅ Marge disponible estimée : **{eur(marge_mensuelle(p))} / mois**")
        elif step == 3:
            st.markdown("### Tes objectifs")
            p["objectifs_1an"] = st.multiselect("🎯 Dans 1 an", OBJ_1AN, default=p.get("objectifs_1an") or [])
            p["objectifs_5ans"] = st.multiselect("🎯 Dans 5 ans", OBJ_5ANS, default=p.get("objectifs_5ans") or [])
            p["objectifs_10ans"] = st.multiselect("🎯 Dans 10 ans et +", OBJ_10ANS, default=p.get("objectifs_10ans") or [])
        elif step == 4:
            st.markdown("### Ton appétence au risque")
            p["profil_risque"] = st.slider("De très prudent (0) à offensif (10)", 0, 10, value=int(p.get("profil_risque", 5)))
            actions, oblig = allocation_cible(p["profil_risque"])
            st.markdown(f"Profil : **{risk_label(p['profil_risque'])}** · Allocation cible : "
                        f"**{actions}% actions / {oblig}% obligations & fonds euros**")
            p["esg"] = st.checkbox("🌱 Prioriser les investissements responsables (ESG)", value=bool(p.get("esg")))
        else:
            st.markdown("### Situation immobilière")
            situations = ["Locataire", "Propriétaire", "Hébergé(e)"]
            p["situation_immo"] = st.radio("🏠 Propriétaire ou locataire ?", situations,
                                           index=situations.index(p["situation_immo"]) if p.get("situation_immo") in situations else 0)
            projets = ["Non", "5+ ans", "2-5 ans", "<2 ans"]
            p["projet_immo"] = st.radio("🎯 Projet d'achat immobilier ?", projets,
                                        index=projets.index(p["projet_immo"]) if p.get("projet_immo") in projets else 0)
            if p["projet_immo"] != "Non":
                p["budget_immo"] = st.number_input("💰 Budget estimé (€)", 0, step=10000, value=int(p.get("budget_immo") or 0))
            else:
                p["budget_immo"] = None

    left, right = st.columns(2)
    with left:
        if step > 1 and st.button("◀ Précédent", use_container_width=True):
            st.session_state.onboard_step = step - 1
            save_profile(st.session_state.email, p); st.rerun()
    with right:
        if step < TOTAL_STEPS:
            if st.button("Suivant  ▶", type="primary", use_container_width=True):
                st.session_state.onboard_step = step + 1
                save_profile(st.session_state.email, p); st.rerun()
        else:
            if st.button("Terminer  ✓", type="primary", use_container_width=True):
                p["onboarded"] = True
                save_profile(st.session_state.email, p)
                st.session_state.nav = "Profil"; st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  ONGLETS
# ═══════════════════════════════════════════════════════════════════════
def _plotly(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, sans-serif", color="#2C3E50", size=12),
                      legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    return fig


def tab_profil(p: dict) -> None:
    page_header("👤", p.get("name") or "Ton profil", f"{p.get('age', '—')} ans · {p.get('email', '')}")
    marge = marge_mensuelle(p)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("💰", "Salaire net", eur(p.get("salaire_net") or 0)), unsafe_allow_html=True)
    c2.markdown(kpi_card("🏠", "Charges fixes", eur(p.get("charges_fixes") or 0)), unsafe_allow_html=True)
    c3.markdown(kpi_card("✅", "Marge dispo", eur(marge) + " /mois"), unsafe_allow_html=True)
    c4.markdown(kpi_card("📊", "Profil risque", f"{risk_label(p.get('profil_risque', 5))} ({p.get('profil_risque', 5)}/10)"),
                unsafe_allow_html=True)
    st.write("")
    st.markdown("#### 🎯 Objectifs par horizon")
    oc1, oc2, oc3 = st.columns(3)
    for col, titre, key in [(oc1, "1 an", "objectifs_1an"), (oc2, "5 ans", "objectifs_5ans"), (oc3, "10 ans +", "objectifs_10ans")]:
        with col:
            st.markdown(f"**{titre}**")
            items = p.get(key) or []
            if items:
                for o in items:
                    st.markdown(f"✅ {o}")
            else:
                st.caption("Aucun objectif renseigné")
    st.write("")
    with st.expander("✏️ Éditer mon profil"):
        with st.form("edit_profile"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Prénom & nom", value=p.get("name") or "")
                age = st.number_input("Âge", 18, 99, value=int(p.get("age") or 30))
                salaire = st.number_input("Salaire net (€)", 0, step=100, value=int(p.get("salaire_net") or 0))
                charges = st.number_input("Charges fixes (€)", 0, step=50, value=int(p.get("charges_fixes") or 0))
            with col2:
                risque = st.slider("Profil de risque", 0, 10, int(p.get("profil_risque", 5)))
                esg = st.checkbox("Préférence ESG", value=bool(p.get("esg")))
                situations = ["Locataire", "Propriétaire", "Hébergé(e)"]
                situ = st.selectbox("Situation immobilière", situations,
                                    index=situations.index(p["situation_immo"]) if p.get("situation_immo") in situations else 0)
                projets = ["Non", "5+ ans", "2-5 ans", "<2 ans"]
                projet = st.selectbox("Projet immobilier", projets,
                                      index=projets.index(p["projet_immo"]) if p.get("projet_immo") in projets else 0)
                budget = st.number_input("Budget immobilier (€)", 0, step=10000, value=int(p.get("budget_immo") or 0))
            if st.form_submit_button("💾 Enregistrer", type="primary"):
                p.update({"name": name or None, "age": age, "salaire_net": salaire, "charges_fixes": charges,
                          "profil_risque": risque, "esg": esg, "situation_immo": situ, "projet_immo": projet,
                          "budget_immo": budget or None})
                save_profile(st.session_state.email, p)
                st.success("Profil mis à jour ✅"); st.rerun()


def tab_patrimoine(p: dict) -> None:
    page_header("📊", "Mon patrimoine", "Vue d'ensemble et répartition de tes actifs")
    assets = p.get("patrimoine", [])
    total = patrimoine_total(assets)
    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi_card("💎", "Patrimoine total", eur(total)), unsafe_allow_html=True)
    c2.markdown(kpi_card("📈", "Rendement moyen", f"{rendement_moyen_pondere(assets):+.1f} %/an"), unsafe_allow_html=True)
    c3.markdown(kpi_card("🎯", "Diversification", f"{diversification_score(assets)}/100"), unsafe_allow_html=True)
    st.write("")
    st.markdown("#### ✏️ Détail de tes actifs")
    st.caption("Ajoute, modifie ou supprime des lignes, puis enregistre.")
    df = pd.DataFrame(assets) if assets else pd.DataFrame(columns=["categorie", "montant", "perf"])
    df = df.reindex(columns=["categorie", "montant", "perf"])
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="patri_editor",
        column_config={
            "categorie": st.column_config.SelectboxColumn("Actif", options=CATEGORIES, required=True),
            "montant": st.column_config.NumberColumn("Montant (€)", min_value=0, step=500, format="%d"),
            "perf": st.column_config.NumberColumn("Perf/an (%)", step=0.1, format="%.1f")})
    if st.button("💾 Enregistrer", type="primary"):
        cleaned = [{"categorie": r["categorie"], "montant": float(r["montant"] or 0), "perf": float(r["perf"] or 0)}
                   for _, r in edited.iterrows() if pd.notna(r.get("categorie")) and (r.get("montant") or 0) > 0]
        p["patrimoine"] = cleaned
        save_profile(st.session_state.email, p)
        st.success("Patrimoine enregistré ✅"); st.rerun()
    if not assets:
        info_box("Renseigne tes actifs pour débloquer les graphiques et une stratégie personnalisée.", icon="ℹ️")
        return
    rep = repartition(assets)
    st.write("")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### Répartition")
        fig = go.Figure(data=[go.Pie(labels=list(rep.keys()), values=list(rep.values()),
            marker=dict(colors=CHART_COLORS), textinfo="label+percent",
            hovertemplate="%{label}<br>%{value:,.0f} €<br>%{percent}<extra></extra>")])
        st.plotly_chart(_plotly(fig), use_container_width=True)
    with g2:
        st.markdown("#### Projection 10 ans")
        proj = projection(p, annees=10)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=proj["annees"], y=proj["total"], mode="lines", name="Patrimoine total",
            line=dict(color=PRIMARY_BLUE, width=3), fill="tozeroy", fillcolor="rgba(15,76,139,0.10)",
            hovertemplate="Année %{x}<br>%{y:,.0f} €<extra></extra>"))
        fig2.update_xaxes(title="Années")
        st.plotly_chart(_plotly(fig2), use_container_width=True)
        st.caption(f"Projection indicative : **{eur(proj['total'][-1])}** dans 10 ans "
                   f"(+{eur(proj['total'][-1] - total)}), hypothèses simplifiées.")


def tab_strategie(p: dict) -> None:
    page_header("🎯", "Ta stratégie personnalisée",
                f"Âge {p.get('age','—')} · Profil {risk_label(p.get('profil_risque',5))} · ESG : {'Oui' if p.get('esg') else 'Non'}")
    if not p.get("salaire_net"):
        info_box("Complète ta situation financière dans l'onglet Profil pour générer ta stratégie.")
        return
    strat = strategie(p)
    prec = strat["precaution"]; d = prec["diag"]
    st.markdown(f"""<div class="mv-step {prec['statut']}"><h3>Étape 1 · {prec['titre']}</h3>
        <span class="mv-badge {prec['statut']}">{prec['badge']}</span>{progress_bar(d['pct'])}
        Cible (3 mois de charges) : <b>{eur(d['cible'])}</b> · Actuel : <b>{eur(d['actuel'])}</b>
        · Manque : <b>{eur(d['manque'])}</b></div>""", unsafe_allow_html=True)
    if d["manque"] > 0:
        info_box(f"En épargnant 200 €/mois, précaution complète en ~{d['mois_pour_completer']} mois.")
    elif d["cible"] > 0:
        st.success("🎉 Bravo ! Ton épargne de précaution est complète — cap sur l'investissement.")
    if strat["immo"]:
        im = strat["immo"]
        st.markdown(f"""<div class="mv-step {im['statut']}"><h3>Étape 2 · {im['titre']}</h3>
            <span class="mv-badge {im['statut']}">{im['badge']} · horizon {im['horizon']}</span>{progress_bar(im['pct'])}
            Budget visé : <b>{eur(im['budget'])}</b> · Apport recommandé (20 %) : <b>{eur(im['apport_cible'])}</b>
            · Reste à épargner : <b>{eur(im['manque'])}</b></div>""", unsafe_allow_html=True)
    inv = strat["invest"]
    esg_txt = " · biais ESG activé 🌱" if inv["esg"] else ""
    st.markdown(f"""<div class="mv-step {inv['statut']}"><h3>Étape 3 · {inv['titre']}</h3>
        <span class="mv-badge {inv['statut']}">{inv['badge']}</span>
        Allocation cible ({inv['risk_label']}) : <b>{inv['actions_pct']}% actions</b> /
        <b>{inv['obligations_pct']}% obligations & fonds euros</b>{esg_txt}<br>
        <span style="color:{TEXT_SECONDARY};font-size:13px;">Enveloppes à privilégier : PEA (actions, fiscalité
        après 5 ans) et assurance-vie (flexibilité, fonds euros).</span></div>""", unsafe_allow_html=True)
    alloc = strat["alloc"]["allocation"]
    st.markdown(f"""<div class="mv-step ok"><h3>Étape 4 · Répartition mensuelle</h3>
        Marge disponible : <b>{eur(strat['marge'])}</b> / mois</div>""", unsafe_allow_html=True)
    if alloc:
        cols = st.columns(len(alloc))
        for col, (label, val) in zip(cols, alloc.items()):
            col.markdown(kpi_card("→", label, eur(val)), unsafe_allow_html=True)
        st.write("")
        st.markdown("#### 🥧 Ton camembert d'épargne idéale (selon ton profil)")
        cp, cn = st.columns([1.2, 1])
        with cp:
            figa = go.Figure(data=[go.Pie(
                labels=list(alloc.keys()), values=list(alloc.values()), hole=0.45,
                marker=dict(colors=CHART_COLORS), textinfo="label+percent",
                hovertemplate="%{label}<br>%{value:,.0f} €/mois<br>%{percent}<extra></extra>")])
            figa.update_layout(showlegend=False)
            st.plotly_chart(_plotly(figa, height=300), use_container_width=True)
        with cn:
            st.markdown("**Comment lire ce camembert ?**")
            st.caption("Il répartit ta marge mensuelle entre précaution, apport immobilier, "
                       "investissement et réserve — pondérée selon ton profil de risque, ton âge "
                       "et ton projet immo. Modifie ton profil et il s'adapte en direct.")
    st.write("")
    st.markdown("#### 📈 Projection 10 ans (si tu suis ce plan)")
    proj = projection(p, annees=10)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=proj["annees"], y=proj["immobilier"], name="Immobilier", stackgroup="one", line=dict(color=GOLD, width=0)))
    fig.add_trace(go.Scatter(x=proj["annees"], y=proj["financier"], name="Investissements", stackgroup="one", line=dict(color=PRIMARY_BLUE, width=0)))
    fig.update_xaxes(title="Années")
    st.plotly_chart(_plotly(fig), use_container_width=True)
    info_box("Projection sur hypothèses de rendement (selon ton profil, immobilier +3,5 %/an). Résultats non garantis.", icon="⚠️")


def tab_epargne(p: dict) -> None:
    page_header("💰", "Épargne vs Investissement", "Diagnostic et simulateurs personnalisés")
    rates = get_rates()
    t_diag, t_credit = st.tabs(["📊 Diagnostic épargne", "🏦 Crédit vs comptant"])
    with t_diag:
        charges = p.get("charges_fixes") or 0
        actuel = st.slider("Épargne d'urgence disponible (€)", 0, 50000,
                           int(epargne_precaution_actuelle(p.get("patrimoine", []))), step=500)
        mensuel = st.slider("Combien peux-tu épargner par mois ? (€)", 0, 2000, 200, step=50)
        diag = diagnostic_precaution(actuel, charges, max(mensuel, 1))
        badge = {"critique": ("neg", "🔴 Critique"), "en_cours": ("neg", "⚠️ À compléter"),
                 "ok": ("pos", "✅ Constituée"), "inconnu": ("neg", "Renseigne tes charges")}[diag["statut"]]
        st.markdown(f"""<div class="mv-scenario {badge[0]}">
            <span class="mv-badge {'ok' if badge[0]=='pos' else 'crit'}">{badge[1]}</span>
            <div class="mv-line"><span>Épargne actuelle</span><span>{eur(diag['actuel'])}</span></div>
            <div class="mv-line"><span>Objectif (3 mois de charges)</span><span>{eur(diag['cible'])}</span></div>
            <div class="mv-line"><span>Manque</span><span class="v-neg">{eur(diag['manque'])}</span></div>
            <div class="mv-line total"><span>Délai pour compléter</span><span>{diag['mois_pour_completer']} mois</span></div></div>""",
            unsafe_allow_html=True)
        st.markdown("#### 🏆 Meilleurs placements pour la précaution")
        for l in livrets(rates):
            st.markdown(f"""<div class="mv-info">{l['medaille']} <b>{l['nom']}</b> — <b>{l['taux']:.2f} %</b> · {l['avantages']}<br>
                <span style="color:{TEXT_SECONDARY};font-size:12px;">Sur 10 000 € : ~{eur(10000*l['taux']/100)}/an · {l['inconvenients']}</span></div>""",
                unsafe_allow_html=True)
    with t_credit:
        default_budget = int(p.get("budget_immo") or 250000)
        c1, c2 = st.columns(2)
        with c1:
            prix = st.slider("Prix du bien (€)", 100000, 800000, default_budget, step=10000)
            apport = st.slider("Apport disponible (€)", 0, 300000, int(default_budget * 0.2), step=5000)
        with c2:
            duree = st.slider("Durée du crédit (ans)", 10, 30, 20)
            taux = st.slider("Taux du crédit (%)", 1.0, 6.0, float(rates["credit_immo_20ans"]), step=0.05)
        sim = simulation_credit(prix, apport, taux / 100, duree)
        endettement = taux_endettement(sim["mensualite_totale"], p.get("salaire_net") or 0)
        st.markdown(f"""<div class="mv-scenario neg"><h4 style="margin:0 0 8px 0;color:{PRIMARY_BLUE};">📊 Scénario crédit</h4>
            <div class="mv-line"><span>Montant emprunté</span><span>{eur(sim['emprunt'])}</span></div>
            <div class="mv-line"><span>Mensualité (hors assurance)</span><span>{eur(sim['mensualite'])}</span></div>
            <div class="mv-line"><span>+ assurance emprunteur</span><span>{eur(sim['assurance_mensuelle'])}</span></div>
            <div class="mv-line"><span>Coût total des intérêts</span><span class="v-neg">{eur(sim['cout_interets'])}</span></div>
            <div class="mv-line total"><span>Mensualité totale</span><span>{eur(sim['mensualite_totale'])}</span></div></div>""",
            unsafe_allow_html=True)
        if p.get("salaire_net"):
            if endettement > 35:
                st.error(f"⚠️ Taux d'endettement : **{endettement:.0f}%** — au-dessus du seuil prudentiel de 35 %.")
            else:
                st.success(f"✅ Taux d'endettement : **{endettement:.0f}%** — sous le seuil de 35 %.")
        info_box("Le crédit permet de garder son épargne investie (effet de levier), mais coûte des intérêts. "
                 "La bonne décision dépend du taux, de l'horizon et de la stabilité pro.")


def tab_taux(p: dict) -> None:
    rates = get_rates()
    page_header("📈", "Comparateur de taux", f"Mise à jour : {rates.get('updated_at')} · Source : {rates.get('source')}")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("🏦", "Taux BCE (dépôt)", f"{rates['taux_bce']:.2f} %"), unsafe_allow_html=True)
    c2.markdown(kpi_card("📉", "Inflation", f"{rates['inflation']:.1f} %"), unsafe_allow_html=True)
    c3.markdown(kpi_card("🏠", "Crédit immo 20 ans", f"{rates['credit_immo_20ans']:.2f} %"), unsafe_allow_html=True)
    c4.markdown(kpi_card("💳", "Meilleur livret", f"{rates['livret_boost']:.2f} %"), unsafe_allow_html=True)
    st.write("")
    t_liv, t_cred = st.tabs(["💳 Livrets", "🏦 Crédit immobilier"])
    with t_liv:
        st.markdown("#### Classement des livrets (sur 10 000 € placés)")
        rows = [{"": l["medaille"], "Livret": l["nom"], "Taux": f"{l['taux']:.2f} %",
                 "Gain 1 an": eur(10000 * l["taux"] / 100), "Avantages": l["avantages"]} for l in livrets(rates)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        info_box("Astuce : combiner LDDS (défiscalisé) et un livret boosté maximise le rendement de la précaution.")
    with t_cred:
        st.markdown("#### Grille de taux crédit immobilier (indicative)")
        budg = int(p.get("budget_immo") or 250000)
        prix = st.number_input("Montant emprunté (€)", 50000, 1000000, budg - int(budg * 0.2), step=10000)
        duree = st.slider("Durée (ans)", 10, 30, 20, key="taux_duree")
        rows = [{"Banque": b["banque"], "Taux": f"{b['taux']:.2f} %",
                 "Mensualité": eur(mensualite(prix, b["taux"] / 100, duree)), "Frais de dossier": eur(b["frais"])}
                for b in credit_banques(rates)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        banks = credit_banques(rates)
        ecart = (banks[-1]["taux"] - banks[0]["taux"]) / 100 * prix * duree
        info_box(f"Écart meilleure vs moins bonne offre : ~{eur(ecart)} sur {duree} ans. Faire jouer la concurrence est très rentable.")


def tab_actualites(p: dict) -> None:
    page_header("📰", "Actualités filtrées pour toi",
                f"Profil {risk_label(p.get('profil_risque',5))} · ESG {'oui' if p.get('esg') else 'non'} · "
                f"Projet immo : {p.get('projet_immo') or '—'}")
    categorie = st.radio("Filtres", CATEGORIES_NEWS, horizontal=True, label_visibility="collapsed")
    news = get_news(p, categorie)
    if not news:
        st.caption("Aucune actualité dans cette catégorie."); return
    st.caption(f"📚 {len(news)} article(s) triés par pertinence pour toi · clique un titre pour lire la source")
    for a in news:
        cls = "mv-news" if a["pertinence"] >= 8 else ("mv-news mid" if a["pertinence"] >= 5 else "mv-news low")
        tag = "🟢 très pertinent" if a["pertinence"] >= 8 else ("🟠 pertinent" if a["pertinence"] >= 5 else "⚪ pour info")
        st.markdown(f"""<div class="mv-card {cls}">
            <a href="{a['url']}" target="_blank" style="text-decoration:none;color:inherit;">
              <div class="title">{a['icon']} {a['titre']} <span style="color:#D4A574;">↗</span></div></a>
            <div class="meta">{a['source']} · {a['quand']} · {tag} · {a['cat']}</div>
            {a['resume']}
            <div style="margin-top:10px;"><a href="{a['url']}" target="_blank"
              style="color:#D4A574;font-weight:600;text-decoration:none;font-size:13px;">Lire l'article →</a></div>
            </div>""", unsafe_allow_html=True)


SUGGESTIONS = [
    "Faut-il que j'ouvre un PEA ou une assurance-vie ?",
    "Est-ce le bon moment pour un crédit immobilier ?",
    "Comment bien diversifier mon portefeuille ?",
    "Combien devrais-je garder en épargne de précaution ?",
    "Comment réduire mes impôts légalement ?",
    "Par où commencer pour investir avec ma marge ?",
]


def _bubble(role: str, content: str) -> str:
    cls = "mv-bubble-user" if role == "user" else "mv-bubble-bot"
    return f'<div class="{cls}">{content.replace(chr(10), "<br>")}</div>'


def tab_chatbot(p: dict) -> None:
    page_header("💬", "Chatbot finance", "Réponses personnalisées, basées sur ton profil réel")
    email = st.session_state.email
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_chat_history(email)
    configured = chatbot_configured()
    if not configured:
        info_box("Le chatbot nécessite ta clé API Anthropic. Renseigne ANTHROPIC_API_KEY en haut de "
                 "<code>mindvest_app.py</code>, puis relance l'app.", icon="🔑")
    used = count_messages_this_month(email)
    if p.get("plan") != "premium":
        st.caption(f"Plan gratuit · **{max(0, FREE_MONTHLY_LIMIT - used)}** message(s) restant(s) ce mois-ci (sur {FREE_MONTHLY_LIMIT}).")
    for m in st.session_state.chat_history:
        st.markdown(_bubble(m["role"], m["content"]), unsafe_allow_html=True)
    pending = None
    with st.expander("💡 Questions rapides", expanded=not st.session_state.chat_history):
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTIONS):
            if cols[i % 2].button(q, key=f"sugg_{i}", use_container_width=True):
                pending = q
    if st.session_state.chat_history and st.button("🗑️ Effacer l'historique"):
        clear_chat(email); st.session_state.chat_history = []; st.rerun()
    prompt = st.chat_input("Pose ta question finance…", disabled=not configured)
    user_msg = prompt or pending
    if not user_msg:
        return
    if p.get("plan") != "premium" and used >= FREE_MONTHLY_LIMIT:
        st.warning("⚠️ Limite du plan gratuit atteinte ce mois-ci. Passe en Premium pour un accès illimité.")
        return
    st.session_state.chat_history.append({"role": "user", "content": user_msg})
    add_chat_message(email, "user", user_msg)
    st.markdown(_bubble("user", user_msg), unsafe_allow_html=True)
    rates = get_rates()
    try:
        with st.spinner("Claude réfléchit…"):
            full = st.write_stream(stream_reply(st.session_state.chat_history, p, rates))
    except Exception as exc:
        full = f"⚠️ Impossible de contacter l'assistant ({type(exc).__name__}). Vérifie ta clé API."
        st.error(full)
    st.session_state.chat_history.append({"role": "assistant", "content": full})
    add_chat_message(email, "assistant", full)
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  NAVIGATION + MAIN
# ═══════════════════════════════════════════════════════════════════════
NAV = [
    ("Profil", "person", tab_profil), ("Patrimoine", "bar-chart", tab_patrimoine),
    ("Stratégie", "bullseye", tab_strategie), ("Épargne", "piggy-bank", tab_epargne),
    ("Taux", "graph-up-arrow", tab_taux), ("Actualités", "newspaper", tab_actualites),
    ("Chatbot", "chat-dots", tab_chatbot),
]
NAV_LABELS = [n[0] for n in NAV]


def sidebar_nav() -> str:
    with st.sidebar:
        st.markdown('<div class="mv-logo"><span>🧠</span> MINDVEST</div>', unsafe_allow_html=True)
        default_index = NAV_LABELS.index(st.session_state.nav) if st.session_state.get("nav") in NAV_LABELS else 0
        try:
            from streamlit_option_menu import option_menu
            selected = option_menu(None, NAV_LABELS, icons=[n[1] for n in NAV], default_index=default_index,
                styles={"container": {"background-color": DARK_BLUE, "padding": "0"},
                        "icon": {"color": "#B0BEC5", "font-size": "16px"},
                        "nav-link": {"color": "#B0BEC5", "font-size": "14px", "font-weight": "500",
                                     "padding": "12px 16px", "border-left": "3px solid transparent",
                                     "--hover-color": "rgba(212,165,116,0.10)"},
                        "nav-link-selected": {"background-color": "rgba(212,165,116,0.12)", "color": GOLD,
                                              "font-weight": "600", "border-left": f"3px solid {GOLD}"}})
        except Exception:
            selected = st.radio("Navigation", NAV_LABELS, index=default_index, label_visibility="collapsed")
        if selected not in NAV_LABELS:
            selected = NAV_LABELS[default_index]
        st.session_state.nav = selected

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        p = st.session_state.profile
        if p.get("plan") == "premium":
            st.markdown('<div class="mv-premium-card"><div class="title">💎 Premium actif</div>'
                        '<div class="sub">Accès illimité au chatbot</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="mv-premium-card"><div class="title">💎 Premium</div>'
                        '<div class="sub">Chatbot illimité · 4,99 €/mois</div></div>', unsafe_allow_html=True)
            if st.button("Passer Premium", use_container_width=True):
                p["plan"] = "premium"
                p["premium_until"] = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                save_profile(st.session_state.email, p)
                st.toast("Bienvenue en Premium 💎", icon="✅"); st.rerun()

        st.markdown("<hr style='border-color:rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        st.caption(f"Connecté : {st.session_state.email}")
        if st.button("Se déconnecter", use_container_width=True):
            logout(); st.rerun()
    return selected


def main() -> None:
    init_db()
    if not st.session_state.get("email"):
        show_login()
        return
    if not st.session_state.profile.get("onboarded"):
        onboarding()
        return
    selected = sidebar_nav()
    render = dict((label, fn) for label, _, fn in NAV).get(selected, tab_profil)
    render(st.session_state.profile)


if __name__ == "__main__":
    main()
