import pandas as pd
import streamlit as st
import plotly.express as px


st.set_page_config(page_title="Ventes Lumina", layout="wide")

SOURCE = "data/lumina_ventes.csv"

COULEURS_FAMILLE = {
    "Livres": "#0072B2",
    "Musique & Vidéo": "#E69F00",
    "Gaming": "#009E73",
    "High-tech": "#CC79A7",
}


# Étape 1 : chargement et cache -------------------------------------------
@st.cache_data
def charger(chemin):
    ventes = pd.read_csv(chemin, parse_dates=["date_commande"])
    ventes["mois"] = ventes["date_commande"].dt.to_period("M").dt.to_timestamp()
    return ventes

def resultat_fr(x, decimales=0):
    texte = f"{x:,.{decimales}f}"
    return texte.replace(",", " ").replace(".", ",")

def euros(x):
    if x >= 1_000_000:
        return f"{resultat_fr(x / 1_000_000, 2)} M€"
    return f"{resultat_fr(x)} €"

def signe(x, decimales, unite):
    x = round(x, decimales) + 0.0  # évite d'afficher « -0,0 »
    plus = "+" if x >= 0 else ""
    return plus + resultat_fr(x, decimales) + unite

ventes = charger(SOURCE)

# Filtre dans la barre latérale 
annees = sorted(ventes["date_commande"].dt.year.unique(), reverse=True)
annee = st.sidebar.selectbox("Année", annees)
df = ventes  # l'année est filtrée en dernier, pour construire aussi precedent

magasins = st.sidebar.multiselect("Magasins", sorted(ventes["magasin"].unique()))
if magasins:
    df = df[df["magasin"].isin(magasins)]

familles = st.sidebar.multiselect("Familles", sorted(ventes["famille"].unique()))
if familles: 
    df = df[df["famille"].isin(familles)]

canal = st.sidebar.radio("Canal", ["Tous", "magasin", "web"])
if canal != "Tous":
    df = df[df["canal"] == canal]

# Séparation des années : precedent AVANT d'écraser df
annee_df = df["date_commande"].dt.year
precedent = df[annee_df == annee - 1]
df = df[annee_df == annee]

if df.empty:
    st.warning("Aucune vente ne correspond à ces filtres.")
    st.stop()

# Année précédente limitée aux mêmes mois que df
mois_presents = df["date_commande"].dt.month.unique()
precedent = precedent[precedent["date_commande"].dt.month.isin(mois_presents)]

def indicateurs(donnees):
    ca = donnees["montant_ligne"].sum()
    commandes = donnees["id_commande"].nunique()
    par_commande = donnees.groupby("id_commande")["montant_ligne"].sum()
    panier = par_commande.mean()
    ca_web = donnees.loc[donnees["canal"] == "web", "montant_ligne"].sum()
    part_web = 100 * ca_web / ca

    return ca, commandes, panier, part_web

ca, commandes, panier, part_web = indicateurs(df)

if precedent.empty:
    evolution = None
    delta_ca = delta_commandes = delta_panier = delta_web = None
else:
    ca_p, commandes_p, panier_p, part_web_p = indicateurs(precedent)
    evolution = 100 * (ca / ca_p - 1)
    delta_ca = signe(evolution, 1, " %")
    delta_commandes = signe(commandes - commandes_p, 0, "")
    delta_panier = signe(panier - panier_p, 2, " €")
    delta_web = signe(part_web - part_web_p, 1, " pt")

if evolution is None: 
    st.title(f"Ventes Lumina {annee}")
else:
    sens = "progresse" if evolution >= 0 else "régresse"
    st.title(f"Ventes Lumina : le CA {sens} de {resultat_fr(abs(evolution), 1)} % "
             "sur un an à périmètre constant")

st.caption(
    f"Périmètre : {annee} · "
    f"magasins : {', '.join(magasins) if magasins else 'tous'} · "
    f"familles : {', '.join(familles) if familles else 'toutes'} · "
    f"canal : {canal.lower()} · source : {SOURCE}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Chiffre d'affaires", euros(ca), delta_ca)
c2.metric("Commandes", resultat_fr(commandes), delta_commandes)
c3.metric("Panier moyen", f"{resultat_fr(panier, 2)} €", delta_panier)
c4.metric("Part du web", f"{resultat_fr(part_web, 1)} %", delta_web)

# -------------- Graphiques 

gauche, droite = st.columns([2, 1])

with gauche: 
    mensuel = df.groupby(["mois", "famille"], as_index=False)["montant_ligne"].sum()
    fig = px.bar(
        mensuel, x="mois", y="montant_ligne", color="famille", 
        color_discrete_map=COULEURS_FAMILLE,
        labels={"mois": "Mois", "montant_ligne": "CA (€)", "famille": "Famille"}, 
        title=f"CA mensuel {annee} par famille",
        template="plotly_white",
    )

    fig.update_layout(hovermode="x unified",
                      legend=dict(orientation="h", y=-0.2, title_text=""))
    fig.update_xaxes(dtick="M1", tickformat="%b")
    st.plotly_chart(fig, width="stretch")