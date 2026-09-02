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

# --- RESERV / DEFAULT-LISTA (Körs endast om filer saknas helt på GitHub) ---
DEFAULT_SETS = [
    {"SetBet": "SV3", "SetName": "Ruler of the Black Flame", "Language": "JPN", "TotalCards": "108", "ReleaseYear": 2023},
    {"SetBet": "OBF", "SetName": "Obsidian Flames", "Language": "ENG", "TotalCards": "230", "ReleaseYear": 2023}
]

DEFAULT_POKEMON_NAMES = [
    "Alolan Raichu", "Pikachu", "Charizard", "Blastoise", "Venusaur", 
    "Gengar", "Mewtwo", "Mew", "Rayquaza", "Umbreon", "Espeon", "Lugia", "Togepi"
]

# --- GITHUB INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
DATA_FILE_PATH = "data.json"

# De 4 nya set-filerna
SET_FILES = [
    "pokemon_sets_japan_part1.json",
    "pokemon_sets_japan_part2.json",
    "pokemon_sets_english.json",
    "pokemon_sets_egna.json"
]
CUSTOM_SETS_FILE_PATH = "pokemon_sets_egna.json"

def github_load_file(file_path, default_content):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return default_content
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(raw_url, headers=headers, params={"t": str(uuid.uuid4())}, timeout=4)
        if res.status_code == 200:
            return json.loads(res.text)
    except Exception:
        pass
    return default_content

def github_save_file(file_path, data_dict, commit_message):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GITHUB_TOKEN eller GITHUB_REPO saknas i Secrets!"
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
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
        "message": commit_message,
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

def search_sets_db(input_text, selected_lang, sets_db):
    clean_text = str(input_text).strip().lower().replace(" ", "")
    if not clean_text:
        return "", ""

    lang_sets = [s for s in sets_db if s.get("Language") == selected_lang]

    # 1. Matchning på exakt SetBet (t.ex. "sv3") inom valt språk
    for s in lang_sets:
        if clean_text == str(s.get("SetBet", "")).lower().replace("+", "plus") or clean_text == str(s.get("SetBet", "")).lower():
            return s.get("SetBet", ""), s.get("SetName", "")

    # 2. Matchning på Totalkort (t.ex. "043/108" -> "108")
    target_total = clean_text
    if "/" in clean_text:
        target_total = clean_text.split("/")[-1].strip()
    numeric_total = target_total.lstrip("0")

    for s in lang_sets:
        tot = str(s.get("TotalCards", "")).strip()
        if tot == target_total or (numeric_total and tot.lstrip("0") == numeric_total):
            return s.get("SetBet", ""), s.get("SetName", "")

    # Fallback: Sök globalt om ej hittat i språk
    for s in sets_db:
        if clean_text == str(s.get("SetBet", "")).lower():
            return s.get("SetBet", ""), s.get("SetName", "")

    return "", ""

# --- INITIERA SESSION STATE ---
if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 0

if "app_data" not in st.session_state or st.session_state["app_data"] is None:
    st.session_state["app_data"] = github_load_file(DATA_FILE_PATH, {"collection": [], "custom_names": []})

if "sets_data" not in st.session_state or st.session_state["sets_data"] is None:
    combined_sets = []
    for file_path in SET_FILES:
        data = github_load_file(file_path, [])
        if isinstance(data, list):
            combined_sets.extend(data)
    
    if not combined_sets:
        combined_sets = DEFAULT_SETS
        
    st.session_state["sets_data"] = combined_sets

app_data = st.session_state["app_data"]
sets_db = st.session_state["sets_data"]

if "collection" not in app_data:
    app_data["collection"] = []
if "custom_names" not in app_data:
    app_data["custom_names"] = []

app_data["collection"] = fix_existing_collection(app_data["collection"])
eur_to_sek = fetch_eur_to_sek_rate()

