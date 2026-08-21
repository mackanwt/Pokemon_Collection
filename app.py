import streamlit as st
import pandas as pd

st.set_page_config(page_title="Lama Bageri", page_icon="🦙", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# DESIGN & STIL (CSS)
# ==========================================
st.markdown("""
    <style>
        .stApp {
            background-color: #FAF6F0;
            color: #3C2A21;
        }
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 2.0rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 98% !important;
        }
        .stButton>button {
            border-radius: 8px !important;
            background-color: #D9826C !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 600 !important;
        }
        .stButton>button:hover {
            background-color: #C86D51 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            margin-top: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 8px 16px;
            background-color: #EFE6DC;
            color: #5C4033;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #D9826C !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stImage"] img {
            mix-blend-mode: multiply;
            object-fit: contain;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# DEFAULT DATA
# ==========================================
DEFAULT_INGREDIENSER = [
    {"Ingrediens": "Apelsin (st)", "Pris": 6.37, "Enhet": "st", "Kalorier": 40},
    {"Ingrediens": "Bakchoklad mörk (kg)", "Pris": 199.75, "Enhet": "kg", "Kalorier": 5400},
    {"Ingrediens": "Bakpulver (kg)", "Pris": 65.00, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Bikarbonat (kg)", "Pris": 74.00, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Blåbär (kg)", "Pris": 79.00, "Enhet": "kg", "Kalorier": 570},
    {"Ingrediens": "Brunsocker (kg)", "Pris": 39.90, "Enhet": "kg", "Kalorier": 3800},
    {"Ingrediens": "Chokladknappar (kg)", "Pris": 216.70, "Enhet": "kg", "Kalorier": 5400},
    {"Ingrediens": "Egg (st)", "Pris": 1.90, "Enhet": "st", "Kalorier": 70},
    {"Ingrediens": "Filmjölk (kg)", "Pris": 22.95, "Enhet": "kg", "Kalorier": 600},
    {"Ingrediens": "Florsocker (kg)", "Pris": 31.90, "Enhet": "kg", "Kalorier": 4000},
    {"Ingrediens": "Färskost (kg)", "Pris": 112.50, "Enhet": "kg", "Kalorier": 2500},
    {"Ingrediens": "Gräddfil (kg)", "Pris": 39.00, "Enhet": "kg", "Kalorier": 1150},
    {"Ingrediens": "Havregryn (kg)", "Pris": 13.30, "Enhet": "kg", "Kalorier": 3700},
    {"Ingrediens": "Honung (kg)", "Pris": 117.00, "Enhet": "kg", "Kalorier": 3000},
    {"Ingrediens": "Ingefära (kg)", "Pris": 615.00, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Jäst (kg)", "Pris": 303.57, "Enhet": "kg", "Kalorier": 1000},
    {"Ingrediens": "Kaffe (kg)", "Pris": 435.00, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Kakao (kg)", "Pris": 194.88, "Enhet": "kg", "Kalorier": 3500},
    {"Ingrediens": "Kanel (kg)", "Pris": 587.50, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Kokosflingor (kg)", "Pris": 114.80, "Enhet": "kg", "Kalorier": 6600},
    {"Ingrediens": "Mandel (kg)", "Pris": 330.00, "Enhet": "kg", "Kalorier": 6000},
    {"Ingrediens": "Mjöl (kg)", "Pris": 7.20, "Enhet": "kg", "Kalorier": 3500},
    {"Ingrediens": "Mjölk (kg)", "Pris": 10.90, "Enhet": "kg", "Kalorier": 450},
    {"Ingrediens": "Morot (kg)", "Pris": 13.95, "Enhet": "kg", "Kalorier": 400},
    {"Ingrediens": "Nejlika (kg)", "Pris": 630.00, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Olja (kg)", "Pris": 28.24, "Enhet": "kg", "Kalorier": 8800},
    {"Ingrediens": "Rågsikt (kg)", "Pris": 9.45, "Enhet": "kg", "Kalorier": 3400},
    {"Ingrediens": "Salt (kg)", "Pris": 11.50, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Sesamfrön (kg)", "Pris": 97.33, "Enhet": "kg", "Kalorier": 5700},
    {"Ingrediens": "Smör (kg)", "Pris": 125.90, "Enhet": "kg", "Kalorier": 7200},
    {"Ingrediens": "Socker (kg)", "Pris": 23.95, "Enhet": "kg", "Kalorier": 4000},
    {"Ingrediens": "Vallmofrön (kg)", "Pris": 202.67, "Enhet": "kg", "Kalorier": 5200},
    {"Ingrediens": "Valnötter (kg)", "Pris": 167.38, "Enhet": "kg", "Kalorier": 6500},
    {"Ingrediens": "Vaniljextrakt (kg)", "Pris": 1199.00, "Enhet": "kg", "Kalorier": 0},
    {"Ingrediens": "Vaniljsocker (kg)", "Pris": 115.00, "Enhet": "kg", "Kalorier": 4000},
    {"Ingrediens": "Vispgrädde (kg)", "Pris": 74.00, "Enhet": "kg", "Kalorier": 3500},
    {"Ingrediens": "Yoghurt (kg)", "Pris": 28.50, "Enhet": "kg", "Kalorier": 600}
]

DEFAULT_TOPPINGS = ["Blåbär (kg)", "Chokladknappar (kg)", "Kokosflingor (kg)", "Valnötter (kg)", "Sesamfrön (kg)", "Vallmofrön (kg)"]

DEFAULT_RECEPT = {
    "Muffins": {"override_kostnad": 51.05, "override_kcal": 4650, "ingredienser": [{"Ingrediens": "Mjöl (kg)", "Mängd": 300}, {"Ingrediens": "Socker (kg)", "Mängd": 200}, {"Ingrediens": "Egg (st)", "Mängd": 2}]},
    "Biskvier": {"override_kostnad": 96.19, "override_kcal": 3350, "ingredienser": []},
    "Oat cookie": {"override_kostnad": 65.87, "override_kcal": 4100, "ingredienser": []},
    "Brownie": {"override_kostnad": 78.32, "override_kcal": 3850, "ingredienser": []},
    "Cookie": {"override_kostnad": 40.22, "override_kcal": 3200, "ingredienser": []},
    "Bagels": {"override_kostnad": 21.06, "override_kcal": 2850, "ingredienser": []},
    "Morotskaka": {"override_kostnad": 69.86, "override_kcal": 4400, "ingredienser": []},
    "Chokladkaka": {"override_kostnad": 143.69, "override_kcal": 9800, "ingredienser": []},
    "Kanelbullar": {"override_kostnad": 69.26, "override_kcal": 5450, "ingredienser": []},
    "Orange cake": {"override_kostnad": 48.23, "override_kcal": 820, "ingredienser": []},
    "Cinnamon loaf": {"override_kostnad": 45.27, "override_kcal": 820, "ingredienser": []}
}

DEFAULT_ORDERS = {
    "Order 11-morfar": {
        "datum": "2026-06-13",
        "rader": [
            {"Recept": "Muffins", "Topping": "Blåbär (kg)", "Mängd_g": 175, "Satser": 1.0, "Bakade": 21, "Sålda": 18, "Pris_st": 15.0},
            {"Recept": "Biskvier", "Topping": "Ingen", "Mängd_g": 0, "Satser": 1.0, "Bakade": 17, "Sålda": 17, "Pris_st": 20.0},
            {"Recept": "Oat cookie", "Topping": "Chokladknappar (kg)", "Mängd_g": 150, "Satser": 1.0, "Bakade": 24, "Sålda": 24, "Pris_st": 15.0}
        ]
    },
    "Order 7-Eivor": {
        "datum": "2026-04-29/2026-05-15",
        "rader": [
            {"Recept": "Muffins", "Topping": "Blåbär (kg)", "Mängd_g": 175, "Satser": 1.0, "Bakade": 19, "Sålda": 17, "Pris_st": 15.0},
            {"Recept": "Cookie", "Topping": "Chokladknappar (kg)", "Mängd_g": 100, "Satser": 1.0, "Bakade": 27, "Sålda": 25, "Pris_st": 10.0},
            {"Recept": "Kanelbullar", "Topping": "Ingen", "Mängd_g": 0, "Satser": 1.0, "Bakade": 38, "Sålda": 36, "Pris_st": 10.0}
        ]
    }
}

if "ingredienser" not in st.session_state:
    st.session_state.ingredienser = DEFAULT_INGREDIENSER

if "toppings_lista" not in st.session_state:
    st.session_state.toppings_lista = DEFAULT_TOPPINGS

if "recept" not in st.session_state:
    st.session_state.recept = DEFAULT_RECEPT

if "orders_db" not in st.session_state:
    st.session_state.orders_db = DEFAULT_ORDERS

if "aktiv_recept_vy" not in st.session_state:
    st.session_state.aktiv_recept_vy = None

GILTIGA_KOLUMNER = ["Ingrediens", "Pris", "Enhet", "Kalorier"]

def berakna_recept_totalt(r_namn):
    r_data = st.session_state.recept.get(r_namn, {})
    ing_lista = r_data.get("ingredienser", [])
    
    if ing_lista:
        tot_k = 0.0
        tot_kcal = 0
        ing_map = {i["Ingrediens"]: i for i in st.session_state.ingredienser if "Ingrediens" in i}
        for item in ing_lista:
            ing_namn = item.get("Ingrediens")
            mängd = float(item.get("Mängd", 0))
            if ing_namn in ing_map:
                info = ing_map[ing_namn]
                enhet = info.get("Enhet", "kg")
                faktor = (mängd / 1000.0) if enhet in ["kg", "l"] else mängd
                tot_k += info.get("Pris", 0.0) * faktor
                tot_kcal += int(info.get("Kalorier", 0) * faktor)
        return tot_k, tot_kcal
    else:
        return r_data.get("override_kostnad", 50.0), r_data.get("override_kcal", 4000)

# LOGGA HÖGST UPP
try:
    st.image("Logga.jpg", width=80)
except Exception:
    try:
        st.image("Logga.png", width=80)
    except Exception:
        pass

# FLIKAR
tab1, tab2, tab3, tab4 = st.tabs(["🥦 Ingredienser", "🍓 Toppings", "📖 Recept", "🛒 Orderbyggare"])

# ------------------------------------------
# Flik 1: Ingredienser
# ------------------------------------------
with tab1:
    st.subheader("🥦 Ingrediensbibliotek")

    df_ing = pd.DataFrame(st.session_state.ingredienser)[GILTIGA_KOLUMNER]

    # Kompakt tabell med fasta kolumnbredder och inbyggd klickbar sortering på rubrikerna
    st.dataframe(
        df_ing,
        use_container_width=False,
        hide_index=True,
        column_config={
            "Ingrediens": st.column_config.TextColumn("Ingrediens", width=220),
            "Pris": st.column_config.NumberColumn("Pris", width=100, format="%.2f kr"),
            "Enhet": st.column_config.TextColumn("Enhet", width=80),
            "Kalorier": st.column_config.NumberColumn("Kalorier", width=100, format="%d")
        }
    )

    with st.expander("➕ / ✏️ Lägg till eller redigera ingredienser"):
        edited_ing_df = st.data_editor(
            pd.DataFrame(st.session_state.ingredienser)[GILTIGA_KOLUMNER],
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "Ingrediens": st.column_config.TextColumn("Ingrediens", width=180, required=True),
                "Pris": st.column_config.NumberColumn("Pris", width=80, format="%.2f kr", min_value=0.0),
                "Enhet": st.column_config.SelectboxColumn("Enhet", width=60, options=["kg", "st", "l", "g"], required=True),
                "Kalorier": st.column_config.NumberColumn("Kalorier", width=80, min_value=0)
            },
            key="ingrediens_editor"
        )
        st.session_state.ingredienser = edited_ing_df.to_dict(orient="records")

# ------------------------------------------
# Flik 2: Toppings
# ------------------------------------------
with tab2:
    st.subheader("🍓 Hantera Toppings")
    col2, _ = st.columns([5, 5])
    with col2:
        alla_ingredienser = sorted([i["Ingrediens"] for i in st.session_state.ingredienser if i.get("Ingrediens")])
        
        st.markdown("##### Lägg till ny topping")
        c_sel, c_btn = st.columns([3, 2])
        with c_sel:
            ny_topping = st.selectbox("Välj ingrediens:", alla_ingredienser, label_visibility="collapsed")
        with c_btn:
            if st.button("➕ Lägg till"):
                if ny_topping and ny_topping not in st.session_state.toppings_lista:
                    st.session_state.toppings_lista.append(ny_topping)
                    st.rerun()

        st.markdown("---")
        st.markdown("##### Befintliga Toppings")
        top_to_remove = None
        for idx, t in enumerate(st.session_state.toppings_lista):
            col_t, col_del = st.columns([4, 1])
            with col_t:
                st.write(f"• **{t}**")
            with col_del:
                if st.button("🗑️ Radera", key=f"del_top_{idx}"):
                    top_to_remove = t

        if top_to_remove:
            st.session_state.toppings_lista.remove(top_to_remove)
            st.rerun()

# ------------------------------------------
# Flik 3: Recept & Receptbyggare
# ------------------------------------------
with tab3:
    st.subheader("📖 Receptöversikt & Byggare")
    
    if st.session_state.aktiv_recept_vy is not None:
        r_namn_aktiv = st.session_state.aktiv_recept_vy
        is_new = (r_namn_aktiv == "NYTT")
        
        st.markdown(f"### {'➕ Skapa Nytt Recept' if is_new else f'✏️ Redigera Recept: {r_namn_aktiv}'}")
        
        nuvarande_data = st.session_state.recept.get(r_namn_aktiv, {"ingredienser": [], "override_kostnad": 0.0, "override_kcal": 0})
        recept_namn_input = st.text_input("Receptnamn:", value="" if is_new else r_namn_aktiv)
        
        st.markdown("#### Ingredienser i receptet")
        st.caption("Mängd anges i gram (för kg-varor) eller antal (för st-varor).")
        
        df_ing_recept = pd.DataFrame(nuvarande_data.get("ingredienser", []))
        if df_ing_recept.empty:
            df_ing_recept = pd.DataFrame([{"Ingrediens": "", "Mängd": 0.0}])
            
        alla_ing_namn = sorted([i["Ingrediens"] for i in st.session_state.ingredienser if i.get("Ingrediens")])
        
        edited_rec_ing = st.data_editor(
            df_ing_recept,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "Ingrediens": st.column_config.SelectboxColumn("Ingrediens", width=200, options=alla_ing_namn, required=True),
                "Mängd": st.column_config.NumberColumn("Mängd (g / st)", width=120, min_value=0.0, step=1.0, format="%.1f")
            },
            key="editor_recept_detaljer"
        )
        
        ing_map = {i["Ingrediens"]: i for i in st.session_state.ingredienser if "Ingrediens" in i}
        live_k = 0.0
        live_kcal = 0
        rader_dict = edited_rec_ing.to_dict(orient="records")
        
        for item in rader_dict:
            i_namn = item.get("Ingrediens")
            mängd = float(item.get("Mängd", 0))
            if i_namn in ing_map:
                info = ing_map[i_namn]
                enhet = info.get("Enhet", "kg")
                faktor = (mängd / 1000.0) if enhet in ["kg", "l"] else mängd
                live_k += info.get("Pris", 0.0) * faktor
                live_kcal += int(info.get("Kalorier", 0) * faktor)
                
        c_k, c_kc = st.columns(2)
        c_k.metric("Beräknad Kostnad för sats", f"{live_k:.2f} kr")
        c_kc.metric("Beräknade Kalorier för sats", f"{live_kcal} kcal")
        
        c_spara, c_avbryt = st.columns([1, 1])
        with c_spara:
            if st.button("💾 Spara Recept", use_container_width=True):
                if recept_namn_input.strip():
                    if not is_new and recept_namn_input != r_namn_aktiv:
                        del st.session_state.recept[r_namn_aktiv]
                    
                    st.session_state.recept[recept_namn_input.strip()] = {
                        "ingredienser": [r for r in rader_dict if r.get("Ingrediens")],
                        "override_kostnad": live_k,
                        "override_kcal": live_kcal
                    }
                    st.session_state.aktiv_recept_vy = None
                    st.rerun()
                else:
                    st.error("Ange ett receptnamn!")
        with c_avbryt:
            if st.button("❌ Avbryt", use_container_width=True):
                st.session_state.aktiv_recept_vy = None
                st.rerun()

    else:
        col_main, _ = st.columns([6, 6])
        with col_main:
            if st.button("➕ Skapa nytt recept"):
                st.session_state.aktiv_recept_vy = "NYTT"
                st.rerun()
                
            st.markdown("---")
            
            recept_lista_ta_bort = None
            for r_namn in sorted(list(st.session_state.recept.keys())):
                k, kcal = berakna_recept_totalt(r_namn)
                col_r1, col_r2, col_r3, col_r4 = st.columns([4, 4, 1, 1])
                with col_r1:
                    st.write(f"**{r_namn}**")
                with col_r2:
                    st.caption(f"{k:.2f} kr | {kcal} kcal")
                with col_r3:
                    if st.button("✏️", key=f"edit_rec_{r_namn}"):
                        st.session_state.aktiv_recept_vy = r_namn
                        st.rerun()
                with col_r4:
                    if st.button("🗑️", key=f"del_rec_{r_namn}"):
                        recept_lista_ta_bort = r_namn

            if recept_lista_ta_bort:
                del st.session_state.recept[recept_lista_ta_bort]
                st.rerun()

# ------------------------------------------
# Flik 4: Orderbyggare
# ------------------------------------------
with tab4:
    st.subheader("🛒 Orderbyggare")
    
    valj_order_nycklar = list(st.session_state.orders_db.keys())
    valj_order = st.selectbox(
        "📋 Välj order att granska eller redigera:", 
        valj_order_nycklar,
        format_func=lambda x: f"{x} ({st.session_state.orders_db[x]['datum']})"
    )

    nuvarande_order = st.session_state.orders_db[valj_order]
    st.markdown(f"### {valj_order}")
    st.caption(f"Datum: {nuvarande_order['datum']}")

    with st.expander("✏️ Redigera orderrader & toppings", expanded=True):
        rader_ta_bort = []
        recept_lista_sorterad = sorted(list(st.session_state.recept.keys()))
        
        for idx, r in enumerate(nuvarande_order["rader"]):
            st.markdown(f"**Rad {idx+1}: {r.get('Recept', 'Recept')}**")
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
            
            nuvarande_recept = r.get("Recept")
            idx_recept = recept_lista_sorterad.index(nuvarande_recept) if nuvarande_recept in recept_lista_sorterad else 0
            
            with c1:
                r["Recept"] = st.selectbox("Recept", recept_lista_sorterad, index=idx_recept, key=f"rec_{valj_order}_{idx}")
            with c2:
                r["Satser"] = st.number_input("Satser", min_value=0.1, value=float(r.get("Satser", 1.0)), step=0.1, key=f"sat_{valj_order}_{idx}")
            with c3:
                r["Bakade"] = st.number_input("Bakade (st)", min_value=1, value=int(r.get("Bakade", 1)), key=f"bak_{valj_order}_{idx}")
            with c4:
                r["Sålda"] = st.number_input("Sålda (st)", min_value=0, value=int(r.get("Sålda", 0)), key=f"sal_{valj_order}_{idx}")
            with c5:
                r["Pris_st"] = st.number_input("Pris/st (kr)", min_value=0.0, value=float(r.get("Pris_st", 0.0)), step=0.5, key=f"prs_{valj_order}_{idx}")

            existerande_toppings = r.get("Toppings_dict", {})
            if not existerande_toppings and r.get("Topping") and r.get("Topping") != "Ingen":
                existerande_toppings = {r["Topping"]: r.get("Mängd_g", 0)}

            valda_toppings = st.multiselect(
                "Välj Toppings:",
                options=sorted(st.session_state.toppings_lista),
                default=list(existerande_toppings.keys()),
                key=f"top_multi_{valj_order}_{idx}"
            )

            nya_toppings_dict = {}
            if valda_toppings:
                top_cols = st.columns(len(valda_toppings))
                for t_idx, t_namn in enumerate(valda_toppings):
                    with top_cols[t_idx]:
                        start_mängd = float(existerande_toppings.get(t_namn, 50))
                        nya_toppings_dict[t_namn] = st.number_input(
                            f"Mängd {t_namn} (g/st):",
                            min_value=0.0,
                            value=start_mängd,
                            step=5.0,
                            key=f"mngd_{valj_order}_{idx}_{t_namn}"
                        )
            
            r["Toppings_dict"] = nya_toppings_dict
            
            if st.button("🗑️ Ta bort rad", key=f"del_row_{valj_order}_{idx}"):
                rader_ta_bort.append(idx)
            st.markdown("---")

        if rader_ta_bort:
            for index in sorted(rader_ta_bort, reverse=True):
                nuvarande_order["rader"].pop(index)
            st.rerun()

        if st.button("➕ Lägg till ny orderrad"):
            nuvarande_order["rader"].append({
                "Recept": recept_lista_sorterad[0] if recept_lista_sorterad else "",
                "Toppings_dict": {},
                "Satser": 1.0,
                "Bakade": 10,
                "Sålda": 10,
                "Pris_st": 15.0
            })
            st.rerun()

    # Beräkningar & Tabellvisning för Orderbyggare
    ing_map = {i["Ingrediens"]: i for i in st.session_state.ingredienser if "Ingrediens" in i}
    table_rows = []
    tot_bakade, tot_salda, tot_kostnad, tot_vinst, tot_pris, tot_kalorier_sats = 0, 0, 0.0, 0.0, 0.0, 0

    for r in nuvarande_order["rader"]:
        rec_k, rec_kcal = berakna_recept_totalt(r.get("Recept", ""))
        
        top_k_tot = 0.0
        top_kcal_tot = 0
        top_beskrivning_list = []
        top_mängd_list = []

        top_dict = r.get("Toppings_dict", {})
        for t_namn, m_g in top_dict.items():
            if t_namn in ing_map and m_g > 0:
                t_info = ing_map[t_namn]
                enhet = t_info.get("Enhet", "kg")
                faktor = (m_g / 1000.0) if enhet in ["kg", "l"] else m_g
                
                top_k_tot += t_info.get("Pris", 0.0) * faktor
                top_kcal_tot += int(t_info.get("Kalorier", 0) * faktor)
                
                top_beskrivning_list.append(t_namn)
                top_mängd_list.append(f"{int(m_g)}g" if enhet == "kg" else f"{int(m_g)}st")

        rad_satser = float(r.get("Satser", 1.0))
        rad_bakade = int(r.get("Bakade", 1))
        rad_salda = int(r.get("Sålda", 0))
        rad_pris_st = float(r.get("Pris_st", 0.0))

        rad_tot_kostnad = (rec_k * rad_satser) + top_k_tot
        rad_kostnad_bakad = rad_tot_kostnad / rad_bakade if rad_bakade > 0 else 0
        rad_kostnad_sald = rad_tot_kostnad / rad_salda if rad_salda > 0 else 0
        
        rad_tot_intakt = rad_salda * rad_pris_st
        rad_vinst = rad_tot_intakt - rad_tot_kostnad
        rad_vinstpaslag = (rad_vinst / rad_tot_kostnad * 100) if rad_tot_kostnad > 0 else 0
        
        rad_kalorier_sats = int((rec_kcal * rad_satser) + top_kcal_tot)
        rad_kalorier_st = int(rad_kalorier_sats / rad_bakade) if rad_bakade > 0 else 0

        tot_bakade += rad_bakade
        tot_salda += rad_salda
        tot_kostnad += rad_tot_kostnad
        tot_vinst += rad_vinst
        tot_pris += rad_tot_intakt
        tot_kalorier_sats += rad_kalorier_sats

        table_rows.append({
            "Recept": r.get("Recept", ""),
            "Toppings": ", ".join(top_beskrivning_list) if top_beskrivning_list else "-",
            "Mängd": ", ".join(top_mängd_list) if top_mängd_list else "-",
            "Topping kr": f"{top_k_tot:.2f} kr" if top_k_tot > 0 else "-",
            "Topping kcal": f"{top_kcal_tot} kcal" if top_kcal_tot > 0 else "-",
            "Satser": f"{rad_satser:.1f}",
            "Bakade": f"{rad_bakade} st",
            "Sålda": f"{rad_salda} st",
            "Kostnad": f"{round(rad_tot_kostnad)} kr",
            "Kostnad/bakad kaka": f"{rad_kostnad_bakad:.1f} kr",
            "Kostnad/såld kaka": f"{rad_kostnad_sald:.1f} kr",
            "Pris/cookie": f"{int(rad_pris_st)} kr",
            "vinstpåslag": f"{int(rad_vinstpaslag)}%",
            "vinst": f"{int(rad_vinst)} kr",
            "Pris": f"{int(rad_tot_intakt)} kr",
            "Kalorier/sats": f"{rad_kalorier_sats} kcal",
            "Kalorier/st": f"{rad_kalorier_st} kcal"
        })

    tot_vinstpaslag = (tot_vinst / tot_kostnad * 100) if tot_kostnad > 0 else 0
    tot_snitt_bakad = tot_kostnad / tot_bakade if tot_bakade > 0 else 0
    tot_snitt_sald = tot_kostnad / tot_salda if tot_salda > 0 else 0
    tot_snitt_pris = tot_pris / tot_salda if tot_salda > 0 else 0

    table_rows.append({
        "Recept": "Tot",
        "Toppings": "", "Mängd": "", "Topping kr": "", "Topping kcal": "",
        "Satser": "",
        "Bakade": f"{tot_bakade} st",
        "Sålda": f"{tot_salda} st",
        "Kostnad": f"{round(tot_kostnad)} kr",
        "Kostnad/bakad kaka": f"{tot_snitt_bakad:.1f} kr",
        "Kostnad/såld kaka": f"{tot_snitt_sald:.1f} kr",
        "Pris/cookie": f"{int(tot_snitt_pris)} kr",
        "vinstpåslag": f"{int(tot_vinstpaslag)}%",
        "vinst": f"{int(tot_vinst)} kr",
        "Pris": f"{int(tot_pris)} kr",
        "Kalorier/sats": f"{tot_kalorier_sats} kcal",
        "Kalorier/st": ""
    })

    df_display = pd.DataFrame(table_rows)

    def fargkoda_kolumner(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        farger = {
            "grå": "background-color: #E2E8F0; color: #1E293B;",
            "gul": "background-color: #FEF9C3; color: #713F12;",
            "vit": "background-color: #FFFFFF; color: #0F172A;",
            "rosa": "background-color: #FCE7F3; color: #831843;",
            "grön": "background-color: #DCFCE7; color: #14532D;",
            "blå": "background-color: #DBEAFE; color: #1E3A8A;",
            "beige": "background-color: #FEF3C7; color: #78350F;",
            "tot_rad": "background-color: #475569; color: #FFFFFF; font-weight: bold;"
        }

        styles["Recept"] = farger["grå"]
        styles["Toppings"] = farger["gul"]
        styles["Mängd"] = farger["gul"]
        styles["Topping kr"] = farger["gul"]
        styles["Topping kcal"] = farger["gul"]
        styles["Satser"] = farger["vit"]
        styles["Bakade"] = farger["rosa"]
        styles["Sålda"] = farger["rosa"]
        styles["Kostnad"] = farger["grön"]
        styles["Kostnad/bakad kaka"] = farger["grön"]
        styles["Kostnad/såld kaka"] = farger["grön"]
        styles["Pris/cookie"] = farger["blå"]
        styles["vinstpåslag"] = farger["blå"]
        styles["vinst"] = farger["blå"]
        styles["Pris"] = farger["blå"]
        styles["Kalorier/sats"] = farger["beige"]
        styles["Kalorier/st"] = farger["beige"]

        tot_idx = df[df["Recept"] == "Tot"].index
        for idx in tot_idx:
            styles.loc[idx] = farger["tot_rad"]

        return styles

    styled_df = df_display.style.apply(fargkoda_kolumner, axis=None)

    st.markdown("#### 📊 Sammanställning & Kalkyl")
    st.dataframe(
        styled_df,
        hide_index=True,
        column_config={
            "Recept": st.column_config.TextColumn("Recept", width=100),
            "Toppings": st.column_config.TextColumn("Toppings", width=120),
            "Mängd": st.column_config.TextColumn("Mängd", width=65),
            "Topping kr": st.column_config.TextColumn("Topping kr", width=85),
            "Topping kcal": st.column_config.TextColumn("Topping kcal", width=95),
            "Satser": st.column_config.TextColumn("Satser", width=60),
            "Bakade": st.column_config.TextColumn("Bakade", width=65),
            "Sålda": st.column_config.TextColumn("Sålda", width=60),
            "Kostnad": st.column_config.TextColumn("Kostnad", width=70),
            "Kostnad/bakad kaka": st.column_config.TextColumn("Kostnad/bakad kaka", width=120),
            "Kostnad/såld kaka": st.column_config.TextColumn("Kostnad/såld kaka", width=115),
            "Pris/cookie": st.column_config.TextColumn("Pris/cookie", width=85),
            "vinstpåslag": st.column_config.TextColumn("vinstpåslag", width=85),
            "vinst": st.column_config.TextColumn("vinst", width=65),
            "Pris": st.column_config.TextColumn("Pris", width=65),
            "Kalorier/sats": st.column_config.TextColumn("Kalorier/sats", width=95),
            "Kalorier/st": st.column_config.TextColumn("Kalorier/st", width=85)
        }
    )
