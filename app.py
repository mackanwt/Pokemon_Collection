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

@st.cache_data(ttl=3600)
def get_image_as_base64(url):
    if not url or not str(url).startswith("http"):
        return "https://assets.tcgdex.net/back.png"
    
    if "tcgdex.net" in url:
        if not url.endswith(".png") and not url.endswith(".jpg") and not url.endswith(".webp"):
            url = f"{url}/high.png"
        return url
        
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            content_type = res.headers.get("content-type", "image/png")
            b64_str = base64.b64encode(res.content).decode("utf-8")
            return f"data:{content_type};base64,{b64_str}"
    except Exception:
        pass
        
    return "https://assets.tcgdex.net/back.png"

# --- GRATIS AUTOMATISK PRISHÄMTNING (TCGdex / TCGplayer) ---
@st.cache_data(ttl=3600)
def fetch_card_price_usd(card_id):
    """Hämtar marknadspris i USD från TCGdex öppna API (kostnadsfritt)."""
    if not card_id:
        return 0.0
    # Rensa språkprefix om det finns
    clean_id = card_id.split("_")[0]
    url = f"https://api.tcgdex.net/v2/en/cards/{clean_id}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=4)
        if res.status_code == 200:
            data = res.json()
            pricing = data.get("variants", {})
            # Leta efter priser i olika varianter
            for var in ["normal", "reverse", "holo", "firstEdition"]:
                if var in pricing and pricing[var]:
                    return float(pricing[var])
            # Fallback till TCGplayer-strukturen om den finns
            tcg_data = data.get("pricing", {}).get("tcgplayer", {})
            if "mid" in tcg_data:
                return float(tcg_data["mid"])
            elif "market" in tcg_data:
                return float(tcg_data["market"])
    except Exception:
        pass
    return 0.0

# --- LÄNKGENERATORER ---
def generate_cardmarket_url(card_name_eng):
    # Säker sökning på enbart engelskt namn för att undvika fel träffar på japanska kort
    clean_name = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf]', '', card_name_eng).strip()
    return f"https://www.cardmarket.com/en/Pokemon/Products/Search?searchString={urllib.parse.quote(clean_name)}"

def generate_pricecharting_url(card_name_eng, is_japanese=False):
    clean_name = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf]', '', card_name_eng).strip()
    query = f"{clean_name} japanese" if is_japanese else clean_name
    return f"https://www.pricecharting.com/search-products?q={urllib.parse.quote(query)}&type=prices"

# --- MAPPNINGSSAMPLING FÖR SETKODER & SETNAMN ---
SET_INFO_MAP = {
    "SM1": {"code": "SUM", "name": "Sun & Moon"},
    "SM2": {"code": "GRI", "name": "Guardians Rising"},
    "SM3": {"code": "BUS", "name": "Burning Shadows"},
    "SM3.5": {"code": "SLG", "name": "Shining Legends"},
    "SM4": {"code": "CIN", "name": "Crimson Invasion"},
    "SM4A": {"code": "CIN", "name": "Crimson Invasion"},
    "SM5": {"code": "UPR", "name": "Ultra Prism"},
    "SM6": {"code": "FLI", "name": "Forbidden Light"},
    "SM7": {"code": "CES", "name": "Celestial Storm"},
    "SM7.5": {"code": "DRM", "name": "Dragon Majesty"},
    "SM8": {"code": "LOT", "name": "Lost Thunder"},
    "SM9": {"code": "TEU", "name": "Team Up"},
    "SM10": {"code": "UNB", "name": "Unbroken Bonds"},
    "SM11": {"code": "UNM", "name": "Unified Minds"},
    "SM11.5": {"code": "HIF", "name": "Hidden Fates"},
    "SM12": {"code": "CEC", "name": "Cosmic Eclipse"},
    "SV1": {"code": "SVI", "name": "Scarlet & Violet"},
    "SV2": {"code": "PAL", "name": "Paldea Evolved"},
    "SV3": {"code": "OBF", "name": "Obsidian Flames"},
    "SV3.5": {"code": "MEW", "name": "151"}
}

