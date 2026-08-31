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
        return None
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(raw_url, headers=headers)
        if res.status_code == 200:
            return json.loads(res.text)
    except Exception:
        pass
    return None

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

# --- CARDMARKET URL BUILDER ---
LANG_MAP = {
    "ENG": 1, "FRA": 2, "GER": 3, "SPA": 4, "ITA": 5, "JPN": 7, "POR": 8, "KOR": 9, "ZHT": 10
}

COND_MAP = {
    "MT": 1, "NM": 2, "EX": 3, "GD": 4, "LP": 5, "PL": 6, "PO": 7
}

def generate_cardmarket_url(card_name, set_name, set_nr, lang_code, cond_code):
    base_search_url = "https://www.cardmarket.com/en/Pokemon/Products/Search"
    search_query = f"{card_name} {set_nr}".strip()
    
    lang_id = LANG_MAP.get(lang_code, 1)
    cond_id = COND_MAP.get(cond_code, 2)
    
    params = {
        "searchString": search_query,
        "language": lang_id,
        "minCondition": cond_id
    }
    return f"{base_search_url}?{urllib.parse.urlencode(params)}"

# --- SMART FLERSPRÅKIG & MULTI-FÄLT SÖKNING ---
@st.cache_data(ttl=3600)
def search_pokemon_cards(query):
    if not query:
        return []
    
    query = query.strip()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    results = []
    seen_ids = set()

    # Rensa numret om användaren söker på t.ex. "016/050" -> "016" och "16"
    clean_num = query.split("/")[0].strip()
    stripped_num = clean_num.lstrip("0") if clean_num.isdigit() else clean_num

    LANG_CODES = {
        "ja": "JPN", "en": "ENG", "fr": "FRA", "de": "GER", 
        "es": "SPA", "it": "ITA", "pt": "POR", "ko": "KOR", "zh-tw": "ZHT"
    }

    # 1. TCGdex API (Bred sökning på Namn, Set & Kortnummer)
    for lang_key, lang_code in LANG_CODES.items():
        try:
            # Hämta alla kort från språket
            url_tcgdex = f"https://api.tcgdex.net/v2/{lang_key}/cards"
            res_dex = requests.get(url_tcgdex, headers=headers, timeout=3)
            
            if res_dex.status_code == 200:
                cards_list = res_dex.json()
                
                # Filtrera lokalt på namn, localId (kortnr) eller set ID (t.ex. sm4a)
                matched_cards = []
                q_lower = query.lower()
                
                for item in cards_list:
                    c_id = item.get("id", "").lower()
                    c_name = item.get("name", "").lower()
                    c_local = str(item.get("localId", "")).lower()
                    
                    # Matchningsvillkor
                    if (q_lower in c_name) or (clean_num == c_local) or (stripped_num == c_local) or (q_lower in c_id):
                        matched_cards.append(item)
                        if len(matched_cards) >= 6:
                            break

                for item in matched_cards:
                    card_id = item.get("id", "")
                    unique_key = f"{card_id}_{lang_code}"
                    
                    if unique_key not in seen_ids:
                        seen_ids.add(unique_key)
                        c_res = requests.get(f"https://api.tcgdex.net/v2/{lang_key}/cards/{card_id}", headers=headers, timeout=2)
                        if c_res.status_code == 200:
                            c = c_res.json()
                            set_id = c.get("set", {}).get("id", "").upper()
                            results.append({
                                "id": unique_key,
                                "name": c.get("name"),
                                "set": {
                                    "name": c.get("set", {}).get("name", ""),
                                    "ptcgoCode": set_id,
                                    "printedTotal": c.get("set", {}).get("cardCount", {}).get("official", "")
                                },
                                "number": c.get("localId", ""),
                                "images": {"small": f"{c.get('image')}/low.png" if c.get('image') else ""},
                                "cardmarket": {"prices": {"averageSellPrice": 0.0}},
                                "default_lang": lang_code
                            })
        except Exception:
            pass
            
        if len(results) >= 12:
            break

    # 2. Pokémon TCG API (Engelsk Reserv)
    if not results:
        try:
            q_str = f"name:\"{query}*\" OR number:\"{clean_num}\" OR number:\"{stripped_num}\" OR set.id:\"{query.lower()}\" OR set.ptcgoCode:\"{query.upper()}\""
            url = f"https://api.pokemontcg.io/v2/cards?q={urllib.parse.quote(q_str)}"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                for d in data[:10]:
                    d["default_lang"] = "ENG"
                    results.append(d)
        except Exception:
            pass

    return results

