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
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            rate = data.get("rates", {}).get("SEK")
            if rate:
                return round(float(rate), 4)
    except Exception:
        pass
    return 11.50

# --- FAST MAPPING FÖR ASIATISKA SETS ---
JAPANESE_SET_MAP = {
    "sm4a": ("Ultradimensional Beasts", "SM4A"),
    "sm4b": ("GX Battle Boost", "SM4B"),
    "sm4+": ("GX Battle Boost", "SM4+"),
    "sm4": ("Crimson Invasion", "CIN"),
    "sm4s": ("Awakened Heroes", "SM4S"),
    "sm4m": ("Transdimensional Ultra Beasts", "SM4M"),
    "sm8b": ("Ultra Shiny GX", "SM8B"),
    "sm12a": ("Tag All Stars", "SM12A"),
    "s12a": ("VSTAR Universe", "S12A"),
    "sv4a": ("Shiny Treasure ex", "SV4A"),
}

LANGUAGE_OPTIONS = {
    "Japanska (JPN)": ("ja", "JPN"),
    "Engelska (ENG)": ("en", "ENG"),
    "Franska (FRA)": ("fr", "FRA"),
    "Tyska (GER)": ("de", "GER"),
    "Spanska (ESP)": ("es", "SPA"),
    "Italienska (ITA)": ("it", "ITA"),
    "Kinesiska (ZHT)": ("zh-tw", "ZHT")
}

def get_set_details_sync(set_id, lang_key="en"):
    if not set_id:
        return "", ""
    
    clean_id = str(set_id).lower().strip()
    
    if clean_id in JAPANESE_SET_MAP:
        return JAPANESE_SET_MAP[clean_id]
        
    try:
        url = f"https://api.tcgdex.net/v2/{lang_key}/sets/{urllib.parse.quote(clean_id)}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        if res.status_code == 200:
            data = res.json()
            set_name = data.get("name") or ""
            set_abbrev = data.get("abbreviation") or data.get("id") or ""
            set_abbrev = str(set_abbrev).upper()
            if set_name and set_name.lower() != clean_id:
                return set_name, set_abbrev
    except Exception:
        pass
        
    return clean_id.upper(), clean_id.upper()

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
        res = requests.get(raw_url, headers=headers, params={"t": str(uuid.uuid4())})
        if res.status_code == 200:
            return json.loads(res.text)
    except Exception:
        pass
    return {"collection": []}

def save_data_to_github(data_dict):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "GITHUB_TOKEN eller GITHUB_REPO saknas i Secrets!"
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    sha = None
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        sha = res.json().get("sha")
    
    content_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": "Uppdaterade samlingsdata via Streamlit",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    put_res = requests.put(url, json=payload, headers=headers)
    if put_res.status_code in [200, 201]:
        return True, "Sparat!"
    else:
        return False, f"GitHub felkod {put_res.status_code}: {put_res.text}"

def fix_existing_collection(collection_list):
    """Säkerställer unika ID:n och korrekta setnamn"""
    for idx, card in enumerate(collection_list):
        if "_id" not in card or not card["_id"]:
            card["_id"] = str(uuid.uuid4())
            
        current_set = str(card.get("Set") or "").strip()
        set_bet = str(card.get("SetBet.") or "").strip()
        
        if current_set.lower() in JAPANESE_SET_MAP or current_set.lower() == set_bet.lower():
            real_name, real_bet = get_set_details_sync(current_set or set_bet)
            if real_name and real_name != current_set:
                card["Set"] = real_name
                card["SetBet."] = real_bet
    return collection_list

def generate_google_cardmarket_url(name, number, set_name):
    safe_name = str(name) if name is not None else ""
    clean_name = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf]', '', safe_name).strip()
    query = f"{clean_name} {number or ''} {set_name or ''} cardmarket"
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"

