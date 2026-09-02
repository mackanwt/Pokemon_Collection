import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import date
import urllib.parse
import re
import uuid

# --- 0. PAGE-KONFIGURATION ---
st.set_page_config(
    page_title="Pokémon Samling", 
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- VALUTAKURS-FUNKTION ---
@st.cache_data(ttl=86400)
def fetch_eur_to_sek_rate():
    try:
        url = "https://open.er-api.com/v6/latest/EUR"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            rate = res.json().get("rates", {}).get("SEK")
            if rate:
                return round(float(rate), 4)
    except Exception:
        pass
    return 11.50

# --- LOKAL SET-DATABAS ---
# Struktur: (SetBet, Fullständigt Namn, Språk, Totalt_antal_kort)
ALL_SETS = [
    # JAPANSKA SET (Sun & Moon)
    ("SM1S", "Collection Sun", "JPN", "060"),
    ("SM1M", "Collection Moon", "JPN", "060"),
    ("SM2K", "Islands Await You", "JPN", "050"),
    ("SM2L", "Alolan Moonlight", "JPN", "050"),
    ("SM3H", "To Have Seen the Battle Rainbow", "JPN", "051"),
    ("SM3N", "Darkness that Consumes Light", "JPN", "051"),
    ("SM4A", "Ultradimensional Beasts", "JPN", "050"),
    ("SM4S", "Solgaleo-GX & Lunala-GX Deck", "JPN", "050"),
    ("SM4+", "GX Battle Boost", "JPN", "114"),
    ("SM8B", "Ultra Shiny GX", "JPN", "150"),
    ("SM12A", "Tag All Stars", "JPN", "173"),
    
    # JAPANSKA SET (Sword & Shield)
    ("S12A", "VSTAR Universe", "JPN", "172"),
    ("S11A", "Incandescent Arcana", "JPN", "068"),
    ("S10B", "Pokémon GO", "JPN", "071"),
    
    # JAPANSKA SET (Scarlet & Violet)
    ("SV1S", "Scarlet ex", "JPN", "078"),
    ("SV1V", "Violet ex", "JPN", "078"),
    ("SV2D", "Clay Burst", "JPN", "071"),
    ("SV2P", "Snow Hazard", "JPN", "071"),
    ("SV3", "Ruler of the Black Flame", "JPN", "108"),
    ("SV3A", "Raging Surf", "JPN", "062"),
    ("SV4A", "Shiny Treasure ex", "JPN", "190"),
    ("SV5A", "Crimson Haze", "JPN", "066"),
    ("SV0A", "Battle Academy", "JPN", "066"),

    # ENGELSKA SET (WOTC Klassiker)
    ("BS", "Base Set", "ENG", "102"),
    ("JU", "Jungle", "ENG", "064"),
    ("FO", "Fossil", "ENG", "062"),
    ("B2", "Base Set 2", "ENG", "130"),
    ("TR", "Team Rocket", "ENG", "082"),
    ("GH", "Gym Heroes", "ENG", "132"),
    ("GC", "Gym Challenge", "ENG", "132"),
    
    # ENGELSKA SET (Moderna)
    ("CIN", "Crimson Invasion", "ENG", "111"),
    ("SUM", "Sun & Moon Base", "ENG", "149"),
    ("GRI", "Guardians Rising", "ENG", "145"),
    ("BUS", "Burning Shadows", "ENG", "147"),
    ("SSH", "Sword & Shield Base", "ENG", "202"),
    ("SVI", "Scarlet & Violet Base", "ENG", "198"),
    ("PAL", "Paldea Evolved", "ENG", "279"),
    ("OBF", "Obsidian Flames", "ENG", "230"),
    ("SV3", "Obsidian Flames", "ENG", "230"),
    ("MEW", "151", "ENG", "207"),
    ("PAR", "Paradox Rift", "ENG", "266"),
    ("PAF", "Paldean Fates", "ENG", "245"),
    ("TEF", "Temporal Forces", "ENG", "218"),
    ("TWM", "Twilight Masquerade", "ENG", "226"),
    ("SFA", "Shrouded Fable", "ENG", "099"),
    ("SCR", "Stellar Crown", "ENG", "175")
]

DEFAULT_POKEMON_NAMES = [
    "Alolan Raichu", "Pikachu", "Charizard", "Blastoise", "Venusaur", 
    "Gengar", "Mewtwo", "Mew", "Rayquaza", "Umbreon", "Espeon", "Lugia"
]

def search_sets(input_text, selected_lang):
    clean_text = str(input_text).strip().lower().replace(" ", "")
    if not clean_text:
        return "", ""

    # 1. Matchning på exakt SetBet/Kod (t.ex. "sv3", "sm4a")
    for bet, name, lang, total in ALL_SETS:
        if clean_text == bet.lower().replace("+", "plus") or clean_text == bet.lower():
            return bet, name

    # 2. Om inmatningen innehåller totalantal (t.ex. "016/050" eller "/050")
    target_total = clean_text
    if "/" in clean_text:
        target_total = clean_text.split("/")[-1].strip()
    numeric_total = target_total.lstrip("0")

    matches = []
    for bet, name, lang, total in ALL_SETS:
        if lang == selected_lang:
            if total == target_total or (numeric_total and total.lstrip("0") == numeric_total):
                matches.append((bet, name))

    if len(matches) == 1:
        return matches[0][0], matches[0][1]
    elif len(matches) > 1:
        return matches[0][0], matches[0][1] # Väljer första som standard vid krock

    return "", ""

# --- GITHUB INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

def load_data_from_github():
    default_data = {"collection": [], "custom_names": DEFAULT_POKEMON_NAMES}
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return default_data
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(raw_url, headers=headers, params={"t": str(uuid.uuid4())}, timeout=4)
        if res.status_code == 200:
            data = json.loads(res.text)
            if "custom_names" not in data:
                data["custom_names"] = DEFAULT_POKEMON_NAMES
            return data
    except Exception:
        pass
    return default_data

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GITHUB_TOKEN eller GITHUB_REPO saknas i Secrets!"
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    sha = None
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200:
            sha = res.json().get("sha")
    except Exception:
        pass
    
    content_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": "Uppdaterade samlingsdata via Streamlit",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    try:
        put_res = requests.put(url, json=payload, headers=headers, timeout=5)
        if put_res.status_code in [200, 201]:
            return True, "Sparat!"
        else:
            return False, f"GitHub felkod {put_res.status_code}: {put_res.text}"
    except Exception as e:
        return False, f"Kunde inte ansluta till GitHub: {str(e)}"

def fix_existing_collection(collection_list):
    for card in collection_list:
        if "_id" not in card or not card["_id"]:
            card["_id"] = str(uuid.uuid4())
    return collection_list

def generate_google_cardmarket_url(name, number, set_name):
    safe_name = str(name) if name is not None else ""
    clean_name = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf]', '', safe_name).strip()
    query = f"{clean_name} {number or ''} {set_name or ''} cardmarket"
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"