# --- SÖKFUNKTION ---
@st.cache_data(ttl=3600)
def search_pokemon_cards(query):
    if not query:
        return []
    
    query_clean = query.strip().lower()
    if "/" in query_clean:
        query_clean = query_clean.split("/")[0].strip()

    search_words = [w for w in re.split(r'\s+', query_clean) if w]
    headers = {'User-Agent': 'Mozilla/5.0'}
    results = []
    seen_ids = set()

    LANG_CODES = {
        "en": "ENG", "ja": "JPN", "fr": "FRA", "de": "GER", 
        "es": "SPA", "it": "ITA", "pt": "POR", "ko": "KOR", "zh-tw": "ZHT"
    }

    eng_cards_map = {}
    try:
        res_eng = requests.get("https://api.tcgdex.net/v2/en/cards", headers=headers, timeout=4)
        if res_eng.status_code == 200:
            for c in res_eng.json():
                eng_cards_map[c.get("id")] = c.get("name")
    except Exception:
        pass

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
                            raw_set_code = card_id.split("-")[0].upper() if "-" in card_id else ""
                            
                            final_set_code = raw_set_code
                            final_set_name = raw_set_code

                            if raw_set_code in SET_INFO_MAP:
                                final_set_code = SET_INFO_MAP[raw_set_code]["code"]
                                final_set_name = SET_INFO_MAP[raw_set_code]["name"]

                            eng_name = eng_cards_map.get(card_id, item.get("name", ""))

                            results.append({
                                "id": unique_key,
                                "raw_id": card_id,
                                "name": item.get("name", ""),
                                "eng_name": eng_name,
                                "set": {"name": final_set_name, "ptcgoCode": final_set_code},
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

usd_to_sek = 10.5
eur_to_sek = 11.5

# --- LAYOUT & TABS ---
tab1, tab2 = st.tabs(["📊 Samling", "➕ Sök & Lägg till kort"])

# --- FLIK 1: SAMLING ---
with tab1:
    st.subheader("Min Samling")
    
    app_data["collection"] = renumber_collection(app_data.get("collection", []))
    collection = app_data["collection"]
    
    if collection:
        df = pd.DataFrame(collection)
        
        for col in ["Värde (USD)", "Köpt för (EUR)", "Cardmarket", "PriceCharting", "Engelskt Namn", "API_ID"]:
            if col not in df.columns:
                df[col] = 0.0 if "Värde" in col or "Köpt" in col else ""
        
        df["Värde (USD)"] = pd.to_numeric(df["Värde (USD)"], errors='coerce').fillna(0.0)
        df["Köpt för (EUR)"] = pd.to_numeric(df["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (SEK)"] = (df["Köpt för (EUR)"] * eur_to_sek).round(2)
        df["Värde idag (SEK)"] = (df["Värde (USD)"] * usd_to_sek).round(2)
        
        if "Bild" in df.columns:
            df["Bild"] = df["Bild"].apply(get_image_as_base64)

        col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
        with col_act1:
            if st.button("🔄 Uppdatera marknadspriser", type="secondary"):
                with st.spinner("Hämtar senaste marknadspriser..."):
                    for item in app_data["collection"]:
                        search_name = item.get("Engelskt Namn") or item.get("Namn", "")
                        item["Cardmarket"] = generate_cardmarket_url(search_name)
                        item["PriceCharting"] = generate_pricecharting_url(search_name, is_japanese=(item.get("Språk") == "JPN"))
                        
                        # Hämta live-pris via gratis TCGdex API
                        api_id = item.get("API_ID")
                        if api_id:
                            live_price = fetch_card_price_usd(api_id)
                            if live_price > 0:
                                item["Värde (USD)"] = live_price
                                item["Värde idag (SEK)"] = round(live_price * usd_to_sek, 2)

                    st.session_state["app_data"] = app_data
                    save_data_to_github(app_data)
                    st.success("Priser och länkar har uppdaterats!")
                    st.rerun()

        with col_act2:
            edit_mode = st.checkbox("✏️ Aktivera redigeringsläge")

        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Värde (USD)", "Värde idag (SEK)", "Cardmarket", "PriceCharting"
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
                "Värde (USD)": st.column_config.NumberColumn("Marknad ($)", format="$%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small"),
                "Cardmarket": st.column_config.LinkColumn("Cardmarket", display_text="🔗 Cardmarket", width="medium"),
                "PriceCharting": st.column_config.LinkColumn("PriceCharting", display_text="📈 PriceCharting", width="medium")
            }
            st.dataframe(df[columns_order], column_config=column_config, use_container_width=True, hide_index=True)
        
        else:
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
                "Värde (USD)": st.column_config.NumberColumn("Marknad ($)", format="$%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small", disabled=True),
                "Cardmarket": st.column_config.TextColumn("Cardmarket URL", width="medium"),
                "PriceCharting": st.column_config.TextColumn("PriceCharting URL", width="medium")
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
                    for item in updated_list:
                        k_eur = float(item.get("Köpt för (EUR)", 0.0) or 0.0)
                        v_usd = float(item.get("Värde (USD)", 0.0) or 0.0)
                        item["Köpt för (SEK)"] = round(k_eur * eur_to_sek, 2)
                        item["Värde idag (SEK)"] = round(v_usd * usd_to_sek, 2)
                    
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
    search_query = st.text_input("Sök t.ex. 'sm4 031' eller 'Alolan Raichu':", key="card_search_input")
    
    if search_query:
        with st.spinner("Söker kort..."):
            results = search_pokemon_cards(search_query)
            
        if results:
            st.success(f"Hittade {len(results)} träffar:")
            
            for card_api in results:
                with st.container():
                    col_img, col_info, col_form = st.columns([1, 2, 2])
                    
                    card_name = card_api.get("name", "")
                    eng_name = card_api.get("eng_name", card_name)
                    set_info = card_api.get("set", {})
                    set_name = set_info.get("name", "")
                    set_code = set_info.get("ptcgoCode", "").upper()
                    number = card_api.get("number", "")
                    def_lang = card_api.get("default_lang", "ENG")
                    api_img_url = card_api.get("image_url", "")
                    raw_id = card_api.get("raw_id", "")

                    with col_img:
                        display_img = get_image_as_base64(api_img_url)
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
                                varde_usd_manual = st.number_input("Värde ($ - Manuellt överskrid)", min_value=0.0, value=0.0, step=0.5)
                            
                            custom_img_url = st.text_input("Bild-URL (Klistra in länk om bilden saknas):", value=api_img_url)

                            if st.form_submit_button("➕ Lägg till i samlingen", type="primary", use_container_width=True):
                                is_jpn = (lang == "JPN")
                                cm_url = generate_cardmarket_url(eng_name)
                                pc_url = generate_pricecharting_url(eng_name, is_japanese=is_jpn)
                                
                                # Hämta automatiskt pris från API
                                auto_price = fetch_card_price_usd(raw_id)
                                final_usd = varde_usd_manual if varde_usd_manual > 0 else auto_price

                                raw_img = custom_img_url.strip() if custom_img_url.strip() else (api_img_url if api_img_url else "")

                                new_entry = {
                                    "API_ID": raw_id,
                                    "Bild": raw_img,
                                    "Pärmnummer": int(parm_nr),
                                    "Språk": lang,
                                    "Namn": card_name,
                                    "Engelskt Namn": eng_name,
                                    "Setnr.": number,
                                    "SetBet.": set_code,
                                    "Set": set_name if set_name else set_code,
                                    "Övrigt": rarity,
                                    "Skick": cond,
                                    "Köpt för (EUR)": kopt_eur,
                                    "Köpt för (SEK)": round(kopt_eur * eur_to_sek, 2),
                                    "Värde (USD)": final_usd,
                                    "Värde idag (SEK)": round(final_usd * usd_to_sek, 2),
                                    "Datum tillagd": date.today().strftime("%Y-%m-%d"),
                                    "Cardmarket": cm_url,
                                    "PriceCharting": pc_url
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
