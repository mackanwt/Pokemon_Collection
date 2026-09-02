import streamlit as st
import pandas as pd
import json
import requests
import base64
import uuid
from typing import List, Dict, Any, Tuple

# --- KONFIGURATION ---
st.set_page_config(page_title="Min Pokémon-samling", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
DATA_FILE_PATH = "pokemon_collection_data.json"

SET_FILES = [
    "pokemon_sets_japanese_part1.json",
    "pokemon_sets_japanese_part2.json",
    "pokemon_sets_english.json",
    "pokemon_sets_egna.json"
]

DEFAULT_SETS = [
    {"SetBet": "BS", "SetName": "Base Set", "Språk": "ENG", "Total": 102},
    {"SetBet": "MEW", "SetName": "151", "Språk": "ENG", "Total": 165},
    {"SetBet": "OBF", "SetName": "Obsidian Flames", "Språk": "ENG", "Total": 197}
]

# --- SÄKER GITHUB-FUNKTION ---
def github_load_file(file_path: str, default_data: Any) -> Any:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            if not content.strip():
                return default_data
            return json.loads(content)
        except Exception as e:
            st.error(f"⚠️ JSON-fel i filen **{file_path}**: {e}")
            return default_data
    return default_data

def github_save_file(file_path: str, content: Any, commit_message: str) -> Tuple[bool, str]:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    sha = None
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()['sha']
        
    encoded_content = base64.b64encode(json.dumps(content, indent=4).encode('utf-8')).decode('utf-8')
    data = {"message": commit_message, "content": encoded_content}
    if sha:
        data["sha"] = sha
        
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        return True, "Sparat"
    return False, response.text

# --- VÄXELKURS ---
@st.cache_data(ttl=3600)
def fetch_eur_to_sek_rate() -> float:
    try:
        url = "https://api.exchangerate-api.com/v4/latest/EUR"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return float(resp.json().get("rates", {}).get("SEK", 11.50))
    except Exception:
        pass
    return 11.50

eur_to_sek = fetch_eur_to_sek_rate()

def generate_google_cardmarket_url(name, setnr, setname):
    if not name:
        return ""
    q = f"{name} {setnr} {setname} site:cardmarket.com".strip()
    return f"https://www.google.com/search?q={q.replace(' ', '+')}"

# --- LADDA SAMLING OCH NAMN SEPARAT ---
if "app_data" not in st.session_state or st.session_state["app_data"] is None:
    loaded_data = github_load_file(DATA_FILE_PATH, {"collection": [], "custom_names": []})
    if not isinstance(loaded_data, dict) or "collection" not in loaded_data:
        loaded_data = {"collection": [], "custom_names": []}
    st.session_state["app_data"] = loaded_data

app_data = st.session_state["app_data"]

if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 1

# --- LADDA SET-FILER ---
if "sets_data" not in st.session_state or st.session_state["sets_data"] is None:
    combined_sets = []
    seen_keys = set()
    
    for file_path in SET_FILES:
        data = github_load_file(file_path, [])
        
        items_list = []
        if isinstance(data, list):
            items_list = data
        elif isinstance(data, dict):
            for k in ["sets", "data", "results", "items"]:
                if k in data and isinstance(data[k], list):
                    items_list = data[k]
                    break
            if not items_list:
                items_list = [val for val in data.values() if isinstance(val, dict)]

        for item in items_list:
            if not isinstance(item, dict):
                continue
            
            set_bet = str(item.get("SetBet") or item.get("ptcgoCode") or item.get("id") or "").strip()
            set_name = str(item.get("SetName") or item.get("name") or "").strip()
            
            raw_lang = str(item.get("Language") or item.get("language") or item.get("Språk") or "ENG").strip().upper()
            if "JAPAN" in raw_lang or raw_lang in ["JP", "JPN"]:
                lang = "JPN"
            else:
                lang = raw_lang[:3]
            
            raw_total = item.get("TotalCards") or item.get("printedTotal") or item.get("total") or item.get("Maxantal kort") or 0
            try:
                total_cards = int(str(raw_total).strip())
            except ValueError:
                total_cards = 0

            unique_key = f"{set_bet}_{lang}"
            if set_bet and unique_key not in seen_keys:
                seen_keys.add(unique_key)
                
                img_dict = item.get("images", {})
                img_url = ""
                if isinstance(img_dict, dict):
                    img_url = img_dict.get("small", "") or img_dict.get("logo", "")
                elif isinstance(img_dict, str):
                    img_url = img_dict

                normalized_item = {
                    "SetBet": set_bet,
                    "SetName": set_name,
                    "Språk": lang,
                    "Total": total_cards,
                    "images": img_url
                }
                combined_sets.append(normalized_item)

    if not combined_sets:
        combined_sets = DEFAULT_SETS

    st.session_state["sets_data"] = combined_sets

sets_db = st.session_state["sets_data"]

# --- TABBAR ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Samling", "⚡ Snabb-registrering", "⚙️ Namn-inställningar", "📁 Set-databas"])

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
            if st.button("🔄 Uppdatera", help="Hämta senast gällande växelkurs och ladda om data"):
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
                
                def clean_num(val):
                    return str(val).split('/')[0].strip().lstrip('0') if val else ""

                processed_list = []
                for row in raw_edited:
                    c_id = row.get("_id") or str(uuid.uuid4())
                    
                    k_eur = float(row.get("Köpt för (EUR)", 0.0) or 0.0)
                    v_eur = float(row.get("Värde (EUR)", 0.0) or 0.0)
                    s_name = row.get("Engelskt Namn") or row.get("Namn") or ""
                    
                    set_nr_input = str(row.get("Setnr.") or "").strip()
                    set_bet = str(row.get("SetBet.") or "").strip()
                    set_name = str(row.get("Set") or "").strip()
                    img_url = str(row.get("Bild") or "").strip()

                    if set_nr_input and (not set_bet or not set_name):
                        target_num = clean_num(set_nr_input)
                        for s_item in sets_db:
                            db_num = clean_num(s_item.get("Total", ""))
                            if db_num and str(db_num) == target_num:
                                if not set_bet:
                                    set_bet = s_item.get("SetBet", "")
                                if not set_name:
                                    set_name = s_item.get("SetName", "")
                                if not img_url:
                                    img_url = s_item.get("images", "")
                                break

                    clean_card = {
                        "_id": c_id,
                        "Bild": img_url,
                        "Pärmnummer": int(row.get("Pärmnummer", 0) or 0),
                        "Språk": row.get("Språk", "ENG"),
                        "Namn": row.get("Namn", ""),
                        "Engelskt Namn": s_name,
                        "Setnr.": set_nr_input,
                        "SetBet.": set_bet,
                        "Set": set_name,
                        "Övrigt": row.get("Övrigt", "Normal"),
                        "Skick": row.get("Skick", "NM"),
                        "Köpt för (EUR)": k_eur,
                        "Köpt för (SEK)": round(k_eur * eur_to_sek, 2),
                        "Värde (EUR)": v_eur,
                        "Värde idag (SEK)": round(v_eur * eur_to_sek, 2),
                        "Google Sök": generate_google_cardmarket_url(s_name, set_nr_input, set_name),
                        "Egen Cardmarket Länk": str(row.get("Egen Cardmarket Länk") or "").strip()
                    }
                    processed_list.append(clean_card)

                processed_list.sort(key=lambda x: int(x.get("Pärmnummer", 0)))
                for seq_nr, card in enumerate(processed_list, start=1):
                    card["Pärmnummer"] = seq_nr

                app_data["collection"] = processed_list
                save_payload = {"collection": processed_list, "custom_names": app_data.get("custom_names", [])}
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

# --- FLIK 2: SNABB-REGISTRERING ---
with tab2:
    st.subheader("⚡ Snabb-registrering")
    st.caption("Välj språk, namn och setnummer för att hämta rätt set automatiskt.")

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

    clean_num_str = reg_setnr_raw.split('/')[0].strip().lstrip('0')
    card_number = int(clean_num_str) if clean_num_str.isdigit() else None

    matching_sets = []
    if card_number is not None:
        for s_item in sets_db:
            s_lang = s_item.get("Språk", "ENG")
            total_cards = s_item.get("Total", 0)
            
            if s_lang == reg_language.upper() and total_cards >= card_number:
                matching_sets.append(s_item)

    selected_set = None
    if matching_sets:
        set_options = {
            f"{s.get('SetName')} ({s.get('SetBet')}) — Total: {s.get('Total')} kort": s
            for s in matching_sets
        }
        chosen_label = st.selectbox("Välj matchande Set:", options=list(set_options.keys()))
        selected_set = set_options[chosen_label]
    elif reg_setnr_raw:
        st.warning(f"Hittade inga {reg_language}-set som har minst {card_number} kort. Kontrollera numret eller språket.")

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
                set_bet = selected_set.get("SetBet", "")
                set_name = selected_set.get("SetName", "")
                img_url = selected_set.get("images", "")

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
    st.subheader("⚙️ Hantera sparade Pokémon-namn")
    st.caption("Lägg till eller ta bort namn från listan.")

    current_names = app_data.get("custom_names", [])
    
    new_custom_name = st.text_input("Lägg till nytt Pokémon-namn")
    if st.button("Lägg till namn"):
        if new_custom_name and new_custom_name not in current_names:
            current_names.append(new_custom_name.strip())
            current_names.sort()
            app_data["custom_names"] = current_names
            save_payload = {"collection": app_data.get("collection", []), "custom_names": current_names}
            success, msg = github_save_file(DATA_FILE_PATH, save_payload, f"Lade till namn: {new_custom_name}")
            if success:
                st.session_state["app_data"] = None
                st.success(f"Namnet '{new_custom_name}' lades till!")
                st.rerun()

    st.write("### Sparade namn:")
    if current_names:
        for name in list(current_names):
            col_name, col_btn = st.columns([4, 1])
            col_name.write(f"- {name}")
            if col_btn.button("Ta bort", key=f"del_name_{name}"):
                current_names.remove(name)
                app_data["custom_names"] = current_names
                save_payload = {"collection": app_data.get("collection", []), "custom_names": current_names}
                success, msg = github_save_file(DATA_FILE_PATH, save_payload, f"Tog bort namn: {name}")
                if success:
                    st.session_state["app_data"] = None
                    st.rerun()
    else:
        st.info("Inga sparade namn tillagda ännu.")

# --- FLIK 4: SET-DATABAS ---
with tab4:
    st.subheader("📁 Tillgängliga Set i Databasen")
    st.caption("Filtrera och inspektera inlästa set per språk.")

    db_lang_filter = st.selectbox("Välj språk att visa:", ["Alla", "ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], key="db_lang_filter")

    if sets_db:
        sets_df = pd.DataFrame(sets_db)
        if "images" in sets_df.columns:
            sets_df = sets_df.drop(columns=["images"])
            
        if db_lang_filter != "Alla" and "Språk" in sets_df.columns:
            sets_df = sets_df[sets_df["Språk"] == db_lang_filter]
            
        st.dataframe(sets_df, use_container_width=True, hide_index=True)
    else:
        st.info("Inga set hittades.")
