import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import date
import urllib.parse
import re

# --- 0. PAGE-KONFIGURATION ---
st.set_page_config(
    page_title="Pokémon Samling", 
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GITHUB CONFIG & INTEGRATION ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = "data.json"

def load_data_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"collection": []}
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(raw_url, headers=headers)
        if res.status_code == 200:
            return json.loads(res.text)
    except Exception:
        pass
    return {"collection": []}

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    sha = res.json()["sha"] if res.status_code == 200 else None
    
    content_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": "Uppdaterade samlingsdata",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    put_res = requests.put(url, json=payload, headers=headers)
    return put_res.status_code in [200, 201]

def renumber_collection(collection_list):
    sorted_list = sorted(collection_list, key=lambda x: int(x.get("Pärmnummer", 0) or 0))
    for idx, card in enumerate(sorted_list, start=1):
        card["Pärmnummer"] = idx
    return sorted_list

# --- CARDMARKET URL GENERATOR ---
LANG_MAP = {"ENG": 1, "FRA": 2, "GER": 3, "SPA": 4, "ITA": 5, "JPN": 7, "POR": 8, "KOR": 9, "ZHT": 10}
COND_MAP = {"MT": 1, "NM": 2, "EX": 3, "GD": 4, "LP": 5, "PL": 6, "PO": 7}

