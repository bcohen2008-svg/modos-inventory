import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="MODOS Flooring Capacity Calculator", layout="wide", page_icon="📊")

class InventoryCapacityEngine:
    def __init__(self):
        self.aliases = {
            "f300": "f300", "f 300": "f300", "פריימר f300": "f300", "f300 פריימר": "f300",
            "paviseal 300": "f300", "paviseal300": "f300",
            "f700": "f700", "f 700": "f700", "paviseal 700": "f700",
            "hidrofugante / f700": "f700", "hidrofugante/f700": "f700",
            "hidrofugante": "f700", "hidrofugante 6772": "f700",
            "lithim silicate": "lithium silicate", "lithium silicate": "lithium silicate",
            "silicato litio": "lithium silicate", "silica litio": "lithium silicate",
            "decopox": "decopox", "decopox (a+b)": "decopox", "דקופוקס": "decopox",
            "eco fondo 1": "ecofondo one", "ecofondo 1": "ecofondo one",
            "ecofondo one": "ecofondo one", "ecofondo one a+b+c": "ecofondo one",
            "ecopox cem": "ecopox cem", "ecopoxcem plus comp a": "ecopox cem",
            "ecopoxcem plus comp b": "ecopox cem", "ecopoxcem plus comp c": "ecopox cem",
            "ecopox cem plus 3c": "ecopox cem", "ecopox cem (3c)": "ecopox cem",
            "orfapol 50": "orfapol 50", "orfapol 50 mate": "orfapol 50",
            "orfapol plus": "orfapol plus", "veladura": "veladura", "veladura transparent": "veladura",
            "pavex primer": "pavex primer", "pavex primer plus": "pavex primer",
            "stone pool base": "stone pool base", "stone pool base grueso": "stone pool base",
            "stone pool fino": "stone pool fino", "stone pool fino neutro": "stone pool fino",
            "stone pool base resin": "stone pool base resin", "stone pool fine resin": "stone pool fine resin",
            "pavimper": "pavimper", "pavimper 2c": "pavimper"
        }
        self.unlimited_terms = ["quartz", "pigment", "accelerator", "sand", "קוורץ", "פיגמנט", "אקסלרטור"]

    def normalize(self, text: str) -> str:
        return self.aliases.get(str(text).strip().lower(), str(text).strip().lower())

    def is_unlimited(self, text: str) -> bool:
        norm = str(text).strip().lower()
        return any(term in norm for term in self.unlimited_terms)

    def calculate(self, inventory_df: pd.DataFrame, recipes_df: pd.DataFrame, system_name: str) -> dict:
        inv = inventory_df.copy()
        rec = recipes_df.copy()
        inv["item_norm"] = inv["Item"].astype(str).apply(self.normalize)
        rec["system_norm"] = rec["System"].astype(str).apply(self.normalize)
        rec["item_norm"] = rec["Item"].astype(str).apply(self.normalize)

        target_norm = self.normalize(system_name)
        sys_recipe = rec[rec["system_norm"] == target_norm].copy()

        if sys_recipe.empty:
            raise ValueError(f"System '{system_name}' not found.")

        inv_agg = inv.groupby("item_norm", as_index=False)["Quantity"].sum()
        merged = pd.merge(sys_recipe, inv_agg, on="item_norm", how="left")
        merged["Quantity"] = merged["Quantity"].fillna(0.0)

        merged["is_unlimited"] = merged["item_norm"].apply(self.is_unlimited)
        merged["Rate"] = merged["Rate"].replace(0, np.nan)

        merged["meters_possible"] = np.where(
            merged["is_unlimited"],
            np.inf,
            np.where(merged["Rate"].isna(), np.nan, merged["Quantity"] / merged["Rate"])
        )

        finite_capacities = merged[~merged["is_unlimited"]]["meters_possible"]
        max_meters = float(finite_capacities.min()) if not finite_capacities.empty else 0.0
        bottleneck_item = merged.loc[merged["meters_possible"].idxmin()]["Item"] if not finite_capacities.empty else "None"

        merged["used_at_max"] = merged["Rate"] * max_meters
        merged["unused_leftover"] = np.where(
            merged["is_unlimited"],
            np.nan,
            merged["Quantity"] - merged["used_at_max"]
        )

        merged["status"] = np.where(
            merged["is_unlimited"],
            "Unlimited Material",
            np.where(np.isclose(merged["meters_possible"], max_meters), "⚠️ LIMITING BOTTLENECK", "Sufficient")
        )

        display_df = pd.DataFrame({
            "Component": merged["Item"],
            "Available Stock": merged["Quantity"],
            "Rate / m²": merged["Rate"],
            "Meters for Product (m²)": merged["meters_possible"].apply(lambda x: "Unlimited" if np.isinf(x) else round(x, 2)),
            "Used at System Max": merged["used_at_max"].apply(lambda x: round(x, 2)),
            "Unused Leftover": merged["unused_leftover"].apply(lambda x: "Unlimited" if np.isnan(x) else round(x, 2)),
            "Status": merged["status"]
        })

        return {
            "system": system_name,
            "max_meters": round(max_meters, 2),
            "bottleneck": bottleneck_item,
            "table": display_df
        }

