import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import numpy as np

# Configuration de la page
st.set_page_config(
    page_title="Tableau de Bord Financier Mensuel",
    page_icon="📊",
    layout="wide"
)

# Initialisation de l'état de session
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'sheets' not in st.session_state:
    st.session_state.sheets = []
if 'exchange_rates' not in st.session_state:
    st.session_state.exchange_rates = {
        'EUR': 0.875843475231553,
        'GBP': 1.14175652188951,
        'INR': 0.012,  # Indian Rupee
        'JPY': 0.0067,  # Japanese Yen
        # Ajoutez d'autres devises au besoin
    }

# Fonctions de traitement
def process_excel_file(file):
    try:
        excel = pd.ExcelFile(file)
        sheets = excel.sheet_names
        data = {}
        
        for sheet in sheets:
            df = pd.read_excel(excel, sheet_name=sheet)
            # Nettoyage des données
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
            data[sheet] = df
            
        return data, sheets
    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier: {str(e)}")
        return None, []

def convert_currency(df, column, from_currency, to_currency='USD'):
    if from_currency in st.session_state.exchange_rates:
        rate = st.session_state.exchange_rates[from_currency]
        df[column] = df[column] * rate
    return df

def process_budget_vs_actual(df):
    """Traitement spécifique pour la feuille Budget VS Actual"""
    # Identifier les sections (Budget, Forecast, Actual)
    sections = {}
    current_section = None
    
    for idx, row in df.iterrows():
        if 'BUDGET' in str(row.iloc[0]):
            current_section = 'Budget'
            sections[current_section] = {'start': idx}
        elif 'FORECAST' in str(row.iloc[0]):
            current_section = 'Forecast'
            sections[current_section] = {'start': idx}
        elif 'ACTUAL' in str(row.iloc[0]):
            current_section = 'Actual'
            sections[current_section] = {'start': idx}
        elif current_section and pd.notna(row.iloc[0]):
            sections[current_section]['end'] = idx
    
    # Extraire les données pour chaque section
    processed_data = {}
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for section, indices in sections.items():
        if 'start' in indices and 'end' in indices:
            section_df = df.iloc[indices['start']:indices['end']+1]
            
            # Trouver les lignes de données
            for idx, row in section_df.iterrows():
                if 'Revenue' in str(row.iloc[0]):
                    revenue_row = row
                elif 'Direct Costs' in str(row.iloc[0]):
                    costs_row = row
                elif 'Gross Profit' in str(row.iloc[0]):
                    profit_row = row
            
            # Créer un DataFrame structuré
            data = {
                'Month': months,
                'Revenue': revenue_row.iloc[2:14].values,
                'Direct Costs': costs_row.iloc[2:14].values,
                'Gross Profit': profit_row.iloc[2:14].values
            }
            processed_df = pd.DataFrame(data)
            processed_df['Type'] = section
            processed_data[section] = processed_df
    
    return processed_data

def process_opex_analysis(df):
    """Traitement spécifique pour la feuille OPEX Group Analysis"""
    # Nettoyer les noms de colonnes
    df.columns = df.iloc[0]
    df = df.drop(0).reset_index(drop=True)
    
    # Identifier les colonnes de mois
    month_cols = [col for col in df.columns if '25' in str(col)]
    
    # Restructurer les données
    melted_df = pd.melt(df, id_vars=['Account Name'], value_vars=month_cols, 
                       var_name='Month', value_name='Amount')
    
    # Nettoyer les données
    melted_df = melted_df.dropna()
    melted_df['Amount'] = pd.to_numeric(melted_df['Amount'], errors='coerce')
    melted_df = melted_df.dropna()
    
    return melted_df

def process_pl_per_customer(df):
    """Traitement spécifique pour la feuille P&L Per Customer"""
    # Identifier les clients
    customers = []
    for idx, row in df.iterrows():
        if isinstance(row.iloc[0], str) and not row.iloc[0].startswith('GP margin') and not row.iloc[0].startswith('Cost of Sales'):
            customers.append(row.iloc[0])
    
    # Extraire les données pour chaque client
    customer_data = []
    months = ['Jan-25', 'Feb-25', 'Mar-25', 'Apr-25', 'May-25', 'Jun-25', 'Jul-25']
    
    for customer in customers:
        customer_idx = df[df.iloc[:, 0] == customer].index[0]
        
        revenue_row = df.iloc[customer_idx + 1]
        costs_row = df.iloc[customer_idx + 2]
        
        for i, month in enumerate(months):
            if i < len(revenue_row) - 1:  # Ignorer la première colonne
                customer_data.append({
                    'Customer': customer,
                    'Month': month,
                    'Revenue': revenue_row.iloc[i+1],
                    'Cost of Sales': costs_row.iloc[i+1],
                    'Gross Profit': revenue_row.iloc[i+1] - costs_row.iloc[i+1]
                })
    
    return pd.DataFrame(customer_data)

