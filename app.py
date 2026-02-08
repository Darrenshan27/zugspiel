"""
ZUGSPIEL – STREAMLIT APP

============================================================
⭐ Orientierung: Wo werden die Kampf-Resultate berechnet?
============================================================

Szenario 1 (Querschnitt-Modell):
    Funktion: simulate_one_round_s1(...)
    -> "Fight result" Bereich:
       - p_hit_player / p_hit_enemy
       - kills_on_enemy / kills_on_player
       - Anwenden der Verluste + Spielende

Szenario 2 (Konstante Trefferchance pro Schuss):
    Funktion: simulate_one_round_s2(...)
    -> "Fight result" Bereich:
       - kills_on_enemy / kills_on_player (je Soldat 1 Schuss pro Runde)
       - Anwenden der Verluste + Spielende

Szenario 3 (Armee-Auswahl + Firepower):
    Funktion: simulate_one_round_s3(...)
    -> "Fight result" Bereich:
       - kills_on_enemy / kills_on_player (je Soldat firepower Schüsse pro Runde)
       - Anwenden der Verluste + Spielende
"""

import time
import random
import base64
from pathlib import Path
import streamlit as st

# ============================================================
# KONFIG
# ============================================================
N_PLAYER_START = 50
M_ENEMY_START = 30

# Szenario 3: Gegner-Setup (konfigurierbar)
S3_ENEMY_SOLDIERS = 45
S3_ENEMY_FIREPOWER = 2

# Szenario 2: konstante Trefferchance pro Schuss
HIT_CHANCE_S2 = 0.10

# Szenario 1: Querschnitt n, Trefferchance pro Schütze = exposed / n
CROSS_SECTION_N_S1 = 40

TICK_SECONDS = 0.1
MAX_LOG_LINES = 200

# Freischaltung Erklärung nach X SPIELEN (pro Szenario separat)
UNLOCK_EXPLANATION_AFTER_GAMES = 5

# Startseiten-Hintergrund
START_BACKGROUND = "start.png"

# Hintergründe pro Szenario
BACKGROUND_FILES_S1 = [
    "szenario1.png",
    "szenario1_1.png",
]
BACKGROUND_FILES_S2 = [
    "szenario2.png",
    "szenario2_1.png",
]
BACKGROUND_FILES_S3 = [
    "szenario3.png",
    "szenario3_1.png",
]

# Szenario 3: Armeen (3 Optionen)
S3_ARMIES = [
    {
        "key": "Sturmtrupp",
        "soldiers": 35,
        "firepower": 3,
        "desc": "Aggressiv, hohe Feuerkraft, weniger Mannstärke.",
    },
    {
        "key": "Infanterie",
        "soldiers": 50,
        "firepower": 2,
        "desc": "Ausgewogen: solide Mannstärke und Feuerkraft.",
    },
    {
        "key": "Miliz",
        "soldiers": 70,
        "firepower": 1,
        "desc": "Viele Soldaten, aber geringe Feuerkraft.",
    },
]

st.set_page_config(page_title="Zugspiel", layout="wide")