def generate_cardmarket_url(card_name, set_code, number, lang_code="JPN", cond_code="NM"):
    lang_id = LANG_MAP.get(lang_code, 7)
    cond_id = COND_MAP.get(cond_code, 2)
    
    num_clean = number.split("/")[0].zfill(3) if number.split("/")[0].isdigit() else number
    search_str = f"{set_code} {num_clean}"
    base_url = "https://www.cardmarket.com/en/Pokemon/Products/Search"
    params = {
        "searchString": search_str,
        "language": lang_id,
        "minCondition": cond_id
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def fetch_cardmarket_price(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200:
            match = re.search(r'30-days average price.*?>([\d,.]+)\s*€', res.text, re.IGNORECASE | re.DOTALL)
            if match:
                return float(match.group(1).replace(',', '.'))
    except Exception:
        pass
    return None

# --- SÖKFUNKTION ---
@st.cache_data(ttl=3600)
def search_pokemon_cards(query):
    if not query:
        return []
    
    query_clean = query.strip().lower()
    search_words = [w for w in re.split(r'[\s/]+', query_clean) if w]
    headers = {'User-Agent': 'Mozilla/5.0'}
    results = []
    seen_ids = set()

    LANG_CODES = {
        "ja": "JPN", "en": "ENG", "fr": "FRA", "de": "GER", 
        "es": "SPA", "it": "ITA", "pt": "POR", "ko": "KOR", "zh-tw": "ZHT"
    }

    for lang_key, lang_code in LANG_CODES.items():
        try:
            url_tcgdex = f"https://api.tcgdex.net/v2/{lang_key}/cards"
            res_dex = requests.get(url_tcgdex, headers=headers, timeout=4)
            
            if res_dex.status_code == 200:
                cards_list = res_dex.json()
                for item in cards_list:
                    c_id = str(item.get("id", "")).lower()
                    c_name = str(item.get("name", "")).lower()
                    c_local = str(item.get("localId", "")).lower()
                    
                    matches_all = True
                    for w in search_words:
                        in_id = w in c_id
                        in_name = w in c_name
                        in_local = (w == c_local) or (w.lstrip("0") == c_local.lstrip("0"))
                        if not (in_id or in_name or in_local):
                            matches_all = False
                            break
                    
                    if matches_all:
                        card_id = item.get("id", "")
                        unique_key = f"{card_id}_{lang_code}"
                        
                        if unique_key not in seen_ids:
                            seen_ids.add(unique_key)
                            
                            img_base = item.get("image", "")
                            img_url = f"{img_base}/high.png" if img_base else ""

                            set_code = card_id.split("-")[0].upper() if "-" in card_id else ""
                            
                            results.append({
                                "id": unique_key,
                                "name": item.get("name", ""),
                                "set": {"name": set_code, "ptcgoCode": set_code},
                                "number": c_local,
                                "image_url": img_url,
                                "default_lang": lang_code
                            })
                            if len(results) >= 20:
                                break
        except Exception:
            pass
        if len(results) >= 20:
            break

    return results

# --- INITIERA SESSION STATE ---
if "app_data" not in st.session_state:
    st.session_state["app_data"] = load_data_from_github()

app_data = st.session_state["app_data"]
if "collection" not in app_data:
    app_data["collection"] = []

current_rate = 11.5

# --- LAYOUT & TABS ---
tab1, tab2 = st.tabs(["📊 Samling", "➕ Sök & Lägg till kort"])

# --- FLIK 1: SAMLING ---
with tab1:
    st.subheader("Min Samling")
    
    app_data["collection"] = renumber_collection(app_data.get("collection", []))
    collection = app_data["collection"]
    
    if collection:
        df = pd.DataFrame(collection)
        
        df["Värde (EUR)"] = pd.to_numeric(df["Värde (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (EUR)"] = pd.to_numeric(df["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (SEK)"] = (df["Köpt för (EUR)"] * current_rate).round(2)
        df["Värde idag (SEK)"] = (df["Värde (EUR)"] * current_rate).round(2)
        
        if "Bild" in df.columns:
            df["Bild"] = df["Bild"].apply(lambda x: x if (x and str(x).startswith("http")) else "https://assets.tcgdex.net/back.png")

        # ÅTGÄRDSRAD MED EDITERINGSLÄGE
        col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
        with col_act1:
            if st.button("🔄 Uppdatera priser (30-dagars snitt från Cardmarket)", type="secondary"):
                with st.spinner("Hämtar senaste priser från Cardmarket..."):
                    updated_count = 0
                    for item in app_data["collection"]:
                        cm_url = item.get("Cardmarket", "")
                        if cm_url:
                            fetched_price = fetch_cardmarket_price(cm_url)
                            if fetched_price is not None:
                                item["Värde (EUR)"] = fetched_price
                                item["Värde idag (SEK)"] = round(fetched_price * current_rate, 2)
                                updated_count += 1
                                
                    st.session_state["app_data"] = app_data
                    save_data_to_github(app_data)
                    st.success(f"Uppdaterade priser för {updated_count} kort!")
                    st.rerun()

        with col_act2:
            edit_mode = st.checkbox("✏️ Aktivera redigeringsläge")

        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Värde (EUR)", "Värde idag (SEK)", "Cardmarket"
        ]

        if not edit_mode:
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
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width="small"),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f", width="small"),
                "Cardmarket": st.column_config.LinkColumn("Cardmarket", display_text="🔗 Cardmarket", width="medium")
            }
            st.dataframe(df[columns_order], column_config=column_config, use_container_width=True, hide_index=True)
        
        else:
            st.info("💡 Du kan nu ändra värden direkt i cellerna nedan, klistra in en ny Bild-URL, eller markera rader och trycka Delete för att ta bort kort.")
            
            column_config_edit = {
                "Bild": st.column_config.TextColumn("Bild-URL", width="medium"),
                "Pärmnummer": st.column_config.NumberColumn("Pärmnr.", width="small"),
                "Språk": st.column_config.TextColumn("Språk", width="small"),
                "Namn": st.column_config.TextColumn("Namn", width="medium"),
                "Setnr.": st.column_config.TextColumn("Setnr.", width="small"),
                "SetBet.": st.column_config.TextColumn("SetBet.", width="small"),
                "Set": st.column_config.TextColumn("Set", width="medium"),
                "Övrigt": st.column_config.TextColumn("Övrigt", width="small"),
                "Skick": st.column_config.TextColumn("Skick", width="small"),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width="small"),
                "Värde (EUR)": st.column_config.NumberColumn("Värde (EUR)", format="%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f", width="small", disabled=True),
                "Cardmarket": st.column_config.TextColumn("Cardmarket URL", width="medium")
            }

            edited_df = st.data_editor(
                df[columns_order],
                column_config=column_config_edit,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic"
            )

            with col_act3:
                if st.button("💾 Spara ändringar", type="primary", use_container_width=True):
                    updated_list = edited_df.to_dict(orient="records")
                    
                    # Beräkna om SEK-priser och numrera om efter pärmnummer
                    for item in updated_list:
                        k_eur = float(item.get("Köpt för (EUR)", 0.0) or 0.0)
                        v_eur = float(item.get("Värde (EUR)", 0.0) or 0.0)
                        item["Köpt för (SEK)"] = round(k_eur * current_rate, 2)
                        item["Värde idag (SEK)"] = round(v_eur * current_rate, 2)
                    
                    app_data["collection"] = renumber_collection(updated_list)
                    st.session_state["app_data"] = app_data
                    save_data_to_github(app_data)
                    st.success("Ändringarna sparades!")
                    st.rerun()

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Totalt antal kort", len(df))
        c2.metric("Totalt värde (SEK)", f"{df['Värde idag (SEK)'].sum():,.2f} kr")
        c3.metric("Total vinst (SEK)", f"{(df['Värde idag (SEK)'].sum() - df['Köpt för (SEK)'].sum()):,.2f} kr")

    else:
        st.info("Samlingen är tom. Gå till fliken 'Sök & Lägg till kort'.")