# --- LAYOUT & TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Samling", "⚡ Snabb-registrering", "⚙️ Namn-inställningar", "🗂️ Set-databas"])

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
                st.session_state["sets_data"] = None
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

        edit_mode = st.checkbox("✏️ Aktivera redigeringsläge (Mata in värden & egna länkar)")

        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Värde (EUR)", "Värde idag (SEK)", "Google Sök", "Egen Cardmarket Länk"
        ]

        if not edit_mode:
            display_df = df.copy()

            column_config = {
                "Bild": st.column_config.ImageColumn("Bild", width=60),
                "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width=60),
                "Språk": st.column_config.TextColumn("Språk", width=60),
                "Namn": st.column_config.TextColumn("Namn", width=150),
                "Setnr.": st.column_config.TextColumn("Setnr.", width=70),
                "SetBet.": st.column_config.TextColumn("SetBet.", width=70),
                "Set": st.column_config.TextColumn("Set", width=160),
                "Övrigt": st.column_config.TextColumn("Övrigt", width=80),
                "Skick": st.column_config.TextColumn("Skick", width=60),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="€%.2f", width=80),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="€%.2f", width=80),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width=90),
                "Google Sök": st.column_config.LinkColumn("Sök Cardmarket", display_text="🔍 Sök", width=100),
                "Egen Cardmarket Länk": st.column_config.LinkColumn("Min Cardmarket Länk", display_text="🔗 Öppna Sida", width=130)
            }
            st.dataframe(display_df[columns_order], column_config=column_config, use_container_width=True, hide_index=True)
        
        else:
            column_config_edit = {
                "_id": None,
                "Bild": st.column_config.TextColumn("Bild-URL", width=100),
                "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width=60, step=1),
                "Språk": st.column_config.SelectboxColumn("Språk", options=["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], width=70),
                "Namn": st.column_config.TextColumn("Namn", width=150),
                "Setnr.": st.column_config.TextColumn("Setnr.", width=70),
                "SetBet.": st.column_config.TextColumn("SetBet.", width=70),
                "Set": st.column_config.TextColumn("Set/Base", width=160),
                "Övrigt": st.column_config.SelectboxColumn("Övrigt", options=["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], width=90),
                "Skick": st.column_config.SelectboxColumn("Skick", options=["NM", "EX", "GD", "LP", "PL", "PO"], width=60),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width=80),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="%.2f", width=80),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width=90, disabled=True),
                "Google Sök": st.column_config.TextColumn("Google Sök URL", disabled=True, width=100),
                "Egen Cardmarket Länk": st.column_config.TextColumn("Klistra in Cardmarket URL här", width=200)
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

            if st.button("💾 Spara ändringar", type="primary", use_container_width=True):
                raw_edited = edited_df.to_dict(orient="records")
                
                processed_list = []
                for row in raw_edited:
                    c_id = row.get("_id") or str(uuid.uuid4())
                    
                    k_eur = float(row.get("Köpt för (EUR)", 0.0) or 0.0)
                    v_eur = float(row.get("Värde (EUR)", 0.0) or 0.0)
                    s_name = row.get("Engelskt Namn") or row.get("Namn") or ""
                    
                    clean_card = {
                        "_id": c_id,
                        "Bild": str(row.get("Bild") or "").strip(),
                        "Pärmnummer": int(row.get("Pärmnummer", 0) or 0),
                        "Språk": row.get("Språk", "ENG"),
                        "Namn": row.get("Namn", ""),
                        "Engelskt Namn": s_name,
                        "Setnr.": str(row.get("Setnr.") or "").strip(),
                        "SetBet.": str(row.get("SetBet.") or "").strip(),
                        "Set": str(row.get("Set") or "").strip(),
                        "Övrigt": row.get("Övrigt", "Normal"),
                        "Skick": row.get("Skick", "NM"),
                        "Köpt för (EUR)": k_eur,
                        "Köpt för (SEK)": round(k_eur * eur_to_sek, 2),
                        "Värde (EUR)": v_eur,
                        "Värde idag (SEK)": round(v_eur * eur_to_sek, 2),
                        "Google Sök": generate_google_cardmarket_url(s_name, row.get("Setnr.", ""), row.get("Set", "")),
                        "Egen Cardmarket Länk": str(row.get("Egen Cardmarket Länk") or "").strip()
                    }
                    processed_list.append(clean_card)

                processed_list.sort(key=lambda x: int(x.get("Pärmnummer", 0)))
                for seq_nr, card in enumerate(processed_list, start=1):
                    card["Pärmnummer"] = seq_nr

                app_data["collection"] = processed_list
                save_payload = {"collection": processed_list, "custom_names": app_data.get("custom_names", [])}
                success, msg = github_save_file(DATA_FILE_PATH, save_payload, "Uppdaterade samling och tog bort rad(er)")
                
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

# --- FLIK 2: DIREKT-REGISTRERING ---
with tab2:
    st.subheader("⚡ Snabb-registrering")
    st.caption("Välj språk, namn och setnummer för att hämta rätt set automatiskt.")

    # 1. Hämta sparade namn till rullistan
    saved_names = app_data.get("custom_names", [])

    c1, c2, c3 = st.columns([1, 2, 2])
    with c1:
        reg_language = st.selectbox("Språk", ["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], index=0)
    with c2:
        if saved_names:
            reg_name = st.selectbox("Pokémon-namn", options=saved_names)
        else:
            reg_name = st.text_input("Pokémon-namn", placeholder="T.ex. Togepi")
    with c3:
        reg_setnr_raw = st.text_input("Setnr.", placeholder="T.ex. 043/108 eller 043")

    # Extrahera enbart siffran från input (t.ex. "043/108" -> 43)
    clean_num_str = reg_setnr_raw.split('/')[0].strip().lstrip('0')
    card_number = int(clean_num_str) if clean_num_str.isdigit() else None

    # Filter-logik för set-databasen
    matching_sets = []
    if card_number is not None:
        for s_item in sets_db:
            total_cards = s_item.get("printedTotal") or s_item.get("total") or 0
            # Om setet har tillräckligt många kort för att innehålla detta nummer
            if total_cards >= card_number:
                matching_sets.append(s_item)

    selected_set = None
    if matching_sets:
        # Skapa alternativ till rullistan: "Set-namn (Kortkod / Totalt antal)"
        set_options = {
            f"{s.get('name')} ({s.get('ptcgoCode', s.get('id', '')).upper()}) — Total: {s.get('printedTotal', s.get('total', '?'))}": s
            for s in matching_sets
        }
        chosen_label = st.selectbox("Välj matchande Set:", options=list(set_options.keys()))
        selected_set = set_options[chosen_label]
    elif reg_setnr_raw:
        st.warning("Hittade inga set som har så många kort. Kontrollera numret eller välj manuellt nedan.")

    # Övriga fält för kortet
    c4, c5, c6, c7 = st.columns(4)
    with c4:
        reg_ovrigt = st.selectbox("Övrigt", ["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"])
    with c5:
        reg_skick = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"])
    with c6:
        reg_kopt = st.number_input("Köpt för (EUR)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
    with c7:
        reg_varde = st.number_input("Värde (EUR)", min_value=0.0, value=0.0, step=0.5, format="%.2f")

    if st.button("➕ Registrera kort i samlingen", type="primary", use_container_width=True):
        if not reg_name:
            st.warning("Du måste fylla i eller välja ett Pokémon-namn.")
        else:
            set_bet = ""
            set_name = ""
            img_url = ""

            if selected_set:
                set_bet = selected_set.get("ptcgoCode") or selected_set.get("id", "").upper()
                set_name = selected_set.get("name", "")
                if "images" in selected_set:
                    img_url = selected_set["images"].get("small", "")

            next_p_nr = len(collection) + 1

            new_card = {
                "_id": str(uuid.uuid4()),
                "Bild": img_url,
                "Pärmnummer": next_p_nr,
                "Språk": reg_language,
                "Namn": reg_name,
                "Engelskt Namn": reg_name,
                "Setnr.": reg_setnr_raw,
                "SetBet.": set_bet,
                "Set": set_name,
                "Övrigt": reg_ovrigt,
                "Skick": reg_skick,
                "Köpt för (EUR)": reg_kopt,
                "Köpt för (SEK)": round(reg_kopt * eur_to_sek, 2),
                "Värde (EUR)": reg_varde,
                "Värde idag (SEK)": round(reg_varde * eur_to_sek, 2),
                "Google Sök": generate_google_cardmarket_url(reg_name, reg_setnr_raw, set_name),
                "Egen Cardmarket Länk": ""
            }

            collection.append(new_card)
            save_payload = {"collection": collection, "custom_names": app_data.get("custom_names", [])}
            success, msg = github_save_file(DATA_FILE_PATH, save_payload, f"Lade till kort: {reg_name}")

            if success:
                st.session_state["app_data"] = None
                st.success(f"Kortet **{reg_name}** ({set_name}) registrerades!")
                st.rerun()
            else:
                st.error(f"Kunde inte spara till GitHub: {msg}")
                
# --- FLIK 3: NAMN-INSTÄLLNINGAR ---
with tab3:
    st.subheader("⚙️ Pokémon-namn i Rullistan")
    st.caption("Hantera listan över namn som ska synas i rullistan när du registrerar nya kort.")

    # Hämtar sparade namn eller tom lista (utan återställning)
    names_list = app_data.get("custom_names", [])
    
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
                success, msg = github_save_file(DATA_FILE_PATH, save_payload, "Uppdaterade namnlista")
                if success:
                    st.session_state["app_data"] = None  # Tvingar cachen att uppdateras från GitHub
                    st.success(f"Lade till '{clean_n}'!")
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()

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
        success, msg = github_save_file(DATA_FILE_PATH, save_payload, "Redigerade namnlista")
        if success:
            st.session_state["app_data"] = None  # Rensar cachen så raderingarna sparas permanent
            st.success("Namnlistan uppdaterades!")
            st.rerun()
        else:
            st.error(msg)
            
# --- FLIK 4: SET-DATABAS ---
with tab4:
    st.subheader("🗂️ Global Set-databas")
    st.caption("Filtrera, redigera och lägg till set. Ändringar du gör här sparas i `pokemon_sets_egna.json` på GitHub.")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_lang = st.selectbox("Filtrera på språk:", ["ALLA", "JPN", "ENG", "SWE", "GER", "FRA", "ITA", "KOR", "SPA", "POR", "ZHT"])
    with col_f2:
        filter_search = st.text_input("Sök i set-namn / kod:", placeholder="T.ex. sv3 eller Ruler")

    sets_df = pd.DataFrame(sets_db)
    
    for c in ["SetBet", "SetName", "Language", "TotalCards", "ReleaseYear"]:
        if c not in sets_df.columns:
            sets_df[c] = ""

    filtered_df = sets_df.copy()
    if filter_lang != "ALLA":
        filtered_df = filtered_df[filtered_df["Language"] == filter_lang]
    if filter_search.strip():
        q = filter_search.strip().lower()
        filtered_df = filtered_df[
            filtered_df["SetBet"].astype(str).str.lower().str.contains(q) | 
            filtered_df["SetName"].astype(str).str.lower().str.contains(q)
        ]

    sets_config = {
        "SetBet": st.column_config.TextColumn("SetBet (Setkod)", width=110),
        "SetName": st.column_config.TextColumn("Set (Fullständigt Namn)", width=220),
        "Language": st.column_config.SelectboxColumn("Språk", options=["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], width=80),
        "TotalCards": st.column_config.TextColumn("Maxantal kort", width=100),
        "ReleaseYear": st.column_config.NumberColumn("Utgivningsår", format="%d", step=1, width=100)
    }

    edited_sets_df = st.data_editor(
        filtered_df,
        column_config=sets_config,
        num_rows="dynamic",
        use_container_width=True,
        key="sets_db_editor"
    )

    if st.button("💾 Spara ändringar i Set-databasen", type="primary"):
        edited_list = edited_sets_df.to_dict(orient="records")
        
        success, msg = github_save_file(CUSTOM_SETS_FILE_PATH, edited_list, "Uppdaterade set-databasen")
        if success:
            st.session_state["sets_data"] = None
            st.success(f"Ändringarna sparades till {CUSTOM_SETS_FILE_PATH}!")
            st.rerun()
        else:
            st.error(msg)