# --- FÖRBÄTTRAD SÖKFUNKTION FÖR FLERA SPRÅK OCH ASIATISKA SET ---
@st.cache_data(ttl=3600, max_entries=100)
def search_pokemon_cards(query, lang_key="en", lang_code="ENG"):
    if not query or len(query.strip()) < 2:
        return []
    
    query_clean = query.strip().lower()
    if "/" in query_clean:
        query_clean = query_clean.split("/")[0].strip()

    words = [w for w in re.split(r'\s+', query_clean) if w]
    if not words:
        return []

    numbers = [w.lstrip("0") for w in words if w.isdigit()]
    text_words = [w for w in words if not w.isdigit()]

    headers = {'User-Agent': 'Mozilla/5.0'}
    results = []
    seen_ids = set()

    # Mappa om vanliga japanska set-koder till TCGdex internt ID-format
    SET_ALIAS_MAP = {
        "sm4a": ["sm4plus", "sm4+"],
        "sm4b": ["sm4b"],
        "sm8b": ["sm8b"],
        "sm12a": ["sm12a"],
        "s12a": ["s12a"],
        "sv4a": ["sv4a"]
    }

    # 1. DIREKT-SÖKNING PÅ SET + NUMMER (t.ex. "sm4a 016" -> testar "sm4plus-016")
    if text_words and numbers:
        raw_set = text_words[0]
        num_target = numbers[0]
        
        # Hämta lista på möjliga set-IDn
        target_sets = SET_ALIAS_MAP.get(raw_set, [raw_set])
        
        for s_id in target_sets:
            # Sök direkt på exakt kort-ID (format: set-nummer, t.ex. sm4plus-16 eller sm4plus-016)
            for test_num in [num_target, num_target.zfill(3)]:
                try:
                    card_exact_id = f"{s_id}-{test_num}"
                    url_card = f"https://api.tcgdex.net/v2/{lang_key}/cards/{urllib.parse.quote(card_exact_id)}"
                    res_card = requests.get(url_card, headers=headers, timeout=2)
                    
                    if res_card.status_code == 200:
                        item = res_card.json()
                        if isinstance(item, dict) and item.get("id"):
                            c_id = str(item.get("id"))
                            img_base = item.get("image") or ""
                            full_set_name, set_code = get_set_details_sync(s_id, lang_key)
                            
                            return [{
                                "id": f"{c_id}_{lang_code}",
                                "name": item.get("name") or "",
                                "eng_name": item.get("name") or "",
                                "set_code": set_code or raw_set.upper(),
                                "set_name": full_set_name or "",
                                "number": str(item.get("localId") or num_target),
                                "image_url": f"{img_base}/high.png" if img_base else "",
                                "default_lang": lang_code
                            }]
                except Exception:
                    pass

    # 2. GENERELL NAMNSÖKNING (Om inte exakt set+nr matchade)
    search_term = text_words[0] if text_words else words[0]
    try:
        url_search = f"https://api.tcgdex.net/v2/{lang_key}/cards?name={urllib.parse.quote(search_term)}"
        res_search = requests.get(url_search, headers=headers, timeout=3)
        
        if res_search.status_code == 200:
            cards_list = res_search.json()
            if isinstance(cards_list, list):
                for item in cards_list:
                    c_id = str(item.get("id") or "").lower()
                    c_name = str(item.get("name") or "").lower()
                    c_local_id = str(item.get("localId") or "").lstrip("0")
                    
                    id_parts = c_id.split("-")
                    id_number = id_parts[-1].lstrip("0") if len(id_parts) > 1 else ""
                    card_num = c_local_id if c_local_id else id_number

                    text_match = all(tw in c_name or tw in c_id for tw in text_words)
                    num_match = True
                    if numbers:
                        num_match = any(num == card_num for num in numbers)

                    if text_match and num_match:
                        card_id = str(item.get("id") or "")
                        unique_key = f"{card_id}_{lang_code}"
                        
                        if unique_key not in seen_ids:
                            seen_ids.add(unique_key)
                            img_base = item.get("image") or ""
                            raw_set_id = card_id.split("-")[0] if "-" in card_id else ""
                            full_set_name, set_code = get_set_details_sync(raw_set_id, lang_key)

                            results.append({
                                "id": unique_key,
                                "name": item.get("name") or "",
                                "eng_name": item.get("name") or "",
                                "set_code": set_code or "",
                                "set_name": full_set_name or "",
                                "number": str(item.get("localId") or (id_parts[-1] if len(id_parts) > 1 else "")),
                                "image_url": f"{img_base}/high.png" if img_base else "",
                                "default_lang": lang_code
                            })
                            if len(results) >= 20:
                                break
    except Exception:
        pass

    return results
    
# --- INITIERA SESSION STATE ---
if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 0

if "app_data" not in st.session_state or st.session_state["app_data"] is None:
    st.session_state["app_data"] = load_data_from_github()

app_data = st.session_state["app_data"]
if "collection" not in app_data:
    app_data["collection"] = []

app_data["collection"] = fix_existing_collection(app_data["collection"])
eur_to_sek = fetch_eur_to_sek_rate()