st.title("🏗️ MODOS Flooring Inventory & Capacity Dashboard")
st.markdown("Real-time bottleneck and yield calculator with editable inventory.")

default_inv = [
    {"Item": "Paviseal 300", "Quantity": 1040.0, "Unit": "L"},
    {"Item": "Paviseal 700", "Quantity": 25.0, "Unit": "kg"},
    {"Item": "Decopox", "Quantity": 250.0, "Unit": "kg"},
    {"Item": "Pavex Primer", "Quantity": 45.0, "Unit": "kg"},
    {"Item": "Veladura", "Quantity": 75.0, "Unit": "kg"},
    {"Item": "Orfapol 50", "Quantity": 98.4, "Unit": "kg"},
    {"Item": "Stone Pool Base", "Quantity": 1250.0, "Unit": "kg"},
    {"Item": "Stone Pool Base Resin", "Quantity": 135.0, "Unit": "L"},
    {"Item": "Stone Pool Fino", "Quantity": 525.0, "Unit": "kg"},
    {"Item": "Stone Pool Fine Resin", "Quantity": 252.5, "Unit": "L"},
    {"Item": "Lithium Silicate", "Quantity": 42.0, "Unit": "kg"},
    {"Item": "Ecopox CEM", "Quantity": 60.0, "Unit": "kg"},
    {"Item": "ECofondo One", "Quantity": 392.0, "Unit": "kg"},
    {"Item": "Orfapol Plus", "Quantity": 20.0, "Unit": "kg"},
    {"Item": "Pavimper", "Quantity": 0.0, "Unit": "kg"}
]