# Interface principale
st.title("Tableau de Bord Financier Mensuel - Application Streamlit")

# Barre latérale
with st.sidebar:
    st.header("Actions")
    
    # Upload du fichier Excel
    uploaded_file = st.file_uploader(
        "Uploader le fichier Excel Group Report",
        type=['xlsx', 'xls'],
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        if st.button("Charger les données"):
            st.session_state.data, st.session_state.sheets = process_excel_file(uploaded_file)
            st.success("Fichier chargé avec succès!")
    
    # Sélection de l'onglet/sheet
    if st.session_state.sheets:
        selected_sheet = st.selectbox(
            "Sélectionner un onglet",
            st.session_state.sheets
        )
    
    # Mise à jour des taux de change
    st.header("Gestion des Devises")
    currency = st.selectbox("Sélectionner une devise", list(st.session_state.exchange_rates.keys()))
    new_rate = st.number_input(f"Taux pour {currency} vers USD", value=st.session_state.exchange_rates[currency])
    if st.button("Mettre à jour le taux"):
        st.session_state.exchange_rates[currency] = new_rate
        st.success(f"Taux pour {currency} mis à jour!")
    
    # Options de visualisation
    st.header("Options de Visualisation")
    show_raw_data = st.checkbox("Afficher les données brutes", value=False)
    dark_mode = st.checkbox("Mode sombre", value=False)

# Appliquer le mode sombre si sélectionné
if dark_mode:
    st.markdown("""
    <style>
    .stApp {
        background-color: #1E1E1E;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Zone principale
if 'data' in st.session_state and st.session_state.data:
    if 'selected_sheet' in locals() and selected_sheet:
        st.header(f"Onglet: {selected_sheet}")
        df = st.session_state.data[selected_sheet]
        
        # Afficher les données brutes si demandé
        if show_raw_data:
            st.subheader("Données Brutes")
            st.dataframe(df)
        
        # Traitement spécifique selon l'onglet
        if selected_sheet == "Budget VS Actual":
            st.subheader("Comparaison Budget vs Forecast vs Actual")
            processed_data = process_budget_vs_actual(df)
            
            if processed_data:
                # Combiner toutes les sections
                combined_df = pd.concat(processed_data.values())
                
                # Visualisation
                fig = px.line(
                    combined_df, 
                    x='Month', 
                    y='Revenue', 
                    color='Type',
                    title="Revenue: Budget vs Forecast vs Actual",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
                
                fig2 = px.line(
                    combined_df, 
                    x='Month', 
                    y='Gross Profit', 
                    color='Type',
                    title="Gross Profit: Budget vs Forecast vs Actual",
                    markers=True
                )
                st.plotly_chart(fig2, use_container_width=True)
                
                # Tableau de comparaison
                st.subheader("Tableau Comparatif")
                pivot_df = combined_df.pivot_table(index='Month', columns='Type', values=['Revenue', 'Gross Profit'])
                st.dataframe(pivot_df.style.format("{:,.2f}"))
        
        elif selected_sheet == "OPEX Group Analysis":
            st.subheader("Analyse des Dépenses OPEX")
            processed_df = process_opex_analysis(df)
            
            if not processed_df.empty:
                # Sélectionner les comptes à afficher
                top_accounts = processed_df.groupby('Account Name')['Amount'].sum().sort_values(ascending=False).head(10).index.tolist()
                selected_accounts = st.multiselect(
                    "Sélectionner les comptes à afficher",
                    options=processed_df['Account Name'].unique(),
                    default=top_accounts
                )
                
                filtered_df = processed_df[processed_df['Account Name'].isin(selected_accounts)]
                
                # Visualisation
                fig = px.bar(
                    filtered_df, 
                    x='Month', 
                    y='Amount', 
                    color='Account Name',
                    title="Dépenses par Compte",
                    barmode='group'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Totaux par mois
                st.subheader("Totaux des Dépenses par Mois")
                monthly_totals = processed_df.groupby('Month')['Amount'].sum().reset_index()
                st.dataframe(monthly_totals.style.format({"Amount": "{:,.2f}"}))
                
                # Top dépenses
                st.subheader("Top 10 des Dépenses")
                top_expenses = processed_df.groupby('Account Name')['Amount'].sum().sort_values(ascending=False).head(10)
                st.dataframe(top_expenses.to_frame().style.format("{:,.2f}"))
        
        elif selected_sheet == "P&L Per Customer":
            st.subheader("Rentabilité par Client")
            processed_df = process_pl_per_customer(df)
            
            if not processed_df.empty:
                # Sélectionner le mois
                months = processed_df['Month'].unique()
                selected_month = st.selectbox("Sélectionner un mois", months)
                
                month_df = processed_df[processed_df['Month'] == selected_month]
                
                # Calculer les marges
                month_df['GP Margin %'] = (month_df['Gross Profit'] / month_df['Revenue']) * 100
                
                # Visualisation
                fig = px.bar(
                    month_df.sort_values('Gross Profit', ascending=False), 
                    x='Customer', 
                    y='Gross Profit',
                    title=f"Profit Brut par Client - {selected_month}",
                    color='GP Margin %',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tableau détaillé
                st.subheader("Détails par Client")
                st.dataframe(
                    month_df[['Customer', 'Revenue', 'Cost of Sales', 'Gross Profit', 'GP Margin %']]
                    .sort_values('Gross Profit', ascending=False)
                    .style.format({
                        "Revenue": "{:,.2f}",
                        "Cost of Sales": "{:,.2f}",
                        "Gross Profit": "{:,.2f}",
                        "GP Margin %": "{:.2f}%"
                    })
                )
        
        elif selected_sheet == "Balance Sheet":
            st.subheader("Bilan Comptable")
            # Implémenter le traitement spécifique pour le bilan
            
        elif selected_sheet == "Sales Accruals":
            st.subheader("Régularisations des Ventes")
            # Implémenter le traitement spécifique pour les régularisations
            
        elif selected_sheet == "Accounts Receivable":
            st.subheader("Comptes Clients")
            # Implémenter le traitement spécifique pour les comptes clients
        
        # Conversion de devises générique
        if st.checkbox("Convertir en USD"):
            currency_col = st.selectbox("Colonne à convertir", df.select_dtypes(include=['float', 'int']).columns)
            from_currency = st.selectbox("De la devise", list(st.session_state.exchange_rates.keys()))
            df = convert_currency(df, currency_col, from_currency)
            st.dataframe(df)
else:
    st.info("Veuillez uploader un fichier Excel pour commencer.")

# Fonction pour afficher les tendances des devises
def show_currency_trends():
    st.header("Tendances des Devises")
    # Simulation de données de tendances (à remplacer par données réelles si disponibles)
    trend_data = pd.DataFrame({
        'Date': pd.date_range(start='2025-01-01', periods=7, freq='M'),
        'EUR': [0.87, 0.88, 0.875, 0.87, 0.86, 0.85, 0.84],
        'GBP': [1.14, 1.15, 1.14, 1.13, 1.12, 1.11, 1.10]
    })
    fig = px.line(trend_data, x='Date', y=['EUR', 'GBP'], title="Tendances des Taux de Change")
    st.plotly_chart(fig)

if st.sidebar.button("Voir les tendances des devises"):
    show_currency_trends()

# Ajouter une section de promotion
st.sidebar.markdown("---")
st.sidebar.header("À Propos de Cette Application")
st.sidebar.info("""
Cette application a été conçue pour visualiser et analyser les rapports financiers mensuels. 
Elle permet de:
- Comparer les budgets, prévisions et résultats réels
- Analyser les dépenses opérationnelles
- Examiner la rentabilité par client
- Convertir les montants entre différentes devises

Développée avec Streamlit pour une expérience utilisateur interactive.
""")

st.sidebar.markdown("---")
st.sidebar.markdown("**Version 1.1**")
st.sidebar.markdown("Améliorations incluses:")
st.sidebar.markdown("- Traitement amélioré des données financières")
st.sidebar.markdown("- Visualisations interactives")
st.sidebar.markdown("- Mode sombre optionnel")
st.sidebar.markdown("- Analyse de rentabilité par client")