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

# --- HJÄLPFUNKTION FÖR GOOGLE-SÖKNING ---
def generate_google_cardmarket_url(name, number, set_name):
    clean_name = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf]', '', name).strip()
    query = f"{clean_name} {number} {set_name} cardmarket"
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"

# --- SÖKFUNKTION (Endast för att hitta bilder/namn/set) ---
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
                            eng_name = eng_cards_map.get(card_id, item.get("name", ""))

                            results.append({
                                "id": unique_key,
                                "name": item.get("name", ""),
                                "eng_name": eng_name,
                                "set_code": raw_set_code,
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
        
        # Säkerställ alla fält
        for col in ["Värde (USD)", "Köpt för (EUR)", "Google Sök", "Egen Cardmarket Länk", "Engelskt Namn"]:
            if col not in df.columns:
                df[col] = 0.0 if "Värde" in col or "Köpt" in col else ""
        
        df["Värde (USD)"] = pd.to_numeric(df["Värde (USD)"], errors='coerce').fillna(0.0)
        df["Köpt för (EUR)"] = pd.to_numeric(df["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (SEK)"] = (df["Köpt för (EUR)"] * eur_to_sek).round(2)
        df["Värde idag (SEK)"] = (df["Värde (USD)"] * usd_to_sek).round(2)
        
        if "Bild" in df.columns:
            df["Bild"] = df["Bild"].apply(get_image_as_base64)

        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            edit_mode = st.checkbox("✏️ Aktivera redigeringsläge (Mata in värden & egna länkar)")

        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Värde (USD)", "Värde idag (SEK)", "Google Sök", "Egen Cardmarket Länk"
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
                "Värde (USD)": st.column_config.NumberColumn("Värde ($)", format="$%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small"),
                "Google Sök": st.column_config.LinkColumn("Sök Cardmarket", display_text="🔍 Google Sök", width="medium"),
                "Egen Cardmarket Länk": st.column_config.LinkColumn("Min Cardmarket Länk", display_text="🔗 Öppna Sida", width="medium")
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
                "Set": st.column_config.TextColumn("Set/Base", width="medium"),
                "Övrigt": st.column_config.TextColumn("Övrigt", width="small"),
                "Skick": st.column_config.TextColumn("Skick", width="small"),
                "Köpt för (EUR)": st.column_config.NumberColumn("Köpt (EUR)", format="%.2f", width="small"),
                "Värde (USD)": st.column_config.NumberColumn("Värde ($)", format="%.2f", width="small"),
                "Värde idag (SEK)": st.column_config.NumberColumn("Värde (SEK)", format="%.2f kr", width="small", disabled=True),
                "Google Sök": st.column_config.TextColumn("Google Sök URL", disabled=True, width="medium"),
                "Egen Cardmarket Länk": st.column_config.TextColumn("Klistra in Cardmarket URL här", width="large")
            }

            edited_df = st.data_editor(
                df[columns_order],
                column_config=column_config_edit,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic"
            )

            with col_act2:
                if st.button("💾 Spara ändringar", type="primary", use_container_width=True):
                    updated_list = edited_df.to_dict(orient="records")
                    for item in updated_list:
                        k_eur = float(item.get("Köpt för (EUR)", 0.0) or 0.0)
                        v_usd = float(item.get("Värde (USD)", 0.0) or 0.0)
                        item["Köpt för (SEK)"] = round(k_eur * eur_to_sek, 2)
                        item["Värde idag (SEK)"] = round(v_usd * usd_to_sek, 2)
                        
                        # Generera alltid om google-sökningen ifall man ändrat namn/set
                        s_name = item.get("Engelskt Namn") or item.get("Namn", "")
                        item["Google Sök"] = generate_google_cardmarket_url(s_name, item.get("Setnr.", ""), item.get("Set", ""))

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
    search_query = st.text_input("Sök t.ex. 'sm4 031' eller 'Whimsicott':", key="card_search_input")
    
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
                    set_code = card_api.get("set_code", "").upper()
                    number = card_api.get("number", "")
                    def_lang = card_api.get("default_lang", "ENG")
                    api_img_url = card_api.get("image_url", "")

                    with col_img:
                        display_img = get_image_as_base64(api_img_url)
                        st.image(display_img, width=120)

                    with col_info:
                        st.markdown(f"### {card_name}")
                        st.write(f"**Språk:** `{def_lang}`")
                        st.write(f"**Setkod:** `{set_code}`")
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
                                set_base_input = st.text_input("Set / Base-namn", value=set_code)

                            with c_b:
                                rarity = st.selectbox("Övrigt", ["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], index=0)
                                kopt_eur = st.number_input("Köpt för (EUR)", min_value=0.0, value=0.0, step=0.5)
                                varde_usd_manual = st.number_input("Värde ($ - Manuellt)", min_value=0.0, value=0.0, step=0.5)
                                custom_link = st.text_input("Klistra in Cardmarket-länk (Valfritt):", value="")
                            
                            custom_img_url = st.text_input("Bild-URL (Klistra in länk om bilden saknas):", value=api_img_url)

                            if st.form_submit_button("➕ Lägg till i samlingen", type="primary", use_container_width=True):
                                google_url = generate_google_cardmarket_url(eng_name, number, set_base_input)
                                raw_img = custom_img_url.strip() if custom_img_url.strip() else (api_img_url if api_img_url else "")

                                new_entry = {
                                    "Bild": raw_img,
                                    "Pärmnummer": int(parm_nr),
                                    "Språk": lang,
                                    "Namn": card_name,
                                    "Engelskt Namn": eng_name,
                                    "Setnr.": number,
                                    "SetBet.": set_code,
                                    "Set": set_base_input,
                                    "Övrigt": rarity,
                                    "Skick": cond,
                                    "Köpt för (EUR)": kopt_eur,
                                    "Köpt för (SEK)": round(kopt_eur * eur_to_sek, 2),
                                    "Värde (USD)": varde_usd_manual,
                                    "Värde idag (SEK)": round(varde_usd_manual * usd_to_sek, 2),
                                    "Datum tillagd": date.today().strftime("%Y-%m-%d"),
                                    "Google Sök": google_url,
                                    "Egen Cardmarket Länk": custom_link.strip()
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