# --- LAYOUT & TABS ---
tab1, tab2 = st.tabs(["📊 Samling", "➕ Sök & Lägg till kort"])

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

                    save_payload = {"collection": processed_list}
                    success, msg = save_data_to_github(save_payload)
                    
                    if success:
                        st.session_state["app_data"] = None 
                        st.session_state["editor_version"] += 1
                        st.success("Ändringarna sparades och ordningen justerades!")
                        st.rerun()
                    else:
                        st.error(f"Kunde inte spara till GitHub: {msg}")

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
    
    col_lang, col_search = st.columns([1, 3])
    with col_lang:
        selected_lang_label = st.selectbox("Välj Sök-språk:", list(LANGUAGE_OPTIONS.keys()), index=0)
        lang_key, lang_code = LANGUAGE_OPTIONS[selected_lang_label]

    with col_search:
        search_query = st.text_input("Sök t.ex. 'sm4a 016' eller 'Alolan Raichu':", key="card_search_input")
    
    if search_query:
        with st.spinner("Söker kort..."):
            results = search_pokemon_cards(search_query, lang_key=lang_key, lang_code=lang_code)
            
        if results:
            st.success(f"Hittade {len(results)} träffar:")
            
            for card_api in results:
                with st.container():
                    col_img, col_info, col_form = st.columns([1, 2, 2])
                    
                    card_name = str(card_api.get("name") or "")
                    eng_name = str(card_api.get("eng_name") or card_name)
                    set_code = str(card_api.get("set_code") or "").upper()
                    full_set_name = str(card_api.get("set_name") or set_code)
                    number = str(card_api.get("number") or "")
                    def_lang = str(card_api.get("default_lang") or "ENG")
                    api_img_url = str(card_api.get("image_url") or "")

                    with col_img:
                        if api_img_url:
                            st.image(api_img_url, width=120)
                        else:
                            st.image("https://assets.tcgdex.net/back.png", width=120)

                    with col_info:
                        st.markdown(f"### {card_name}")
                        st.write(f"**Språk:** `{def_lang}`")
                        st.write(f"**Setkod:** `{set_code}`")
                        st.write(f"**Set:** `{full_set_name}`")
                        st.write(f"**Setnr:** {number}")

                    with col_form:
                        safe_set_str = re.sub(r'[^a-zA-Z0-9_]', '_', full_set_name)
                        form_key = f"form_{card_api['id']}_{safe_set_str}"
                        with st.form(key=form_key):
                            c_a, c_b = st.columns(2)
                            all_langs = ["ENG", "JPN", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"]
                            default_lang_idx = all_langs.index(def_lang) if def_lang in all_langs else 0
                            
                            with c_a:
                                lang = st.selectbox("Språk", all_langs, index=default_lang_idx)
                                cond = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"], index=0)
                                parm_nr = st.number_input("Pärmnummer", min_value=1, value=len(app_data.get("collection", [])) + 1)
                                set_base_input = st.text_input("Set / Base-namn", value=full_set_name)

                            with c_b:
                                rarity = st.selectbox("Övrigt", ["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], index=0)
                                kopt_eur = st.number_input("Köpt för (EUR)", min_value=0.0, value=0.0, step=0.5)
                                varde_eur_manual = st.number_input("Värde (EUR)", min_value=0.0, value=0.0, step=0.5)
                                custom_link = st.text_input("Klistra in Cardmarket-länk (Valfritt):", value="")
                            
                            custom_img_url = st.text_input("Bild-URL (Klistra in länk om bilden saknas):", value=api_img_url)

                            if st.form_submit_button("➕ Lägg till i samlingen", type="primary", use_container_width=True):
                                google_url = generate_google_cardmarket_url(eng_name, number, set_base_input)
                                raw_img = custom_img_url.strip() if custom_img_url.strip() else (api_img_url if api_img_url else "")

                                new_entry = {
                                    "_id": str(uuid.uuid4()),
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
                                    "Värde (EUR)": varde_eur_manual,
                                    "Värde idag (SEK)": round(varde_eur_manual * eur_to_sek, 2),
                                    "Datum tillagd": date.today().strftime("%Y-%m-%d"),
                                    "Google Sök": google_url,
                                    "Egen Cardmarket Länk": custom_link.strip()
                                }
                                
                                for existing_card in app_data["collection"]:
                                    if int(existing_card.get("Pärmnummer", 0)) >= parm_nr:
                                        existing_card["Pärmnummer"] = int(existing_card["Pärmnummer"]) + 1
                                        
                                app_data["collection"].append(new_entry)
                                
                                sorted_coll = sorted(app_data["collection"], key=lambda x: int(x.get("Pärmnummer", 0) or 0))
                                for idx, card in enumerate(sorted_coll, start=1):
                                    card["Pärmnummer"] = idx
                                
                                save_payload = {"collection": sorted_coll}
                                success, msg = save_data_to_github(save_payload)
                                if success:
                                    st.session_state["app_data"] = None
                                    st.session_state["editor_version"] += 1
                                    st.success(f"Lade till {card_name} (#{parm_nr})!")
                                    st.rerun()
                                else:
                                    st.error(f"Kunde inte spara till GitHub: {msg}")
                    st.divider()
        else:
            st.warning("Inga kort hittades för din sökning. Se till att du valt rätt språk i dropdown-menyn.")