# --- HÄMTA DATA ---
app_data = load_data_from_github()
if not app_data or "collection" not in app_data:
    app_data = {"collection": []}

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
        
        # Beräkningar
        df["Värde (EUR)"] = pd.to_numeric(df["Värde (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (EUR)"] = pd.to_numeric(df["Köpt för (EUR)"], errors='coerce').fillna(0.0)
        df["Köpt för (SEK)"] = (df["Köpt för (EUR)"] * current_rate).round(2)
        df["Värde idag (SEK)"] = (df["Värde (EUR)"] * current_rate).round(2)
        
        if "Cardmarket" not in df.columns:
            df["Cardmarket"] = ""
            
        for idx, row in df.iterrows():
            if not row["Cardmarket"]:
                df.at[idx, "Cardmarket"] = generate_cardmarket_url(
                    row.get("Namn", ""), 
                    row.get("Set", ""), 
                    row.get("Setnr.", ""), 
                    row.get("Språk", "ENG"), 
                    row.get("Skick", "NM")
                )

        # Hantera Enskild Radera
        with st.expander("🛠️ Hantera / Radera enskilt kort", expanded=False):
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                del_parm = st.number_input("Välj Pärmnummer att radera:", min_value=1, max_value=len(df), value=1)
            with col_del2:
                st.write("")
                if st.button("🗑️ Radera kort", type="primary", use_container_width=True):
                    idx_to_remove = del_parm - 1
                    removed_card = app_data["collection"].pop(idx_to_remove)
                    app_data["collection"] = renumber_collection(app_data["collection"])
                    save_data_to_github(app_data)
                    st.success(f"Raderade #{del_parm} ({removed_card.get('Namn')})")
                    st.rerun()

        # Visningstabell
        columns_order = [
            "Bild", "Pärmnummer", "Språk", "Namn", "Setnr.", "SetBet.", "Set", 
            "Övrigt", "Skick", "Köpt för (EUR)", "Värde (EUR)", "Värde idag (SEK)", "Cardmarket"
        ]
        
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
            "Cardmarket": st.column_config.LinkColumn("Cardmarket", display_text="🔗 Öppna på Cardmarket", width="medium")
        }

        st.dataframe(
            df[columns_order],
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Totalt antal kort", len(df))
        c2.metric("Totalt värde (SEK)", f"{df['Värde idag (SEK)'].sum():,.2f} kr")
        c3.metric("Total vinst (SEK)", f"{(df['Värde idag (SEK)'].sum() - df['Köpt för (SEK)'].sum()):,.2f} kr")

        # NÖDKNAPP: RENSA HELA SAMLINGEN
        st.write("")
        st.write("")
        with st.expander("⚠️ Rensa hela samlingen", expanded=False):
            st.warning("Detta raderar alla kort i samlingen permanent på GitHub!")
            if st.button("🔥 RADERA ALLA KORT I SAMLINGEN", type="primary"):
                app_data["collection"] = []
                save_data_to_github(app_data)
                st.success("Samlingen har tömts helt!")
                st.rerun()

    else:
        st.info("Samlingen är tom. Gå till fliken 'Sök & Lägg till kort' för att lägga till ditt första kort.")

# --- FLIK 2: SÖK & LÄGG TILL ---
with tab2:
    st.subheader("🔍 Sök på Namn, Nummer (t.ex. 016/050) eller Setkod (t.ex. sm4a)")
    
    search_query = st.text_input("Skriv sökord:", key="card_search_input")
    
    if search_query:
        with st.spinner("Söker och matchar kortnummer, setkoder och namn..."):
            results = search_pokemon_cards(search_query)
            
        if results:
            st.success(f"Hittade {len(results)} träffar:")
            
            for card_api in results:
                with st.container():
                    col_img, col_info, col_form = st.columns([1, 2, 2])
                    
                    card_name = card_api.get("name", "")
                    set_info = card_api.get("set", {})
                    set_name = set_info.get("name", "")
                    set_code = set_info.get("ptcgoCode", set_info.get("id", "")).upper()
                    number = card_api.get("number", "")
                    printed_total = set_info.get("printedTotal", "")
                    full_number = f"{number}/{printed_total}" if printed_total else number
                    
                    img_url = card_api.get("images", {}).get("small", "")
                    def_lang = card_api.get("default_lang", "ENG")
                    
                    cm_prices = card_api.get("cardmarket", {}).get("prices", {})
                    suggested_price = cm_prices.get("averageSellPrice", cm_prices.get("trendPrice", 0.0))

                    with col_img:
                        if img_url:
                            st.image(img_url, width=130)

                    with col_info:
                        st.markdown(f"### {card_name}")
                        st.write(f"**Språk hittat:** `{def_lang}`")
                        st.write(f"**Set:** {set_name} (`{set_code}`)")
                        st.write(f"**Setnr:** {full_number}")
                        if suggested_price:
                            st.caption(f"Estimerat marknadsvärde: ~{suggested_price} EUR")

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
                                varde_eur = st.number_input("Värde (EUR)", min_value=0.0, value=float(suggested_price or 0.0), step=0.5)

                            if st.form_submit_button("➕ Lägg till i samlingen", type="primary", use_container_width=True):
                                cm_url = generate_cardmarket_url(card_name, set_name, full_number, lang, cond)
                                
                                new_entry = {
                                    "Bild": img_url,
                                    "Pärmnummer": int(parm_nr),
                                    "Språk": lang,
                                    "Namn": card_name,
                                    "Setnr.": full_number,
                                    "SetBet.": set_code,
                                    "Set": set_name,
                                    "Övrigt": rarity,
                                    "Skick": cond,
                                    "Köpt för (EUR)": kopt_eur,
                                    "Köpt för (SEK)": round(kopt_eur * current_rate, 2),
                                    "Värde (EUR)": varde_eur,
                                    "Värde idag (SEK)": round(varde_eur * current_rate, 2),
                                    "Datum tillagd": date.today().strftime("%Y-%m-%d"),
                                    "Cardmarket": cm_url
                                }
                                
                                for existing_card in app_data["collection"]:
                                    if int(existing_card.get("Pärmnummer", 0)) >= parm_nr:
                                        existing_card["Pärmnummer"] = int(existing_card["Pärmnummer"]) + 1
                                        
                                app_data["collection"].append(new_entry)
                                app_data["collection"] = renumber_collection(app_data["collection"])
                                
                                save_data_to_github(app_data)
                                st.success(f"Lade till {card_name} (#{parm_nr})!")
                                st.rerun()
                    st.divider()
        else:
            st.warning("Ingen automatisk träff hittades. Du kan lägga till kortet manuellt nedan.")

    # --- FALLBACK: MANUELL INMATNING OM KORTET SAKNAS I API ---
    st.write("")
    with st.expander("✏️ Kan du inte hitta kortet? Lägg till manuellt", expanded=not search_query):
        with st.form("manual_add_form"):
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                m_name = st.text_input("Namn *", value="Alolan Raichu")
                m_set = st.text_input("Set *", value="Ultradimensional Beasts")
                m_setbet = st.text_input("SetBet *", value="SM4A")
            with m_col2:
                m_setnr = st.text_input("Setnr. *", value="016/050")
                m_lang = st.selectbox("Språk", ["JPN", "ENG", "SWE", "FRA", "GER", "ITA", "KOR", "SPA", "POR", "ZHT"], index=0, key="m_lang")
                m_cond = st.selectbox("Skick", ["NM", "EX", "GD", "LP", "PL", "PO"], index=0, key="m_cond")
            with m_col3:
                m_parm = st.number_input("Pärmnummer", min_value=1, value=len(app_data.get("collection", [])) + 1, key="m_parm")
                m_ovrigt = st.selectbox("Övrigt", ["Normal", "Holo", "Reverse Holo", "Secret Rare", "Promo"], index=0, key="m_ovr")
                m_img = st.text_input("Bild URL (valfri)", value="")
                m_kopt = st.number_input("Köpt för (EUR)", min_value=0.0, value=0.0, key="m_kopt")
                m_varde = st.number_input("Värde (EUR)", min_value=0.0, value=2.70, key="m_varde")

            if st.form_submit_button("➕ Spara manuellt kort", type="primary", use_container_width=True):
                cm_url = generate_cardmarket_url(m_name, m_set, m_setnr, m_lang, m_cond)
                new_entry = {
                    "Bild": m_img,
                    "Pärmnummer": int(m_parm),
                    "Språk": m_lang,
                    "Namn": m_name,
                    "Setnr.": m_setnr,
                    "SetBet.": m_setbet,
                    "Set": m_set,
                    "Övrigt": m_ovrigt,
                    "Skick": m_cond,
                    "Köpt för (EUR)": m_kopt,
                    "Köpt för (SEK)": round(m_kopt * current_rate, 2),
                    "Värde (EUR)": m_varde,
                    "Värde idag (SEK)": round(m_varde * current_rate, 2),
                    "Datum tillagd": date.today().strftime("%Y-%m-%d"),
                    "Cardmarket": cm_url
                }
                
                for existing_card in app_data["collection"]:
                    if int(existing_card.get("Pärmnummer", 0)) >= m_parm:
                        existing_card["Pärmnummer"] = int(existing_card["Pärmnummer"]) + 1
                        
                app_data["collection"].append(new_entry)
                app_data["collection"] = renumber_collection(app_data["collection"])
                
                save_data_to_github(app_data)
                st.success(f"Lade till {m_name} (#{m_parm}) manuellt!")
                st.rerun()
