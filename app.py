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

# --- RESERV / DEFAULT-LISTA (Körs endast om sets.json saknas helt på GitHub) ---
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
SETS_FILE_PATH = "sets.json"

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
    st.session_state["app_data"] = github_load_file(DATA_FILE_PATH, {"collection": [], "custom_names": DEFAULT_POKEMON_NAMES})

if "sets_data" not in st.session_state or st.session_state["sets_data"] is None:
    st.session_state["sets_data"] = github_load_file(SETS_FILE_PATH, DEFAULT_SETS)

app_data = st.session_state["app_data"]
sets_db = st.session_state["sets_data"]

if "collection" not in app_data:
    app_data["collection"] = []
if "custom_names" not in app_data or not app_data["custom_names"]:
    app_data["custom_names"] = DEFAULT_POKEMON_NAMES

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
                    success, msg = github_save_file(DATA_FILE_PATH, save_payload, "Uppdaterade samling")
                    
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
    st.subheader("⚡ Snabb-registrering via direktredigering")
    st.caption("Fyll i raden nedan och tryck Enter. SetBet och Set-namn beräknas automatiskt utifrån Språk och Setnr.")

    if "new_card_state" not in st.session_state:
        next_parm = len(app_data.get("collection", [])) + 1
        st.session_state["new_card_state"] = pd.DataFrame([{
            "Pärmnummer": next_parm,
            "Språk": "ENG",
            "Namn": app_data["custom_names"][0] if app_data["custom_names"] else "Pikachu",
            "Setnr.": "",
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
    auto_bet, auto_set = search_sets_db(curr_num, curr_lang, sets_db)

    reg_df.at[0, "SetBet."] = auto_bet
    reg_df.at[0, "Set"] = auto_set

    reg_config = {
        "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width=60, step=1),
        "Språk": st.column_config.SelectboxColumn("Språk", options=["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], width=70),
        "Namn": st.column_config.SelectboxColumn("Namn", options=app_data.get("custom_names", DEFAULT_POKEMON_NAMES), width=150),
        "Setnr.": st.column_config.TextColumn("Setnr.", width=70),
        "SetBet.": st.column_config.TextColumn("SetBet.", width=70),
        "Set": st.column_config.TextColumn("Set", width=160),
        "Övrigt": st.column_config.SelectboxColumn("Övrigt", options=["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], width=90),
        "Skick": st.column_config.SelectboxColumn("Skick", options=["NM", "EX", "GD", "LP", "PL", "PO"], width=60),
        "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width=80),
        "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="%.2f", width=80),
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
        st.info("💡 Skriv in ett setnummer eller setkod (t.ex. 'SV3' eller '043/108') i 'Setnr.' för att identifiera setet.")

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
        success, msg = github_save_file(DATA_FILE_PATH, save_payload, "Lade till nytt kort")

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

# --- FLIK 3: NAMN-INSTÄLLNINGAR ---
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
                success, msg = github_save_file(DATA_FILE_PATH, save_payload, "Uppdaterade namnlista")
                if success:
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
            st.success("Namnlistan uppdaterades!")
            st.rerun()
        else:
            st.error(msg)

# --- FLIK 4: SET-DATABAS ---
with tab4:
    st.subheader("🗂️ Global Set-databas (`sets.json`)")
    st.caption("Filtrera, redigera och lägg till set. Ändringar du gör här sparas i `sets.json` på GitHub.")

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
        
        merged_db = []
        edited_keys = {(r.get("SetBet"), r.get("Language")) for r in edited_list}
        
        for r in edited_list:
            if r.get("SetBet") and r.get("SetName"):
                merged_db.append(r)
                
        for s in sets_db:
            key = (s.get("SetBet"), s.get("Language"))
            if key not in edited_keys:
                merged_db.append(s)

        success, msg = github_save_file(SETS_FILE_PATH, merged_db, "Uppdaterade sets.json manuellt")
        if success:
            st.session_state["sets_data"] = None
            st.success("Set-databasen sparades till GitHub!")
            st.rerun()
        else:
            st.error(msg)