# --- FLIK 2: SÖK & LÄGG TILL ---
with tab2:
    st.subheader("🔍 Sök på Namn, Nummer eller Setkod")
    
    search_query = st.text_input("Sök t.ex. 'sm4a 016' eller 'Raichu':", key="card_search_input")
    
    if search_query:
        with st.spinner("Söker kort..."):
            results = search_pokemon_cards(search_query)
            
        if results:
            st.success(f"Hittade {len(results)} träffar:")
            
            for card_api in results:
                with st.container():
                    col_img, col_info, col_form = st.columns([1, 2, 2])
                    
                    card_name = card_api.get("name", "")
                    set_info = card_api.get("set", {})
                    set_name = set_info.get("name", "")
                    set_code = set_info.get("ptcgoCode", "").upper()
                    number = card_api.get("number", "")
                    def_lang = card_api.get("default_lang", "ENG")
                    api_img_url = card_api.get("image_url", "")

                    with col_img:
                        display_img = api_img_url if api_img_url else "https://assets.tcgdex.net/back.png"
                        st.image(display_img, width=120)

                    with col_info:
                        st.markdown(f"### {card_name}")
                        st.write(f"**Språk:** `{def_lang}`")
                        st.write(f"**Set:** {set_name} (`{set_code}`)")
                        st.write(f"**Setnr:** {number}")

                    with col_form:
                        with st.form(key=f"add_form_{card_api['id']}"):
                            c_a, c_b = st.columns(2)
                            all_langs = ["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"]
                            default_lang_idx = all_langs.index(def_lang) if def_lang in all_langs else 0
                            
                            with c_a:
                                lang = st.selectbox("Språk", all_langs, index=default_lang_idx)
                                cond = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"], index=0)
                                parm_nr = st.number_input("Pärmnummer", min_value=1, value=len(app_data.get("collection", [])) + 1)
                            with c_b:
                                rarity = st.selectbox("Övrigt", ["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], index=0)
                                kopt_eur = st.number_input("Köpt för (EUR)", min_value=0.0, value=0.0, step=0.5)
                                varde_eur = st.number_input("Värde (EUR - Manuellt)", min_value=0.0, value=2.70, step=0.5)
                            
                            custom_img_url = st.text_input("Bild-URL (Klistra in länk om bilden saknas):", value=api_img_url)

                            if st.form_submit_button("➕ Lägg till i samlingen", type="primary", use_container_width=True):
                                cm_url = generate_cardmarket_url(card_name, set_code, number, lang, cond)
                                cm_price = fetch_cardmarket_price(cm_url)
                                final_price = varde_eur if varde_eur > 0 else (cm_price if cm_price else 0.0)
                                
                                final_img = custom_img_url.strip() if custom_img_url.strip() else (api_img_url if api_img_url else "https://assets.tcgdex.net/back.png")

                                new_entry = {
                                    "Bild": final_img,
                                    "Pärmnummer": int(parm_nr),
                                    "Språk": lang,
                                    "Namn": card_name,
                                    "Setnr.": number,
                                    "SetBet.": set_code,
                                    "Set": set_name if set_name else set_code,
                                    "Övrigt": rarity,
                                    "Skick": cond,
                                    "Köpt för (EUR)": kopt_eur,
                                    "Köpt för (SEK)": round(kopt_eur * current_rate, 2),
                                    "Värde (EUR)": final_price,
                                    "Värde idag (SEK)": round(final_price * current_rate, 2),
                                    "Datum tillagd": date.today().strftime("%Y-%m-%d"),
                                    "Cardmarket": cm_url
                                }
                                
                                for existing_card in app_data["collection"]:
                                    if int(existing_card.get("Pärmnummer", 0)) >= parm_nr:
                                        existing_card["Pärmnummer"] = int(existing_card["Pärmnummer"]) + 1
                                        
                                app_data["collection"].append(new_entry)
                                app_data["collection"] = renumber_collection(app_data["collection"])
                                
                                st.session_state["app_data"] = app_data
                                save_data_to_github(app_data)
                                st.success(f"Lade till {card_name} (#{parm_nr})!")
                                st.rerun()
                    st.divider()
