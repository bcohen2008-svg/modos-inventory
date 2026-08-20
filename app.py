import streamlit as st
import pandas as pd
import numpy as np
import math
import io

st.set_page_config(page_title="MODOS Flooring Inventory & Project Calculator", layout="wide", page_icon="🏗️")

# -------------------------------------------------------------
# ENGINE DEFINITION
# -------------------------------------------------------------
class InventoryCapacityEngine:
    def __init__(self):
        self.aliases = {
            # F300 (Paviseal 300)
            "f300": "f300", "f 300": "f300", "פריימר f300": "f300", "f300 פריימר": "f300",
            "paviseal 300": "f300", "paviseal300": "f300", "paviseal 300 (f300)": "f300",
            
            # F700 / Hidrofugante
            "f700": "f700", "f 700": "f700", "paviseal 700": "f700", "paviseal 700 (f700)": "f700",
            "hidrofugante / f700": "f700", "hidrofugante/f700": "f700",
            "hidrofugante": "f700", "hidrofugante 6772": "f700",
            
            # Silicate
            "lithim silicate": "lithium silicate", "lithium silicate": "lithium silicate",
            "silicato litio": "lithium silicate", "silica litio": "lithium silicate",
            
            # Decopox
            "decopox": "decopox", "decopox (a+b)": "decopox", "דקופוקס": "decopox",
            
            # EcoFondo 1
            "eco fondo 1": "ecofondo one", "ecofondo 1": "ecofondo one",
            "ecofondo one": "ecofondo one", "ecofondo one a+b+c": "ecofondo one",
            
            # Ecopox CEM
            "ecopox cem": "ecopox cem", "ecopoxcem plus comp a": "ecopox cem",
            "ecopoxcem plus comp b": "ecopox cem", "ecopoxcem plus comp c": "ecopox cem",
            "ecopox cem plus 3c": "ecopox cem", "ecopox cem (3c)": "ecopox cem",
            
            # Topcoats & Glazes
            "orfapol 50": "orfapol 50", "orfapol 50 mate": "orfapol 50",
            "orfapol plus": "orfapol plus", "veladura": "veladura", "veladura transparent": "veladura",
            
            # Primers (Modos Epoxy Primer = Pavex Primer)
            "pavex primer": "pavex primer", "pavex primer plus": "pavex primer",
            "modos epoxy primer": "pavex primer", "modos epoxy primer a": "pavex primer", "modos epoxy primer b": "pavex primer",
            
            # Distinct Stonefeel Powders
            "stonefeel pool base grueso": "stonefeel base grueso",
            "stone pool base grueso": "stonefeel base grueso",
            "stonefeel base grueso": "stonefeel base grueso",
            "stone pool base": "stonefeel base grueso",
            
            "stonefeel grueso neutro": "stonefeel grueso",
            "stonefeel grueso": "stonefeel grueso",
            "stone pool grueso": "stonefeel grueso",
            
            # Fino Colors
            "stonefeel pool fino nuetro": "stonefeel fino (neutro)",
            "stonefeel pool fino neutro": "stonefeel fino (neutro)",
            "stonefeel fino (neutro)": "stonefeel fino (neutro)",
            "stonefeel pool fino tiffra": "stonefeel fino (tiffra)",
            "stonefeel fino (tiffra)": "stonefeel fino (tiffra)",
            "stonefeel pool fino hueso": "stonefeel fino (hueso)",
            "stonefeel fino (hueso)": "stonefeel fino (hueso)",
            "stonefeel pool fino jade": "stonefeel fino (jade)",
            "stonefeel fino (jade)": "stonefeel fino (jade)",
            "stonefeel fino": "stonefeel fino (total)",
            "stone pool fino": "stonefeel fino (total)",
            
            "stone feel base fina 0.4": "stone feel base fina 0.4",
            "stone feel base fina": "stone feel base fina 0.4",
            "stonefeel base fina": "stone feel base fina 0.4",
            
            # Base Resin
            "stone feel pool base": "stonefeel base resin",
            "stone pool base resin": "stonefeel base resin",
            "stonepool 2c base": "stonefeel base resin",
            "stonefeel base 2c": "stonefeel base resin",
            "stonepool base": "stonefeel base resin",
            
            # Fine / Finish Resin
            "stone feel pool finish": "stonefeel fine resin",
            "stone pool fine resin": "stonefeel fine resin",
            "stonepool finish": "stonefeel fine resin",
            "stonefeel finish 2c": "stonefeel fine resin",
            "stonepool 2c finish": "stonefeel fine resin",
            "stonepool 2c abacado": "stonefeel fine resin"
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
        
        fino_color_items = [
            "stonefeel fino (neutro)", "stonefeel fino (tiffra)",
            "stonefeel fino (hueso)", "stonefeel fino (jade)"
        ]
        fino_total_qty = inv_agg[inv_agg["item_norm"].isin(fino_color_items)]["Quantity"].sum()
        
        if "stonefeel fino (total)" not in inv_agg["item_norm"].values and fino_total_qty > 0:
            inv_agg = pd.concat([inv_agg, pd.DataFrame([{"item_norm": "stonefeel fino (total)", "Quantity": fino_total_qty}])], ignore_index=True)
            
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
        
        color_breakdown = []
        if any("fino" in item for item in sys_recipe["item_norm"]):
            rate_row = sys_recipe[sys_recipe["item_norm"] == "stonefeel fino (total)"]
            if not rate_row.empty:
                fino_rate = float(rate_row["Rate"].iloc[0])
                for color_name in ["Neutro", "Tiffra", "Hueso", "Jade"]:
                    color_key = f"stonefeel fino ({color_name.lower()})"
                    qty_val = float(inv_agg[inv_agg["item_norm"] == color_key]["Quantity"].sum()) if color_key in inv_agg["item_norm"].values else 0.0
                    m2_color = qty_val / fino_rate if fino_rate > 0 else 0.0
                    color_breakdown.append({
                        "Fino Color": color_name,
                        "Stock (kg)": qty_val,
                        "Rate / m²": fino_rate,
                        "Meters Possible (m²)": round(m2_color, 2)
                    })

        return {
            "system": system_name,
            "max_meters": round(max_meters, 2),
            "bottleneck": bottleneck_item,
            "table": display_df,
            "color_breakdown": pd.DataFrame(color_breakdown) if color_breakdown else None
        }

# -------------------------------------------------------------
# APP INTERFACE
# -------------------------------------------------------------
st.title("🏗️ MODOS Flooring Master Inventory & Project Calculator")
st.markdown("Real-time bottleneck and capacity analyzer with a dedicated project materials estimator (no prices).")

# Full Master Warehouse Inventory
full_warehouse_master_inv = [
    {"Item": "Paviseal 300 (F300)", "Size/Packaging": "1000L IBC + 8x 5L Pails", "Quantity": 1040.0, "Unit": "L", "Category": "Primer / Sealer"},
    {"Item": "Paviseal 700 (F700)", "Size/Packaging": "24x 1kg Bottles + 1kg Hidrofugante", "Quantity": 25.0, "Unit": "kg", "Category": "Topcoat / Sealer"},
    {"Item": "Decopox", "Size/Packaging": "25x 10kg Kits (225kg A + 25kg B)", "Quantity": 250.0, "Unit": "kg", "Category": "Decopox Complete"},
    {"Item": "Pavex Primer", "Size/Packaging": "Pavex Plus (45kg) + Modos Epoxy Primer (30kg)", "Quantity": 75.0, "Unit": "kg", "Category": "Primer"},
    {"Item": "Veladura", "Size/Packaging": "15x 5kg Pails", "Quantity": 75.0, "Unit": "kg", "Category": "Glaze / Topcoat"},
    {"Item": "Orfapol 50", "Size/Packaging": "14x 6kg + 7x 1.2kg Sets + Extra", "Quantity": 98.4, "Unit": "kg", "Category": "Polyurethane Topcoat"},
    {"Item": "Stonefeel base grueso", "Size/Packaging": "49x 25kg Bags", "Quantity": 1225.0, "Unit": "kg", "Category": "Stonefeel Powder"},
    {"Item": "Stonefeel grueso", "Size/Packaging": "32x 25kg Bags", "Quantity": 800.0, "Unit": "kg", "Category": "Stonefeel Powder"},
    {"Item": "Stonefeel fino (Neutro)", "Size/Packaging": "19x 25kg Bags", "Quantity": 475.0, "Unit": "kg", "Category": "Stonefeel Powder"},
    {"Item": "Stonefeel fino (Tiffra)", "Size/Packaging": "2x 25kg Bags", "Quantity": 50.0, "Unit": "kg", "Category": "Stonefeel Powder"},
    {"Item": "Stonefeel fino (Hueso)", "Size/Packaging": "25kg Bags", "Quantity": 0.0, "Unit": "kg", "Category": "Stonefeel Powder"},
    {"Item": "Stonefeel fino (Jade)", "Size/Packaging": "25kg Bags", "Quantity": 0.0, "Unit": "kg", "Category": "Stonefeel Powder"},
    {"Item": "Stone feel base fina 0.4", "Size/Packaging": "36x 25kg Bags", "Quantity": 900.0, "Unit": "kg", "Category": "Stonefeel Powder"},
    {"Item": "Stonefeel base resin", "Size/Packaging": "Stonepool 2C Base (680L) + Stone Feel Pool Base (82.5L)", "Quantity": 762.5, "Unit": "L", "Category": "Stonefeel Resin"},
    {"Item": "Stonefeel fine resin", "Size/Packaging": "32x 20L Pails (640L) + 7x 7.5L Pails (52.5L)", "Quantity": 692.5, "Unit": "L", "Category": "Stonefeel Resin"},
    {"Item": "Lithium Silicate", "Size/Packaging": "2x 1kg Bottles + 8x 5kg Pails", "Quantity": 42.0, "Unit": "kg", "Category": "Densifier"},
    {"Item": "Ecopox CEM", "Size/Packaging": "12x 5kg Matched Sets (A+B+C)", "Quantity": 60.0, "Unit": "kg", "Category": "Epoxy Cement Primer"},
    {"Item": "ECofondo One", "Size/Packaging": "14x 28kg Sets (A+B+C)", "Quantity": 392.0, "Unit": "kg", "Category": "Epoxy Slurry / Base"},
    {"Item": "Orfapol Plus", "Size/Packaging": "2x 10kg Kits (15.8kg A + 4.2kg B)", "Quantity": 20.0, "Unit": "kg", "Category": "Polyurethane Topcoat"},
    
    # Other Master Inventory Line Items
    {"Item": "Stonefeel pool grueso Gris bas", "Size/Packaging": "1x 25kg Bag (Excluded from standard systems)", "Quantity": 25.0, "Unit": "kg", "Category": "Stonefeel Powder (Special)"},
    {"Item": "Orfapol 100", "Size/Packaging": "4x 5kg Pails", "Quantity": 20.0, "Unit": "kg", "Category": "Polyurethane Topcoat"},
    {"Item": "Paviseal 505", "Size/Packaging": "1x 5kg", "Quantity": 5.0, "Unit": "kg", "Category": "Sealer"},
    {"Item": "Paviseal 505 relief enhancer", "Size/Packaging": "1x 5kg", "Quantity": 5.0, "Unit": "kg", "Category": "Additive"},
    {"Item": "Resipav garden", "Size/Packaging": "1x 5kg", "Quantity": 5.0, "Unit": "kg", "Category": "Resin"},
    {"Item": "Desencofrante-L2", "Size/Packaging": "5x 3.5kg", "Quantity": 17.5, "Unit": "kg", "Category": "Release Agent"},
    {"Item": "Epoxyden primer S.L. A", "Size/Packaging": "2x 10kg", "Quantity": 20.0, "Unit": "kg", "Category": "Primer"},
    {"Item": "Epoxyden primer S.L. B", "Size/Packaging": "2x 5kg", "Quantity": 10.0, "Unit": "kg", "Category": "Primer"},
    {"Item": "Denbergloss silicon acrylic A", "Size/Packaging": "1x 14.4L", "Quantity": 14.4, "Unit": "L", "Category": "Topcoat"},
    {"Item": "Denvergloss silicon acrylic B", "Size/Packaging": "1x 3.6L", "Quantity": 3.6, "Unit": "L", "Category": "Topcoat"},
    {"Item": "Pavidur 1c", "Size/Packaging": "1x 25kg", "Quantity": 25.0, "Unit": "kg", "Category": "Mortar"},
    {"Item": "Pavidur 1c Accelerator", "Size/Packaging": "1x 0.2kg", "Quantity": 0.2, "Unit": "kg", "Category": "Accelerator"},
    {"Item": "Pavifort 85-15 A", "Size/Packaging": "1x 4.5kg", "Quantity": 4.5, "Unit": "kg", "Category": "Floor Coat"},
    {"Item": "Pavifort 85-15 B", "Size/Packaging": "1x 1.666kg", "Quantity": 1.67, "Unit": "kg", "Category": "Floor Coat"},
    {"Item": "Pavigrout R2 white", "Size/Packaging": "21x 25kg Bags", "Quantity": 525.0, "Unit": "kg", "Category": "Grout / Repair"},
    {"Item": "Pavigrout fluido", "Size/Packaging": "2x 25kg Bags", "Quantity": 50.0, "Unit": "kg", "Category": "Grout"},
    {"Item": "Pavigrout Unnamed", "Size/Packaging": "2x 25kg Bags", "Quantity": 50.0, "Unit": "kg", "Category": "Grout"},
    {"Item": "Cemcol C2TES1", "Size/Packaging": "4x 25kg Bags", "Quantity": 100.0, "Unit": "kg", "Category": "Adhesive"},
    {"Item": "Microtopping white", "Size/Packaging": "50x 20kg Bags", "Quantity": 1000.0, "Unit": "kg", "Category": "Microcement"},
    {"Item": "Revex Cal", "Size/Packaging": "27x 25kg Bags", "Quantity": 675.0, "Unit": "kg", "Category": "Lime Plaster"},
    {"Item": "Redexy 3C Comp A", "Size/Packaging": "2x 4.5kg", "Quantity": 9.0, "Unit": "kg", "Category": "Repair Mortar"},
    {"Item": "Redexy 3C Comp B", "Size/Packaging": "2x 3kg", "Quantity": 6.0, "Unit": "kg", "Category": "Repair Mortar"},
    {"Item": "Redexy 3C Comp C", "Size/Packaging": "3x 15kg", "Quantity": 45.0, "Unit": "kg", "Category": "Repair Mortar"},
    {"Item": "Hidroguard Transparent", "Size/Packaging": "10x 1kg Bottles", "Quantity": 10.0, "Unit": "kg", "Category": "Sealer"},
    {"Item": "Cromasil", "Size/Packaging": "4x 1kg", "Quantity": 4.0, "Unit": "kg", "Category": "Treatment"},
    {"Item": "Pantera", "Size/Packaging": "5x 25kg Bags", "Quantity": 125.0, "Unit": "kg", "Category": "Aggregates"},
    {"Item": "Goat all terrain", "Size/Packaging": "1x 25kg Bag", "Quantity": 25.0, "Unit": "kg", "Category": "Aggregates"},
    {"Item": "Pavimper 2C", "Size/Packaging": "1x 24kg Bag", "Quantity": 24.0, "Unit": "kg", "Category": "Waterproofing"},
    {"Item": "Pavimper CB", "Size/Packaging": "12L", "Quantity": 12.0, "Unit": "L", "Category": "Waterproofing"}
]

# Recipes with Container Sizes for Project Estimation
recipes_data = [
    # 1. Decopox Standard
    {"System": "Decopox Standard", "Item": "פריימר F300", "Rate": 0.02, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Decopox Standard", "Item": "Pavex Primer", "Rate": 0.30, "Container_Size": 30.0, "Unit": "kg"},
    {"System": "Decopox Standard", "Item": "Small Quartz", "Rate": 0.30, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Decopox Standard", "Item": "Decopox", "Rate": 1.00, "Container_Size": 10.0, "Unit": "kg"},
    {"System": "Decopox Standard", "Item": "Color Pigment", "Rate": 0.025, "Container_Size": 0.25, "Unit": "kg"},
    {"System": "Decopox Standard", "Item": "Veladura", "Rate": 0.10, "Container_Size": 5.0, "Unit": "kg"},
    {"System": "Decopox Standard", "Item": "Orfapol 50", "Rate": 0.10, "Container_Size": 6.0, "Unit": "kg"},
    
    # 2. Decopox Ecopox CEM
    {"System": "Decopox Ecopox CEM", "Item": "פריימר F300", "Rate": 0.02, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Decopox Ecopox CEM", "Item": "Ecopox CEM", "Rate": 1.20, "Container_Size": 5.0, "Unit": "kg"},
    {"System": "Decopox Ecopox CEM", "Item": "Small Quartz", "Rate": 0.15, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Decopox Ecopox CEM", "Item": "Decopox", "Rate": 1.00, "Container_Size": 10.0, "Unit": "kg"},
    {"System": "Decopox Ecopox CEM", "Item": "Color Pigment", "Rate": 0.025, "Container_Size": 0.25, "Unit": "kg"},
    {"System": "Decopox Ecopox CEM", "Item": "Veladura", "Rate": 0.10, "Container_Size": 5.0, "Unit": "kg"},
    {"System": "Decopox Ecopox CEM", "Item": "Orfapol 50", "Rate": 0.10, "Container_Size": 6.0, "Unit": "kg"},
    
    # 3. Decopox EcoFondo 1
    {"System": "Decopox EcoFondo 1", "Item": "פריימר F300", "Rate": 0.02, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Decopox EcoFondo 1", "Item": "Eco Fondo 1", "Rate": 2.80, "Container_Size": 28.0, "Unit": "kg"},
    {"System": "Decopox EcoFondo 1", "Item": "Small Quartz", "Rate": 0.15, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Decopox EcoFondo 1", "Item": "Decopox", "Rate": 1.00, "Container_Size": 10.0, "Unit": "kg"},
    {"System": "Decopox EcoFondo 1", "Item": "Color Pigment", "Rate": 0.025, "Container_Size": 0.25, "Unit": "kg"},
    {"System": "Decopox EcoFondo 1", "Item": "Veladura", "Rate": 0.10, "Container_Size": 5.0, "Unit": "kg"},
    {"System": "Decopox EcoFondo 1", "Item": "Orfapol 50", "Rate": 0.10, "Container_Size": 6.0, "Unit": "kg"},
    
    # 4. Stonefeel fino
    {"System": "Stonefeel fino", "Item": "פריימר F300", "Rate": 0.04, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel fino", "Item": "Stonefeel base grueso", "Rate": 4.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel fino", "Item": "Stonefeel base resin", "Rate": 1.00, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel fino", "Item": "Stonefeel fino", "Rate": 3.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel fino", "Item": "Stonefeel fine resin", "Rate": 1.00, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel fino", "Item": "Lithium Silicate", "Rate": 0.01, "Container_Size": 1.0, "Unit": "kg"},
    {"System": "Stonefeel fino", "Item": "Paviseal 700", "Rate": 0.005, "Container_Size": 1.0, "Unit": "kg"},
    
    # 5. Stonefeel grueso
    {"System": "Stonefeel grueso", "Item": "פריימר F300", "Rate": 0.04, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel grueso", "Item": "Stonefeel base grueso", "Rate": 4.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel grueso", "Item": "Stonefeel base resin", "Rate": 1.00, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel grueso", "Item": "Stonefeel grueso", "Rate": 4.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel grueso", "Item": "Stonefeel fine resin", "Rate": 1.00, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel grueso", "Item": "Lithium Silicate", "Rate": 0.01, "Container_Size": 1.0, "Unit": "kg"},
    {"System": "Stonefeel grueso", "Item": "Paviseal 700", "Rate": 0.005, "Container_Size": 1.0, "Unit": "kg"},
    
    # 6. Stonefeel Fino and grueso
    {"System": "Stonefeel Fino and grueso", "Item": "פריימר F300", "Rate": 0.04, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel Fino and grueso", "Item": "Stonefeel base grueso", "Rate": 4.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel Fino and grueso", "Item": "Stonefeel base resin", "Rate": 1.00, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel Fino and grueso", "Item": "Stonefeel fino", "Rate": 2.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel Fino and grueso", "Item": "Stonefeel grueso", "Rate": 2.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel Fino and grueso", "Item": "Stonefeel fine resin", "Rate": 1.00, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel Fino and grueso", "Item": "Lithium Silicate", "Rate": 0.01, "Container_Size": 1.0, "Unit": "kg"},
    {"System": "Stonefeel Fino and grueso", "Item": "Paviseal 700", "Rate": 0.005, "Container_Size": 1.0, "Unit": "kg"},
    
    # 7. Stonefeel walls fino
    {"System": "Stonefeel walls fino", "Item": "פריימר F300", "Rate": 0.04, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel walls fino", "Item": "Stone feel base fina 0.4", "Rate": 3.00, "Container_Size": 25.0, "Unit": "kg"},
    {"System": "Stonefeel walls fino", "Item": "Stonefeel fine resin", "Rate": 1.00, "Container_Size": 20.0, "Unit": "L"},
    {"System": "Stonefeel walls fino", "Item": "Lithium Silicate", "Rate": 0.01, "Container_Size": 1.0, "Unit": "kg"},
    {"System": "Stonefeel walls fino", "Item": "Paviseal 700", "Rate": 0.005, "Container_Size": 1.0, "Unit": "kg"}
]

rec_df = pd.DataFrame(recipes_data)
engine = InventoryCapacityEngine()

# Sidebar: File Upload / Filters
st.sidebar.header("📁 Inventory Controls")
uploaded_file = st.sidebar.file_uploader("Upload Updated Inventory (.xlsx / .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    inv_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
else:
    inv_df = pd.DataFrame(full_warehouse_master_inv)

search_query = st.sidebar.text_input("🔍 Search Material / Category", "")
category_list = ["All"] + sorted(list(set(inv_df["Category"].dropna().unique())))
selected_category = st.sidebar.selectbox("📂 Filter by Category", category_list)

filtered_inv = inv_df.copy()
if selected_category != "All":
    filtered_inv = filtered_inv[filtered_inv["Category"] == selected_category]
if search_query.strip() != "":
    filtered_inv = filtered_inv[
        filtered_inv["Item"].str.contains(search_query, case=False, na=False) |
        filtered_inv["Category"].str.contains(search_query, case=False, na=False)
    ]

# -------------------------------------------------------------
# 1. LIVE EDITABLE WAREHOUSE STOCK
# -------------------------------------------------------------
st.subheader("📦 Master Warehouse Stock (Live Editable)")
st.caption("Double-click any quantity below to edit live. All systems, bottleneck alerts, and leftover stock will recalculate instantly.")
edited_inv_df = st.data_editor(filtered_inv, num_rows="dynamic", use_container_width=True)

if len(filtered_inv) != len(inv_df):
    inv_df.update(edited_inv_df)
    active_inv = inv_df
else:
    active_inv = edited_inv_df

# -------------------------------------------------------------
# 2. EXECUTIVE DASHBOARD
# -------------------------------------------------------------
systems = [
    "Decopox Standard", "Decopox Ecopox CEM", "Decopox EcoFondo 1",
    "Stonefeel fino", "Stonefeel grueso", "Stonefeel Fino and grueso", "Stonefeel walls fino"
]
results = {}
summary_list = []

for s in systems:
    res = engine.calculate(active_inv, rec_df, s)
    results[s] = res
    summary_list.append({
        "System Name": res["system"],
        "Max Yield (m²)": f"{res['max_meters']:.2f} m²",
        "Limiting Bottleneck": res["bottleneck"]
    })

st.markdown("---")
st.subheader("📊 Maximum System Capacity Dashboard")
cols1 = st.columns(3)
cols1[0].metric(label="Decopox Standard", value=f"{results['Decopox Standard']['max_meters']} m²", delta=f"Bottleneck: {results['Decopox Standard']['bottleneck']}", delta_color="inverse")
cols1[1].metric(label="Decopox Ecopox CEM", value=f"{results['Decopox Ecopox CEM']['max_meters']} m²", delta=f"Bottleneck: {results['Decopox Ecopox CEM']['bottleneck']}", delta_color="inverse")
cols1[2].metric(label="Decopox EcoFondo 1", value=f"{results['Decopox EcoFondo 1']['max_meters']} m²", delta=f"Bottleneck: {results['Decopox EcoFondo 1']['bottleneck']}", delta_color="inverse")

cols2 = st.columns(4)
cols2[0].metric(label="Stonefeel fino", value=f"{results['Stonefeel fino']['max_meters']} m²", delta=f"Bottleneck: {results['Stonefeel fino']['bottleneck']}", delta_color="inverse")
cols2[1].metric(label="Stonefeel grueso", value=f"{results['Stonefeel grueso']['max_meters']} m²", delta=f"Bottleneck: {results['Stonefeel grueso']['bottleneck']}", delta_color="inverse")
cols2[2].metric(label="Stonefeel Fino & Grueso", value=f"{results['Stonefeel Fino and grueso']['max_meters']} m²", delta=f"Bottleneck: {results['Stonefeel Fino and grueso']['bottleneck']}", delta_color="inverse")
cols2[3].metric(label="Stonefeel Walls Fino", value=f"{results['Stonefeel walls fino']['max_meters']} m²", delta=f"Bottleneck: {results['Stonefeel walls fino']['bottleneck']}", delta_color="inverse")

# -------------------------------------------------------------
# 3. PROJECT MATERIALS CALCULATOR (NO PRICES)
# -------------------------------------------------------------
st.markdown("---")
st.subheader("🧮 Project Materials Calculator (No Prices)")
st.caption("Calculate exact material quantities and container counts for any project size.")

calc_col1, calc_col2 = st.columns([2, 1])
with calc_col1:
    selected_calc_system = st.selectbox("Select Flooring System for Calculation", systems)
with calc_col2:
    project_sqm = st.number_input("Enter Project Area (m²)", min_value=1.0, value=100.0, step=5.0)

# Generate project requirements
calc_recipe = rec_df[rec_df["System"] == selected_calc_system].copy()
calc_recipe["item_norm"] = calc_recipe["Item"].astype(str).apply(engine.normalize)
inv_agg_calc = active_inv.copy()
inv_agg_calc["item_norm"] = inv_agg_calc["Item"].astype(str).apply(engine.normalize)
inv_agg_calc = inv_agg_calc.groupby("item_norm", as_index=False)["Quantity"].sum()

calc_merged = pd.merge(calc_recipe, inv_agg_calc, on="item_norm", how="left")
calc_merged["Quantity"] = calc_merged["Quantity"].fillna(0.0)

calc_rows = []
for _, r in calc_merged.iterrows():
    rate_val = float(r["Rate"])
    req_qty = rate_val * project_sqm
    cont_size = float(r["Container_Size"])
    exact_cont = req_qty / cont_size if cont_size > 0 else 0.0
    rounded_cont = math.ceil(exact_cont)
    unit_str = str(r["Unit"])
    avail_qty = float(r["Quantity"])
    
    is_unlimited_item = engine.is_unlimited(r["Item"])
    if is_unlimited_item:
        stock_status = "✅ Unlimited Supply"
    elif avail_qty >= req_qty:
        stock_status = f"✅ In Stock ({avail_qty:.1f} available)"
    else:
        shortage = req_qty - avail_qty
        stock_status = f"❌ Short by {shortage:.1f} {unit_str}"

    calc_rows.append({
        "Component / Layer": r["Item"],
        "Rate (per m²)": f"{rate_val:.3f} {unit_str}",
        "Total Required": f"{req_qty:.2f} {unit_str}",
        "Container Size": f"{cont_size:.1f} {unit_str}",
        "Containers (Exact)": round(exact_cont, 2),
        "Containers (Rounded Up)": rounded_cont,
        "Warehouse Stock Status": stock_status
    })

df_calc_display = pd.DataFrame(calc_rows)
st.dataframe(df_calc_display, use_container_width=True)

# -------------------------------------------------------------
# 4. DETAILED CAPACITY TABS & UNUSED LEFTOVERS
# -------------------------------------------------------------
st.markdown("---")
st.subheader("🔍 Detailed Product Breakdown & Leftover Inventory at Max Capacity")
tabs = st.tabs(systems)

for i, s in enumerate(systems):
    with tabs[i]:
        res = results[s]
        st.dataframe(res["table"], use_container_width=True)
        if res["color_breakdown"] is not None:
            st.markdown("🎨 **Stonefeel Fino Colors Capacity Breakdown:**")
            st.dataframe(res["color_breakdown"], use_container_width=True)

# -------------------------------------------------------------
# 5. EXCEL EXPORT
# -------------------------------------------------------------
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    pd.DataFrame(summary_list).to_excel(writer, sheet_name="Executive Summary", index=False)
    active_inv.to_excel(writer, sheet_name="Master Warehouse Stock", index=False)
    df_calc_display.to_excel(writer, sheet_name="Project Estimator", index=False)
    for s in systems:
        results[s]["table"].to_excel(writer, sheet_name=s[:31], index=False)
        if results[s]["color_breakdown"] is not None:
            results[s]["color_breakdown"].to_excel(writer, sheet_name=f"{s[:20]}_Colors", index=False)

st.download_button(
    label="📥 Download Complete Updated Excel Report (With Calculator & Master Stock)",
    data=excel_buffer.getvalue(),
    file_name="MODOS_Master_Inventory_and_Capacity_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