# --- INITIERA SESSION STATE ---
if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 0

if "app_data" not in st.session_state or st.session_state["app_data"] is None:
    st.session_state["app_data"] = load_data_from_github()

app_data = st.session_state["app_data"]
if "collection" not in app_data:
    app_data["collection"] = []
if "custom_names" not in app_data or not app_data["custom_names"]:
    app_data["custom_names"] = DEFAULT_POKEMON_NAMES

app_data["collection"] = fix_existing_collection(app_data["collection"])
eur_to_sek = fetch_eur_to_sek_rate()

# --- LAYOUT & TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Samling", "⚡ Snabb-registrering", "⚙️ Namn-inställningar"])

# --- FLIK 1: SAMLING ---
with tab1:
    col_header, col_rate = st.columns([2, 3])
    with col_header:
        st.subheader("Min Samling")
    with col_rate:
        c_rate_txt, c_rate_btn = st.columns([2, 1])
        with c_rate_txt:
            st.info(f"💱 **Aktuell kurs:** 1 EUR = **{eur_to_sek:.2f} SEK**")
        with c_rate_btn:
            if st.button("🔄 Uppdatera", help="Hämta senast gällande växelkurs"):
                fetch_eur_to_sek_rate.clear()
                st.session_state["app_data"] = None
                st.rerun()

    collection = sorted(app_data.get("collection", []), key=lambda x: int(x.get("Pärmnummer", 0) or 0))
    app_data["collection"] = collection
    
    if collection:
        df = pd.DataFrame(collection)
        
        if "Värde (USD)" in df.columns and "Värde (EUR)" not in df.columns:
            df["Värde (EUR)"] = df["Värde (USD)"]
        
        for col in ["Bild", "Pärmnummer", "Värde (EUR)", "Köpt för (EUR)", "Google Sök", "Egen Cardmarket Länk", "Engelskt Namn", "_id"]:
            if col not in df.columns:
                df[col] = 0.0 if "Värde" in col or "Köpt" in col else ""
        
        df["Bild"] = df["Bild"].fillna("").astype(str)
        df["Värde (EUR)"] = pd.to_numeric(df["Värde (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (EUR)"] = pd.to_numeric(df["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df["Egen Cardmarket Länk"] = df["Egen Cardmarket Länk"].fillna("").astype(str)
        
        df["Köpt för (SEK)"] = (df["Köpt för (EUR)"] * eur_to_sek).round(2)
        df["Värde idag (SEK)"] = (df["Värde (EUR)"] * eur_to_sek).round(2)

        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            edit_mode = st.checkbox("✏️ Aktivera redigeringsläge (Mata in värden & egna länkar)")

        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Värde (EUR)", "Värde idag (SEK)", "Google Sök", "Egen Cardmarket Länk"
        ]

        if not edit_mode:
            display_df = df.copy()

            column_config = {
                "Bild": st.column_config.ImageColumn("Bild", width="small"),
                "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width="small"),
                "Språk": st.column_config.TextColumn("Språk", width="small"),
                "Namn": st.column_config.TextColumn("Namn", width="medium"),
                "Setnr.": st.column_config.TextColumn("Setnr.", width="small"),
                "SetBet.": st.column_config.TextColumn("SetBet.", width="small"),
                "Set": st.column_config.TextColumn("Set", width="medium"),
                "Övrigt": st.column_config.TextColumn("Övrigt", width="small"),
                "Skick": st.column_config.TextColumn("Skick", width="small"),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="€%.2f", width="small"),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="€%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small"),
                "Google Sök": st.column_config.LinkColumn("Sök Cardmarket", display_text="🔍 Google Sök", width="medium"),
                "Egen Cardmarket Länk": st.column_config.LinkColumn("Min Cardmarket Länk", display_text="🔗 Öppna Sida", width="medium")
            }
            st.dataframe(display_df[columns_order], column_config=column_config, use_container_width=True, hide_index=True)
        
        else:
            column_config_edit = {
                "_id": None,
                "Bild": st.column_config.TextColumn("Bild-URL", width="medium"),
                "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width="small", step=1),
                "Språk": st.column_config.SelectboxColumn("Språk", options=["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], width="small"),
                "Namn": st.column_config.TextColumn("Namn", width="medium"),
                "Setnr.": st.column_config.TextColumn("Setnr.", width="small"),
                "SetBet.": st.column_config.TextColumn("SetBet.", width="small"),
                "Set": st.column_config.TextColumn("Set/Base", width="medium"),
                "Övrigt": st.column_config.SelectboxColumn("Övrigt", options=["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], width="small"),
                "Skick": st.column_config.SelectboxColumn("Skick", options=["NM", "EX", "GD", "LP", "PL", "PO"], width="small"),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width="small"),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small", disabled=True),
                "Google Sök": st.column_config.TextColumn("Google Sök URL", disabled=True, width="medium"),
                "Egen Cardmarket Länk": st.column_config.TextColumn("Klistra in Cardmarket URL här", width="large")
            }

            edit_columns = ["_id"] + columns_order
            editor_key = f"collection_editor_v{st.session_state['editor_version']}"

            edited_df = st.data_editor(
                df[edit_columns],
                column_config=column_config_edit,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key=editor_key
            )

            with col_act2:
                if st.button("💾 Spara ändringar", type="primary", use_container_width=True):
                    raw_edited = edited_df.to_dict(orient="records")
                    old_collection = app_data.get("collection", [])
                    old_map = {c["_id"]: int(c.get("Pärmnummer", 0) or 0) for c in old_collection if "_id" in c}
                    
                    existing_ids = set()
                    changed_card_id = None
                    old_nr = None
                    new_nr = None

                    for row in raw_edited:
                        c_id = row.get("_id")
                        if c_id:
                            existing_ids.add(c_id)
                            curr_input_nr = int(row.get("Pärmnummer", 0) or 0)
                            prev_nr = old_map.get(c_id)
                            if prev_nr and curr_input_nr != prev_nr:
                                changed_card_id = c_id
                                old_nr = prev_nr
                                new_nr = curr_input_nr

                    deleted_nrs = [nr for c_id, nr in old_map.items() if c_id not in existing_ids]

                    processed_list = []
                    for row in raw_edited:
                        c_id = row.get("_id")
                        if c_id == changed_card_id:
                            target_nr = new_nr
                        else:
                            target_nr = old_map.get(c_id, int(row.get("Pärmnummer", 0) or 0))
                            if changed_card_id and old_nr and new_nr:
                                if old_nr < new_nr:
                                    if old_nr < target_nr <= new_nr:
                                        target_nr -= 1
                                elif new_nr < old_nr:
                                    if new_nr <= target_nr < old_nr:
                                        target_nr += 1
                            for d_nr in deleted_nrs:
                                if target_nr > d_nr:
                                    target_nr -= 1

                        row["Pärmnummer"] = target_nr
                        row["Egen Cardmarket Länk"] = str(row.get("Egen Cardmarket Länk") or "").strip()
                        k_eur = float(row.get("Köpt för (EUR)", 0.0) or 0.0)
                        v_eur = float(row.get("Värde (EUR)", 0.0) or 0.0)
                        row["Köpt för (SEK)"] = round(k_eur * eur_to_sek, 2)
                        row["Värde idag (SEK)"] = round(v_eur * eur_to_sek, 2)
                        s_name = row.get("Engelskt Namn") or row.get("Namn") or ""
                        row["Google Sök"] = generate_google_cardmarket_url(s_name, row.get("Setnr.", ""), row.get("Set", ""))
                        processed_list.append(row)

                    processed_list.sort(key=lambda x: int(x.get("Pärmnummer", 0)))
                    for seq_nr, card in enumerate(processed_list, start=1):
                        card["Pärmnummer"] = seq_nr

                    app_data["collection"] = processed_list
                    save_payload = {"collection": processed_list, "custom_names": app_data.get("custom_names", DEFAULT_POKEMON_NAMES)}
                    success, msg = save_data_to_github(save_payload)
                    
                    if success:
                        st.session_state["app_data"] = None 
                        st.session_state["editor_version"] += 1
                        st.success("Ändringarna sparades!")
                        st.rerun()
                    else:
                        st.error(f"Kunde inte spara till GitHub: {msg}")

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Totalt antal kort", len(df))
        c2.metric("Totalt värde (SEK)", f"{df['Värde idag (SEK)'].sum():,.2f} kr")
        c3.metric("Total vinst (SEK)", f"{(df['Värde idag (SEK)'].sum() - df['Köpt för (SEK)'].sum()):,.2f} kr")
    else:
        st.info("Samlingen är tom. Gå till fliken 'Snabb-registrering'.")

# --- FLIK 2: DIREKT-REGISTRERING (TABELLFORM) ---
with tab2:
    st.subheader("⚡ Snabb-registrering via direktredigering")
    st.caption("Fyll i raden nedan och tryck på Enter. SetBet och Set-namn beräknas automatiskt utifrån Språk och Setnr.")

    if "new_card_state" not in st.session_state:
        next_parm = len(app_data.get("collection", [])) + 1
        st.session_state["new_card_state"] = pd.DataFrame([{
            "Pärmnummer": next_parm,
            "Språk": "ENG",
            "Namn": app_data["custom_names"][0] if app_data["custom_names"] else "Pikachu",
            "Setnr.": "016/050",
            "SetBet.": "",
            "Set": "",
            "Övrigt": "Normal",
            "Skick": "NM",
            "Köpt för (EUR)": 0.0,
            "Värde (EUR)": 0.0
        }])

    reg_df = st.session_state["new_card_state"]

    curr_lang = reg_df.at[0, "Språk"]
    curr_num = reg_df.at[0, "Setnr."]
    auto_bet, auto_set = search_sets(curr_num, curr_lang)

    reg_df.at[0, "SetBet."] = auto_bet
    reg_df.at[0, "Set"] = auto_set

    reg_config = {
        "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width="small", step=1),
        "Språk": st.column_config.SelectboxColumn("Språk", options=["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], width="small"),
        "Namn": st.column_config.SelectboxColumn("Namn", options=app_data.get("custom_names", DEFAULT_POKEMON_NAMES), width="medium"),
        "Setnr.": st.column_config.TextColumn("Setnr.", width="small"),
        "SetBet.": st.column_config.TextColumn("SetBet.", width="small"),
        "Set": st.column_config.TextColumn("Set", width="medium"),
        "Övrigt": st.column_config.SelectboxColumn("Övrigt", options=["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], width="small"),
        "Skick": st.column_config.SelectboxColumn("Skick", options=["NM", "EX", "GD", "LP", "PL", "PO"], width="small"),
        "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width="small"),
        "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="%.2f", width="small"),
    }

    edited_reg = st.data_editor(
        reg_df,
        column_config=reg_config,
        use_container_width=True,
        hide_index=True,
        key="registration_editor"
    )

    st.session_state["new_card_state"] = edited_reg

    if auto_set:
        st.success(f" Hittade automatisk matchning: **{auto_set}** (`{auto_bet}`)")
    else:
        st.info("💡 Skriv in ett setnummer eller setkod (t.ex. 'SV3' eller '016/050') i cellen 'Setnr.' för att hitta setet.")

    st.divider()

    if st.button("💾 Spara och lägg till kort i samlingen", type="primary", use_container_width=True):
        row_data = edited_reg.to_dict(orient="records")[0]
        
        c_name = str(row_data.get("Namn", "")).strip()
        c_num = str(row_data.get("Setnr.", "")).strip()
        c_set_name = str(row_data.get("Set", "")).strip()
        c_parm = int(row_data.get("Pärmnummer", len(app_data.get("collection", [])) + 1))
        k_eur = float(row_data.get("Köpt för (EUR)", 0.0) or 0.0)
        v_eur = float(row_data.get("Värde (EUR)", 0.0) or 0.0)

        google_url = generate_google_cardmarket_url(c_name, c_num, c_set_name)

        new_entry = {
            "_id": str(uuid.uuid4()),
            "Bild": "",
            "Pärmnummer": c_parm,
            "Språk": row_data.get("Språk", "ENG"),
            "Namn": c_name,
            "Engelskt Namn": c_name,
            "Setnr.": c_num,
            "SetBet.": str(row_data.get("SetBet.", "")).strip(),
            "Set": c_set_name,
            "Övrigt": row_data.get("Övrigt", "Normal"),
            "Skick": row_data.get("Skick", "NM"),
            "Köpt för (EUR)": k_eur,
            "Köpt för (SEK)": round(k_eur * eur_to_sek, 2),
            "Värde (EUR)": v_eur,
            "Värde idag (SEK)": round(v_eur * eur_to_sek, 2),
            "Datum tillagd": date.today().strftime("%Y-%m-%d"),
            "Google Sök": google_url,
            "Egen Cardmarket Länk": ""
        }

        for existing_card in app_data["collection"]:
            if int(existing_card.get("Pärmnummer", 0)) >= c_parm:
                existing_card["Pärmnummer"] = int(existing_card["Pärmnummer"]) + 1

        app_data["collection"].append(new_entry)

        sorted_coll = sorted(app_data["collection"], key=lambda x: int(x.get("Pärmnummer", 0) or 0))
        for idx, card in enumerate(sorted_coll, start=1):
            card["Pärmnummer"] = idx

        save_payload = {"collection": sorted_coll, "custom_names": app_data.get("custom_names", DEFAULT_POKEMON_NAMES)}
        success, msg = save_data_to_github(save_payload)

        if success:
            st.session_state["app_data"] = None
            st.session_state["editor_version"] += 1
            st.session_state["new_card_state"] = pd.DataFrame([{
                "Pärmnummer": len(sorted_coll) + 1,
                "Språk": row_data.get("Språk", "ENG"),
                "Namn": c_name,
                "Setnr.": "",
                "SetBet.": "",
                "Set": "",
                "Övrigt": "Normal",
                "Skick": "NM",
                "Köpt för (EUR)": 0.0,
                "Värde (EUR)": 0.0
            }])
            st.success(f"Lade till {c_name} (#{c_parm})!")
            st.rerun()
        else:
            st.error(f"Kunde inte spara till GitHub: {msg}")

# --- FLIK 3: INSTÄLLNINGAR / NAMN ---
with tab3:
    st.subheader("⚙️ Pokémon-namn i Rullistan")
    st.caption("Hantera listan över namn som ska synas i rullistan när du registrerar nya kort.")

    names_list = app_data.get("custom_names", DEFAULT_POKEMON_NAMES)
    
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        new_name_input = st.text_input("Lägg till nytt Pokémon-namn:", placeholder="T.ex. Lucario")
    with col_add2:
        st.write(" ")
        st.write(" ")
        if st.button("➕ Lägg till namn", use_container_width=True):
            clean_n = new_name_input.strip()
            if clean_n and clean_n not in names_list:
                names_list.append(clean_n)
                names_list.sort()
                app_data["custom_names"] = names_list
                save_payload = {"collection": app_data.get("collection", []), "custom_names": names_list}
                success, msg = save_data_to_github(save_payload)
                if success:
                    st.success(f"Lade till '{clean_n}'!")
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()

    st.markdown("**Befintliga namn i listan:**")
    names_df = pd.DataFrame({"Pokémon Name": names_list})
    edited_names = st.data_editor(
        names_df,
        num_rows="dynamic",
        use_container_width=True,
        key="names_editor"
    )

    if st.button("💾 Spara Namnlista", type="primary"):
        updated_names = [n.strip() for n in edited_names["Pokémon Name"].dropna().tolist() if n.strip()]
        updated_names = sorted(list(set(updated_names)))
        app_data["custom_names"] = updated_names
        save_payload = {"collection": app_data.get("collection", []), "custom_names": updated_names}
        success, msg = save_data_to_github(save_payload)
        if success:
            st.success("Namnlistan uppdaterades!")
            st.rerun()
        else:
            st.error(msg)
