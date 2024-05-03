import streamlit as st
from PIL import Image
import requests
from io import BytesIO

# Custom CSS styles
st.markdown(
    """
    <style>
        body {
            background-color: #00ff00; /* background color */
            color: #ffffff; /* text color */
            font-family: sans-serif; /* font family */
        }
        .stSidebar { 
            background-color: #ffff00 !important; /* sidebar background color */
        }
        .stButton>button {
            background-color: #0000ff !important; /* button background color */
            color: #ffffff !important; /* button text color */
        }
        /* Add more custom styles as needed */
    </style>
    """,
    unsafe_allow_html=True
)

# Configuração da página
st.set_page_config(
    page_title='Análise de Extratos BP & Via Verde',
    layout='wide',  # Adjust as needed
    initial_sidebar_state='expanded'  # Adjust as needed
)



# Carregar uma imagem via URL
url = 'https://raw.githubusercontent.com/rjoelsantos97/combust_BP/af90fcddd50b89e2b4dbda681d2e25ba5b93bd3f/logo.png'  # Substitua pelo URL real da imagem
response = requests.get(url)
image = Image.open(BytesIO(response.content))

# Mostrar a imagem (logotipo) no Streamlit
st.image(image, width=200)  # Ajuste a largura conforme necessário




# Função para processar dados de portagens
def processar_portagens(portagens_path):
    frota_df = pd.read_excel('FROTA_DETALHES.xlsx')
    portagens_df = pd.read_csv(portagens_path, skiprows=7, sep=';', encoding='ISO-8859-1')
    portagens_df['VALOR'] = portagens_df['VALOR'].str.replace(',', '.').astype(float)
    portagens_df['TAXA IVA'] = portagens_df['TAXA IVA'].astype(str).str.replace(',', '.').astype(float)
    aggregated_portagens = portagens_df.groupby(['MATRÍCULA', 'TAXA IVA']).sum().reset_index()
    final_df = pd.merge(aggregated_portagens, frota_df[['Matricula', 'Categoria', 'Centro analitico']], 
                        left_on='MATRÍCULA', right_on='Matricula', how='left')
    final_df['Matricula'].fillna('Sem Matrícula', inplace=True)
    final_df['Centro analitico'].fillna(0, inplace=True)
    final_df['Categoria'].fillna('Ligeiro Mercadorias', inplace=True)
    final_df['Valor Apresentado'] = final_df.apply(
        lambda x: x['VALOR'] if x['Categoria'] == 'Ligeiro Passageiros' else x['VALOR'] / (1 + x['TAXA IVA']/100), axis=1)
    final_df['Ref'] = final_df['Categoria'].map({
        'Ligeiro Passageiros': 'C62511132106',
        'Ligeiro Mercadorias': 'C62511131006'
    })
    final_df['QTD'] = 1
    final_df['IVA incluido'] = final_df['Categoria'].map(
        lambda x: 'Sim' if x == 'Ligeiro Passageiros' else 'Não'
    )
    final_df = final_df[['Ref', 'Matricula', 'Centro analitico', 'QTD', 'Valor Apresentado', 'TAXA IVA', 'IVA incluido']]
    return final_df

