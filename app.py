import streamlit as st
import pandas as pd

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
        'HELENA GOMES': 'AG-46-IR',
        'INES AZEVEDO': 'AS-50-VS',
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
        '39-PO-97': '39-PO-87'
    }
    
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
    custos_combustivel_final = custos_agregados[colunas_output]


    return custos_agregados  # Return the aggregated DataFrame

# Streamlit app layout
st.title('Vehicle Cost Processing App')

# File uploader for COSTS
uploaded_file_custos = st.file_uploader("Upload CUSTOS_COMBUSTIVEL.xlsx", type='xlsx')

if uploaded_file_custos:
    # Load the 'FROTA_DETALHES.xlsx' file from the directory
    dados_frota = pd.read_excel('FROTA_DETALHES.xlsx')

    # Read the uploaded file
    custos_combustivel_raw = pd.read_excel(uploaded_file_custos)

    # Process the data
    processed_data = process_data(dados_frota, custos_combustivel_raw)

    # Show preview of data
    st.write("Preview of Processed Data:")
    st.dataframe(processed_data.head())

    # Button to download the processed data
    def to_excel(df):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        writer.save()
        processed_data = output.getvalue()
        return processed_data

    st.download_button(
        label="Download processed data as Excel",
        data=to_excel(processed_data),
        file_name='CUSTOS_COMBUSTIVEL_AGREGADO_FINAL.xlsx',
        mime='application/vnd.ms-excel'
    )

st.write("Upload the CUSTOS_COMBUSTIVEL.xlsx file to process and download the results.")