recipes_data = [
    {"System": "Decopox Standard", "Item": "פריימר F300", "Rate": 0.02},
    {"System": "Decopox Standard", "Item": "Pavex Primer", "Rate": 0.30},
    {"System": "Decopox Standard", "Item": "Small Quartz", "Rate": 0.30},
    {"System": "Decopox Standard", "Item": "Decopox", "Rate": 1.00},
    {"System": "Decopox Standard", "Item": "Color Pigment", "Rate": 0.025},
    {"System": "Decopox Standard", "Item": "Veladura", "Rate": 0.10},
    {"System": "Decopox Standard", "Item": "Orfapol 50", "Rate": 0.10},
    {"System": "Stone Pool", "Item": "פריימר F300", "Rate": 0.04},
    {"System": "Stone Pool", "Item": "Stone Pool Base", "Rate": 4.00},
    {"System": "Stone Pool", "Item": "Stone Pool Base Resin", "Rate": 1.00},
    {"System": "Stone Pool", "Item": "Stone Pool Fino", "Rate": 3.00},
    {"System": "Stone Pool", "Item": "Stone Pool Fine Resin", "Rate": 1.00},
    {"System": "Stone Pool", "Item": "Lithim Silicate", "Rate": 0.01},
    {"System": "Stone Pool", "Item": "Hidrofugante / F700", "Rate": 0.005},
    {"System": "Decopox Ecopox CEM", "Item": "פריימר F300", "Rate": 0.02},
    {"System": "Decopox Ecopox CEM", "Item": "Ecopox CEM", "Rate": 1.20},
    {"System": "Decopox Ecopox CEM", "Item": "Small Quartz", "Rate": 0.15},
    {"System": "Decopox Ecopox CEM", "Item": "Decopox", "Rate": 1.00},
    {"System": "Decopox Ecopox CEM", "Item": "Color Pigment", "Rate": 0.025},
    {"System": "Decopox Ecopox CEM", "Item": "Veladura", "Rate": 0.10},
    {"System": "Decopox Ecopox CEM", "Item": "Orfapol 50", "Rate": 0.10},
    {"System": "Decopox EcoFondo 1", "Item": "פריימר F300", "Rate": 0.02},
    {"System": "Decopox EcoFondo 1", "Item": "Eco Fondo 1", "Rate": 2.80},
    {"System": "Decopox EcoFondo 1", "Item": "Small Quartz", "Rate": 0.15},
    {"System": "Decopox EcoFondo 1", "Item": "Decopox", "Rate": 1.00},
    {"System": "Decopox EcoFondo 1", "Item": "Color Pigment", "Rate": 0.025},
    {"System": "Decopox EcoFondo 1", "Item": "Veladura", "Rate": 0.10},
    {"System": "Decopox EcoFondo 1", "Item": "Orfapol 50", "Rate": 0.10}
]

rec_df = pd.DataFrame(recipes_data)
engine = InventoryCapacityEngine()

st.sidebar.header("📁 Data Source")
uploaded_file = st.sidebar.file_uploader("Upload Updated Inventory (.xlsx / .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        inv_df = pd.read_csv(uploaded_file)
    else:
        inv_df = pd.read_excel(uploaded_file)
else:
    inv_df = pd.DataFrame(default_inv)

st.subheader("📝 Live Editable Warehouse Inventory")
st.caption("Double-click any quantity below to edit live. All systems will recalculate instantly.")
edited_inv_df = st.data_editor(inv_df, num_rows="dynamic", use_container_width=True)

systems = ["Decopox Standard", "Stone Pool", "Decopox Ecopox CEM", "Decopox EcoFondo 1"]
results = {}
summary_list = []

for s in systems:
    res = engine.calculate(edited_inv_df, rec_df, s)
    results[s] = res
    summary_list.append({
        "System Name": res["system"],
        "Max Yield (m²)": f"{res['max_meters']:.2f} m²",
        "Limiting Bottleneck": res["bottleneck"]
    })

st.markdown("---")
st.subheader("📊 Executive Summary")
cols = st.columns(len(systems))
for i, s in enumerate(systems):
    res = results[s]
    cols[i].metric(label=s, value=f"{res['max_meters']} m²", delta=f"Bottleneck: {res['bottleneck']}", delta_color="inverse")

st.markdown("---")
st.subheader("🔍 Detailed Product Breakdown & Leftover Inventory")
tabs = st.tabs(systems)

for i, s in enumerate(systems):
    with tabs[i]:
        res = results[s]
        st.dataframe(res["table"], use_container_width=True)

excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    pd.DataFrame(summary_list).to_excel(writer, sheet_name="Executive Summary", index=False)
    for s in systems:
        results[s]["table"].to_excel(writer, sheet_name=s[:31], index=False)

st.download_button(
    label="📥 Download Updated Excel Report",
    data=excel_buffer.getvalue(),
    file_name="MODOS_Live_Capacity_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