# Define the function to process the data
def process_data(frota, custos):
    # Mapeamento de matrículas para categorias e centros analíticos
    mapa_categoria = frota.set_index('Matricula')['Categoria'].to_dict()
    mapa_centro_analitico = frota.set_index('Matricula')['Centro analitico'].to_dict()

    # Function definitions
    def buscar_categoria(matricula):
        return mapa_categoria.get(matricula, 'Não - NAPS')

    def buscar_centro_analitico(matricula):
        return mapa_centro_analitico.get(matricula, '')

    def determinar_codigo(produto, categoria):
        """ Determina o código com base no produto e categoria do veículo. """
        if 'ADBLUE' in produto:
            if categoria == 'Ligeiro Mercadorias':
                return "C62261221006"
            elif categoria == 'Ligeiro Passageiros':
                return "C62261221006"
        elif 'GASOLEO' in produto or 'DIESEL' in produto:
            if categoria == 'Ligeiro Passageiros':
                return "C62421121106"
            elif categoria == 'Ligeiro Mercadorias':
                return "C62421122006"
        elif 'GASOLINA' in produto:
            if categoria == 'Ligeiro Passageiros':
                return "C62421121106"
        return None


    def calcular_valor(categoria, valor_liquido):
        """ Calcula o valor ajustado com base na categoria do veículo. """
        return valor_liquido * 1.23 if categoria == 'Ligeiro Passageiros' else valor_liquido

    # Substituir a matrícula com base no mapeamento de proprietários
    # Mapeamento de proprietários para matrículas
    proprietarios_matriculas = {
        'EUGENIA VIEIRA': 'AS-17-HV',
        #'HELENA GOMES': 'AG-46-IR',
        #'INES AZEVEDO': 'AS-50-VS',
        'JOSE AZEVEDO': 'AQ-99-HL'
    }
    custos_combustivel_raw['Matrícula'] = custos_combustivel_raw.apply(
        lambda row: proprietarios_matriculas.get(row['Proprietário'], row['Matrícula']),
        axis=1
    )
    # Correções manuais de matrículas
    correcoes_matriculas = {
        'BF-20-EV': 'BF-02-EV',
        'BC-56-EU': 'BC-56-UE',
        '39-PO-97': '39-PO-87',
        '02-UZ-92':'NA-NA-NA'
    }
    custos_combustivel_raw['Matrícula'] = custos_combustivel_raw['Matrícula'].replace(correcoes_matriculas)
    
    # Agregar os custos por 'Produto' e 'Matrícula'
    custos_agregados = custos_combustivel_raw.groupby(['Produto', 'Matrícula']).agg({
        'Quantidade': 'sum',
        'Valor líquido': 'sum',
        'IVA': 'sum',
        'Valor total a faturar': 'sum'
    }).reset_index()    
    
    # Adicionar informações de 'FROTA_DETALHES' e outras colunas necessárias
    custos_agregados['Centro analitico'] = custos_agregados['Matrícula'].apply(buscar_centro_analitico)
    custos_agregados['Categoria'] = custos_agregados['Matrícula'].apply(buscar_categoria)
    custos_agregados['REF'] = custos_agregados.apply(
        lambda row: determinar_codigo(row['Produto'], row['Categoria']),
        axis=1
    )
    custos_agregados['Valor Ajustado'] = custos_agregados.apply(
        lambda row: calcular_valor(row['Categoria'], row['Valor líquido']),
        axis=1
    )
    
    # Verificar a existência da matrícula e adicionar a observação se necessário
    custos_agregados['Observação'] = custos_agregados['Matrícula'].apply(
        lambda x: '' if x in dados_frota['Matricula'].values else 'Não - NAPS'
    )
    
    # Definir a coluna 'QTD' como 1 para todos os registros
    custos_agregados['QTD'] = 1
    
    # Adicionar a coluna 'IVA Incluído'
    custos_agregados['IVA Incluído'] = custos_agregados.apply(
        lambda row: 'IVA Incluído' if row['Categoria'] == 'Ligeiro Passageiros' else '',
        axis=1
    )
    
    # Selecionar as colunas desejadas para o output final
    colunas_output = ['REF', 'QTD', 'Valor Ajustado',  
                      'Matrícula', 'Centro analitico','IVA Incluído', 'Observação','Produto']
    
        # Filter out rows where the observation is "Não - NAPS"
    custos_agregados = custos_agregados[custos_agregados['Observação'] != 'Não - NAPS']
    custos_combustivel_final = custos_agregados[colunas_output]
    


    return custos_combustivel_final  # Return the aggregated DataFrame




# Layout principal do Streamlit
st.title('Análise de Extratos BP & Via Verde')
tab1, tab2 = st.tabs(["Análise BP", "Análise Via Verde"])

# Tab de Análise BP
with tab1:
    st.header("Análise de Combustíveis BP")
    uploaded_file_custos = st.file_uploader("Faça upload do ficheiro excel da BP", type='xlsx')
    if uploaded_file_custos:
        dados_frota = pd.read_excel('FROTA_DETALHES.xlsx')
        custos_combustivel_raw = pd.read_excel(uploaded_file_custos)
        processed_data = process_data(dados_frota, custos_combustivel_raw)
        if not processed_data.empty:
            st.success('Processamento de BP efectuado com sucesso !')
            st.dataframe(processed_data)
            towrite = BytesIO()
            processed_data.to_excel(towrite, index=False, engine='openpyxl')
            towrite.seek(0)
            st.download_button("Descarregue aqui o arquivo BP", towrite, "resultado_bp.xlsx", "application/vnd.ms-excel")

# Tab de Análise Via Verde
with tab2:
    st.header("Análise Via Verde")
    uploaded_file_portagens = st.file_uploader("Faça upload do ficheiro de extracto de portagens", type=['csv'])
    if uploaded_file_portagens:
        result_portagens = processar_portagens(uploaded_file_portagens)
        if not result_portagens.empty:
            st.success('Processamento de Via Verde efectuado com sucesso !')
            st.dataframe(result_portagens)
            towrite = BytesIO()
            result_portagens.to_excel(towrite, index=False, engine='openpyxl')
            towrite.seek(0)
            st.download_button("Descarregue aqui o arquivo Via Verde", towrite, "resultado_via_verde.xlsx", "application/vnd.ms-excel")