# ============================================================
# UI: Background + Styles (base64, cached)
# ============================================================
@st.cache_data(show_spinner=False)
def _b64_of_image(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode()


def set_background_and_ui(image_path: str):
    encoded = _b64_of_image(image_path)
    if not encoded:
        st.markdown(
            """
            <style>
            .stApp { background: #111; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        .glass {{
            background: rgba(255,255,255,0.82);
            padding: 1rem 1.2rem;
            border-radius: 14px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.15);
        }}

        .mini-label {{
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}

        .nameplate {{
            background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(230,230,230,0.95));
            border: 1px solid rgba(0,0,0,0.25);
            border-radius: 10px;
            padding: 0.55rem 0.75rem;
            font-size: 1.05rem;
            font-weight: 800;
            text-align: center;
            box-shadow: inset 0 1px 2px rgba(255,255,255,0.6),
                        0 2px 6px rgba(0,0,0,0.2);
            letter-spacing: 0.02em;
        }}

        .stTextArea textarea {{
            background: rgba(255,255,255,0.96) !important;
        }}
        .stTextArea textarea:focus {{
            background: rgba(255,255,255,0.98) !important;
        }}

        .stSelectbox [data-baseweb="select"] > div {{
            background: rgba(255,255,255,0.96) !important;
        }}

        .stButton > button {{
            background: rgba(255,255,255,0.96) !important;
            border: 1px solid rgba(0,0,0,0.18) !important;
        }}
        .stButton > button:hover {{
            background: rgba(255,255,255,0.99) !important;
        }}
        .stButton > button:active,
        .stButton > button:focus {{
            background: rgba(255,255,255,0.99) !important;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(0,0,0,0.12) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Helpers
# ============================================================
def plural(n: int, singular: str, plural_form: str | None = None) -> str:
    if n == 1:
        return singular
    return plural_form if plural_form is not None else singular + "e"


def deine_schuetzen_phrase(n: int) -> str:
    return "deines Schützen" if n == 1 else "deiner Schützen"


def append_log(line: str):
    st.session_state.log.append(line)
    if len(st.session_state.log) > MAX_LOG_LINES:
        st.session_state.log = st.session_state.log[-MAX_LOG_LINES:]


def available_backgrounds_for(scenario: str) -> list[str]:
    if scenario == "Szenario 1":
        files = BACKGROUND_FILES_S1
    elif scenario == "Szenario 2":
        files = BACKGROUND_FILES_S2
    else:
        files = BACKGROUND_FILES_S3

    avail = [f for f in files if Path(f).exists()]
    return avail if avail else files


# ============================================================
# State Init
# ============================================================
def ensure_globals():
    if "page" not in st.session_state:
        st.session_state.page = "start"  # start | game | explanation_s1 | explanation_s2 | army_select_s3

    if "current_scenario" not in st.session_state:
        st.session_state.current_scenario = "Szenario 2"

    # Unlock Counter pro Szenario
    if "games_played_s1" not in st.session_state:
        st.session_state.games_played_s1 = 0
    if "games_played_s2" not in st.session_state:
        st.session_state.games_played_s2 = 0
    if "games_played_s3" not in st.session_state:
        st.session_state.games_played_s3 = 0

    if "explanation_text_s1" not in st.session_state:
        st.session_state.explanation_text_s1 = ""
    if "explanation_text_s2" not in st.session_state:
        st.session_state.explanation_text_s2 = ""
    # (für Szenario 3 noch keine Erklärung angefragt – kann später ergänzt werden)

    if "player_name" not in st.session_state:
        st.session_state.player_name = "Dein Zug"
    if "enemy_name" not in st.session_state:
        st.session_state.enemy_name = "Feind"

    if "bg_file" not in st.session_state:
        st.session_state.bg_file = START_BACKGROUND

    # Szenario 3: Army Selection
    if "s3_army_key" not in st.session_state:
        st.session_state.s3_army_key = None
    if "s3_army_soldiers" not in st.session_state:
        st.session_state.s3_army_soldiers = None
    if "s3_army_firepower" not in st.session_state:
        st.session_state.s3_army_firepower = None


def init_match_for(scenario: str):
    st.session_state.current_scenario = scenario

    # Szenario 3: erst Armee wählen, bevor Match init
    if scenario == "Szenario 3" and not st.session_state.s3_army_key:
        st.session_state.page = "army_select_s3"
        bgs = available_backgrounds_for("Szenario 3")
        st.session_state.bg_file = bgs[0] if bgs else START_BACKGROUND
        return

    st.session_state.running = False
    st.session_state.game_over = False
    st.session_state.round = 0

    st.session_state.player_cover = 0

    # Player Start abhängig vom Szenario
    if scenario == "Szenario 3":
        st.session_state.player_shooters = int(st.session_state.s3_army_soldiers or N_PLAYER_START)
    else:
        st.session_state.player_shooters = N_PLAYER_START

    if scenario == "Szenario 3":
        st.session_state.enemy_shooters = S3_ENEMY_SOLDIERS
    else:
        st.session_state.enemy_shooters = M_ENEMY_START


    st.session_state.winner = None
    st.session_state.log = []

    bgs = available_backgrounds_for(scenario)
    st.session_state.bg_file = bgs[0] if bgs else START_BACKGROUND


# ============================================================
# Combat
# ============================================================
def simulate_one_round_s2(player_shooters_target: int):
    player_total = st.session_state.player_cover + st.session_state.player_shooters

    shooters = max(0, min(player_shooters_target, player_total))
    cover = player_total - shooters
    st.session_state.player_cover = cover
    st.session_state.player_shooters = shooters

    # -------- FIGHT RESULT (S2) --------
    kills_on_enemy = min(
        sum(1 for _ in range(shooters) if random.random() < HIT_CHANCE_S2),
        st.session_state.enemy_shooters,
    )

    enemy_shooters = st.session_state.enemy_shooters
    kills_on_player = min(
        sum(1 for _ in range(enemy_shooters) if random.random() < HIT_CHANCE_S2),
        st.session_state.player_shooters,
    )
    # ----------------------------------

    st.session_state.enemy_shooters -= kills_on_enemy
    st.session_state.player_shooters -= kills_on_player
    st.session_state.round += 1

    p_name = st.session_state.player_name
    e_name = st.session_state.enemy_name
    player_left = st.session_state.player_cover + st.session_state.player_shooters
    enemy_left = max(0, st.session_state.enemy_shooters)

    append_log(
        f"Runde {st.session_state.round}: "
        f"{p_name} schaltet {kills_on_enemy} {plural(kills_on_enemy, 'Gegner')} aus, "
        f"{e_name} schaltet {kills_on_player} {deine_schuetzen_phrase(kills_on_player)} aus. "
        f"Stand: {p_name} = {player_left}, {e_name} = {enemy_left}"
    )

    if st.session_state.enemy_shooters <= 0 or player_left <= 0:
        st.session_state.game_over = True
        st.session_state.running = False
        st.session_state.games_played_s2 += 1

        if player_left > 0 and st.session_state.enemy_shooters <= 0:
            st.session_state.winner = p_name
        elif st.session_state.enemy_shooters > 0 and player_left <= 0:
            st.session_state.winner = e_name
        else:
            st.session_state.winner = "Unentschieden"

        append_log(f"Spielende: Gewinner ist {st.session_state.winner}.")


def simulate_one_round_s1(player_shooters_target: int):
    player_total = st.session_state.player_cover + st.session_state.player_shooters

    shooters = max(0, min(player_shooters_target, player_total))
    cover = player_total - shooters
    st.session_state.player_cover = cover
    st.session_state.player_shooters = shooters

    enemy_exposed = max(0, st.session_state.enemy_shooters)
    p_hit_player = min(1.0, enemy_exposed / max(1, CROSS_SECTION_N_S1))

    # -------- FIGHT RESULT (S1) --------
    kills_on_enemy = min(
        sum(1 for _ in range(shooters) if random.random() < p_hit_player),
        st.session_state.enemy_shooters,
    )

    player_exposed = max(0, st.session_state.player_shooters)
    p_hit_enemy = min(1.0, player_exposed / max(1, CROSS_SECTION_N_S1))

    enemy_shooters = st.session_state.enemy_shooters
    kills_on_player = min(
        sum(1 for _ in range(enemy_shooters) if random.random() < p_hit_enemy),
        st.session_state.player_shooters,
    )
    # ----------------------------------

    st.session_state.enemy_shooters -= kills_on_enemy
    st.session_state.player_shooters -= kills_on_player
    st.session_state.round += 1

    p_name = st.session_state.player_name
    e_name = st.session_state.enemy_name
    player_left = st.session_state.player_cover + st.session_state.player_shooters
    enemy_left = max(0, st.session_state.enemy_shooters)

    append_log(
        f"Runde {st.session_state.round}: "
        f"{p_name} schaltet {kills_on_enemy} {plural(kills_on_enemy, 'Gegner')} aus, "
        f"{e_name} schaltet {kills_on_player} {deine_schuetzen_phrase(kills_on_player)} aus. "
        f"Stand: {p_name} = {player_left}, {e_name} = {enemy_left}"
    )

    if st.session_state.enemy_shooters <= 0 or player_left <= 0:
        st.session_state.game_over = True
        st.session_state.running = False
        st.session_state.games_played_s1 += 1

        if player_left > 0 and st.session_state.enemy_shooters <= 0:
            st.session_state.winner = p_name
        elif st.session_state.enemy_shooters > 0 and player_left <= 0:
            st.session_state.winner = e_name
        else:
            st.session_state.winner = "Unentschieden"

        append_log(f"Spielende: Gewinner ist {st.session_state.winner}.")


def simulate_one_round_s3(player_shooters_target: int):
    """Szenario 3: wie Szenario 2, aber jeder Soldat schießt firepower-mal."""
    player_total = st.session_state.player_cover + st.session_state.player_shooters

    shooters = max(0, min(player_shooters_target, player_total))
    cover = player_total - shooters
    st.session_state.player_cover = cover
    st.session_state.player_shooters = shooters

    player_firepower = int(st.session_state.s3_army_firepower or 1)
    enemy_firepower = int(S3_ENEMY_FIREPOWER)  # Gegner bleibt "Standard" (kannst du später erweitern)

    # -------- FIGHT RESULT (S3) --------
    # Spieler: shooters * firepower Schüsse
    player_shots = shooters * player_firepower
    kills_on_enemy = min(
        sum(1 for _ in range(player_shots) if random.random() < HIT_CHANCE_S2),
        st.session_state.enemy_shooters,
    )

    # Gegner: enemy_shooters * enemy_firepower Schüsse
    enemy_shooters = st.session_state.enemy_shooters
    enemy_shots = enemy_shooters * enemy_firepower
    kills_on_player = min(
        sum(1 for _ in range(enemy_shots) if random.random() < HIT_CHANCE_S2),
        st.session_state.player_shooters,
    )
    # ----------------------------------

    st.session_state.enemy_shooters -= kills_on_enemy
    st.session_state.player_shooters -= kills_on_player
    st.session_state.round += 1

    p_name = st.session_state.player_name
    e_name = st.session_state.enemy_name
    player_left = st.session_state.player_cover + st.session_state.player_shooters
    enemy_left = max(0, st.session_state.enemy_shooters)

    append_log(
        f"Runde {st.session_state.round}: "
        f"{p_name} (FP {player_firepower}) schaltet {kills_on_enemy} {plural(kills_on_enemy, 'Gegner')} aus, "
        f"{e_name} schaltet {kills_on_player} {deine_schuetzen_phrase(kills_on_player)} aus. "
        f"Stand: {p_name} = {player_left}, {e_name} = {enemy_left}"
    )

    if st.session_state.enemy_shooters <= 0 or player_left <= 0:
        st.session_state.game_over = True
        st.session_state.running = False
        st.session_state.games_played_s3 += 1

        if player_left > 0 and st.session_state.enemy_shooters <= 0:
            st.session_state.winner = p_name
        elif st.session_state.enemy_shooters > 0 and player_left <= 0:
            st.session_state.winner = e_name
        else:
            st.session_state.winner = "Unentschieden"

        append_log(f"Spielende: Gewinner ist {st.session_state.winner}.")


# ============================================================
# BOOTSTRAP
# ============================================================
ensure_globals()

# ============================================================
# SIDEBAR: Szenario wechseln
# ============================================================
st.sidebar.title("Navigation")

scenario_sidebar = st.sidebar.selectbox(
    "Szenario wechseln:",
    ["Szenario 1", "Szenario 2", "Szenario 3"],
    index=["Szenario 1", "Szenario 2", "Szenario 3"].index(st.session_state.current_scenario)
)

if st.sidebar.button("Szenario laden", use_container_width=True):
    init_match_for(scenario_sidebar)
    # init_match_for kann bei Szenario 3 auf army_select_s3 routen
    if st.session_state.page != "army_select_s3":
        st.session_state.page = "game"
    st.rerun()

if st.sidebar.button("Startseite", use_container_width=True):
    st.session_state.page = "start"
    st.session_state.bg_file = START_BACKGROUND
    st.rerun()


# ============================================================
# ROUTING: START PAGE
# ============================================================
if st.session_state.page == "start":
    set_background_and_ui(START_BACKGROUND)

    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("## 🚆 Zugspiel – Startseite")

    st.write(
        "Du bist der **Capitän** und führst deinen Zug durch ein Gefecht.\n\n"
        "Du entscheidest live, wie viele Soldaten **in Deckung** gehen und wie viele "
        "**das Feuer erwidern**.\n\n"
        "Wähle ein Szenario, um zu beginnen:"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("▶ Szenario 1", use_container_width=True):
            init_match_for("Szenario 1")
            st.session_state.page = "game"
            st.rerun()
        st.caption("Querschnitt-Modell")

    with c2:
        if st.button("▶ Szenario 2", use_container_width=True):
            init_match_for("Szenario 2")
            st.session_state.page = "game"
            st.rerun()
        st.caption("Fixe Trefferchance")

    with c3:
        if st.button("▶ Szenario 3", use_container_width=True):
            init_match_for("Szenario 3")  # routet ggf. zur Armee-Wahl
            if st.session_state.page != "army_select_s3":
                st.session_state.page = "game"
            st.rerun()
        st.caption("Armee-Wahl + Firepower")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ============================================================
# ROUTING: Szenario 3 – Armee wählen
# ============================================================
if st.session_state.page == "army_select_s3":
    # Hintergrund S3
    bgs = available_backgrounds_for("Szenario 3")
    set_background_and_ui(bgs[0] if bgs else START_BACKGROUND)

    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("## Szenario 3 – Wähle deine Armee")

    options = [a["key"] for a in S3_ARMIES]
    choice = st.selectbox("Armee", options, index=0)

    chosen = next(a for a in S3_ARMIES if a["key"] == choice)
    st.markdown(f"**Beschreibung:** {chosen['desc']}")
    st.markdown(f"**Soldaten:** {chosen['soldiers']}")
    st.markdown(f"**Firepower:** {chosen['firepower']} (Schüsse pro Soldat pro Runde)")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Armee wählen & starten", use_container_width=True):
            st.session_state.s3_army_key = chosen["key"]
            st.session_state.s3_army_soldiers = chosen["soldiers"]
            st.session_state.s3_army_firepower = chosen["firepower"]

            # Match jetzt initialisieren
            init_match_for("Szenario 3")
            st.session_state.page = "game"
            st.rerun()

    with c2:
        if st.button("Zurück zur Startseite", use_container_width=True):
            st.session_state.page = "start"
            st.session_state.bg_file = START_BACKGROUND
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ============================================================
# Ab hier: GAME / EXPLANATION
# ============================================================
scenario = st.session_state.current_scenario

# Hintergrund immer setzen
set_background_and_ui(st.session_state.bg_file)

# ============================================================
# Erklärung-Seiten (1 & 2 wie gehabt)
# ============================================================
if st.session_state.page == "explanation_s1":
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("## Erklärung Szenario 1")

    st.session_state.explanation_text_s1 = st.text_area(
        "Erklärungstext (Szenario 1)",
        value=st.session_state.explanation_text_s1,
        height=420,
    )

    if st.button("Zurück zum Spiel", use_container_width=True):
        st.session_state.page = "game"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.session_state.page == "explanation_s2":
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("## Erklärung Szenario 2")

    st.session_state.explanation_text_s2 = st.text_area(
        "Erklärungstext (Szenario 2)",
        value=st.session_state.explanation_text_s2,
        height=420,
    )

    if st.button("Zurück zum Spiel", use_container_width=True):
        st.session_state.page = "game"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ============================================================
# GAME UI
# ============================================================
player_total_now = st.session_state.player_cover + st.session_state.player_shooters
enemy_total_now = max(0, st.session_state.enemy_shooters)

left, center, right = st.columns([1.15, 1.7, 1.15], vertical_alignment="top")

with left:
    st.markdown('<div class="mini-label">Name (dein Team)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="nameplate">{st.session_state.player_name}</div>', unsafe_allow_html=True)

    st.markdown(f"### Soldaten: **{player_total_now}**")
    # Player-Bar: Startwert abhängig vom Szenario
    if scenario == "Szenario 3":
        start_val = int(st.session_state.s3_army_soldiers or N_PLAYER_START)
    else:
        start_val = N_PLAYER_START
    player_ratio = (player_total_now / start_val) if start_val > 0 else 0.0
    st.progress(min(1.0, max(0.0, player_ratio)))

with right:
    st.markdown('<div class="mini-label">Name (Gegner)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="nameplate">{st.session_state.enemy_name}</div>', unsafe_allow_html=True)

    if st.session_state.game_over:
        st.markdown(f"### Soldaten: **{enemy_total_now}**")
    else:
        st.markdown("### Soldaten: **?**")

    st.caption("")

with center:
    st.markdown(f"## {scenario}")

    if scenario == "Szenario 1":
        st.write(
            "Kampfregel: Trefferchance pro Schütze = **(exponierte Gegner) / n**\n\n"
            f"Querschnitt n = **{CROSS_SECTION_N_S1}**"
        )
    elif scenario == "Szenario 2":
        st.write(f"Kampfregel: Trefferchance pro Schuss = **{int(HIT_CHANCE_S2*100)}%**")
    else:
        fp = int(st.session_state.s3_army_firepower or 1)
        st.write(
            f"Kampfregel: wie Szenario 2, aber jeder Soldat schießt **{fp}×** pro Runde "
            f"(Trefferchance pro Schuss = **{int(HIT_CHANCE_S2*100)}%**)."
        )

    # Slider: WIE VIELE SCHIESSEN
    if player_total_now <= 0 or st.session_state.game_over:
        shooters_target = 0
        st.slider(
            "feuer_slider_dummy",
            min_value=0,
            max_value=1,
            value=0,
            disabled=True,
            label_visibility="collapsed",
        )
        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; margin-top:-8px; font-weight:700;">
                <div>🛡️ In Deckung: 0</div>
                <div>🔥 Erwidern Feuer: 0</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        max_shooters = player_total_now
        current_shooters = min(st.session_state.player_shooters, max_shooters)

        shooters_target = st.slider(
            "feuer_slider",
            min_value=0,
            max_value=max_shooters,
            value=current_shooters,
            label_visibility="collapsed",
        )

        cover_now = player_total_now - shooters_target
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; margin-top:-8px; font-weight:700;">
                <div>🛡️ In Deckung: {cover_now}</div>
                <div>🔥 Erwidern Feuer: {shooters_target}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Buttons
    b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 1, 1])


    with b1:
        start_disabled = st.session_state.running or st.session_state.game_over or (player_total_now <= 0)
        if st.button("Start", disabled=start_disabled, use_container_width=True):
            st.session_state.running = True
            append_log("Start gedrückt – das Gefecht beginnt.")

    with b2:
        if st.button("Pause", disabled=(not st.session_state.running), use_container_width=True):
            st.session_state.running = False
            append_log("Pause – das Gefecht ist angehalten.")

    with b3:
        if st.session_state.game_over:
            if st.button("Restart", use_container_width=True):
                # Bei Szenario 3 bleibt Armee gewählt; wer neu wählen will, geht über Sidebar/Startseite
                init_match_for(scenario)
                st.session_state.page = "game"
                st.rerun()
        else:
            st.button("Restart", disabled=True, use_container_width=True)

    with b4:
        if scenario == "Szenario 1":
            played = st.session_state.games_played_s1
            unlocked = played >= UNLOCK_EXPLANATION_AFTER_GAMES
            label = "Erklärung" if unlocked else f"Erklärung ({played}/{UNLOCK_EXPLANATION_AFTER_GAMES})"
            if st.button(label, disabled=not unlocked, use_container_width=True):
                st.session_state.page = "explanation_s1"
                st.rerun()
        elif scenario == "Szenario 2":
            played = st.session_state.games_played_s2
            unlocked = played >= UNLOCK_EXPLANATION_AFTER_GAMES
            label = "Erklärung" if unlocked else f"Erklärung ({played}/{UNLOCK_EXPLANATION_AFTER_GAMES})"
            if st.button(label, disabled=not unlocked, use_container_width=True):
                st.session_state.page = "explanation_s2"
                st.rerun()
        else:
            # Szenario 3 Erklärung derzeit nicht gefordert
            st.button("Erklärung", disabled=True, use_container_width=True)
    with b5:
        if scenario == "Szenario 3":
            if st.button("Armee neu wählen", use_container_width=True):
                # Match stoppen & zur Armee-Auswahl
                st.session_state.running = False
                st.session_state.game_over = False
                st.session_state.page = "army_select_s3"
                st.rerun()
        else:
            st.button("Armee neu wählen", disabled=True, use_container_width=True)

    # Statuszeile
    st.markdown(
        f"""
        <div style="display:flex; gap:32px; font-size:16px; font-weight:700; margin-top:8px;">
            <div>Runde: {st.session_state.round}</div>
            <div>In Deckung: {st.session_state.player_cover}</div>
            <div>Schießen: {st.session_state.player_shooters}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Ergebnis
    if st.session_state.game_over:
        p_left = st.session_state.player_cover + st.session_state.player_shooters
        e_left = max(0, st.session_state.enemy_shooters)
        st.success(f"**Spiel beendet!** Gewinner: **{st.session_state.winner}**")
        st.write(f"Überlebt – {st.session_state.player_name}: **{p_left}**, {st.session_state.enemy_name}: **{e_left}**")


# Log-Feed (zentriert)
#c_left, c_mid, c_right = st.columns([1, 2, 1])
#with c_mid:
    st.markdown("### Log-Feed")
    if st.session_state.log:
        st.text("\n".join(reversed(st.session_state.log[-80:])))
    else:
        st.caption("Noch keine Ereignisse.")


# ============================================================
# Game-Loop: Tick
# ============================================================
if st.session_state.running and not st.session_state.game_over:
    bgs = available_backgrounds_for(scenario)
    if bgs:
        if len(bgs) > 1:
            next_bg = random.choice(bgs)
            if next_bg == st.session_state.bg_file:
                next_bg = random.choice(bgs)
            st.session_state.bg_file = next_bg
        else:
            st.session_state.bg_file = bgs[0]

    if scenario == "Szenario 1":
        simulate_one_round_s1(shooters_target)
    elif scenario == "Szenario 2":
        simulate_one_round_s2(shooters_target)
    else:
        simulate_one_round_s3(shooters_target)

    time.sleep(TICK_SECONDS)
    st.rerun()
