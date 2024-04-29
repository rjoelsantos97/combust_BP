import streamlit as st
import pandas as pd
from io import BytesIO
import xlsxwriter

# Define the to_excel function at the top of your script
def to_excel(df):
    with BytesIO() as output:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            writer.save()
        return output.getvalue()

# Função para processar os dados
def processar_dados(dados_combustivel):
    # Mapeamento de matrículas para categorias e centros analíticos
    mapa_categoria = dados_frota.set_index('Matricula')['Categoria'].to_dict()
    mapa_centro_analitico = dados_frota.set_index('Matricula')['Centro analitico'].to_dict()

    # Funções para buscar informações com base na matrícula
    def buscar_categoria(matricula):
        return mapa_categoria.get(matricula, 'Não - NAPS')  # Retorna 'Não - NAPS' se a matrícula não for encontrada

    def buscar_centro_analitico(matricula):
        return mapa_centro_analitico.get(matricula, '')

    # Funções para determinar o código e calcular o valor ajustado
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

    # Mapeamento de proprietários para matrículas
    proprietarios_matriculas = {
        'EUGENIA VIEIRA': 'AS-17-HV',
        'HELENA GOMES': 'AG-46-IR',
        'INES AZEVEDO': 'AS-50-VS',
        'JOSE AZEVEDO': 'AQ-99-HL'
    }

    # Substituir a matrícula com base no mapeamento de proprietários
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
    custos_combustivel_final = custos_agregados[colunas_output]
    return custos_combustivel_final

# Carregar os dados das planilhas do Excel
dados_frota = pd.read_excel('FROTA_DETALHES.xlsx')

# Streamlit app
st.title('Processador de Custos de Combustível')

# File uploader permite ao usuário carregar seus próprios dados
uploaded_file = st.file_uploader("Carregue o arquivo CUSTOS_COMBUSTIVEL", type=['xlsx'])

# Initialize dados_processados as None to check later if it has been set
dados_processados = None

if uploaded_file is not None:
    # Se um arquivo for carregado, processar os dados
    custos_combustivel_raw = pd.read_excel(uploaded_file)
    dados_processados = processar_dados(custos_combustivel_raw)
    
    # Exibir os dados processados na app
    st.write("Dados Processados:")
    st.dataframe(dados_processados)

#Only display the download button if dados_processados has been set with processed data

if dados_processados is not None:
    st.download_button(
        label="Download Excel",
        data=to_excel(dados_processados),  # Pass the processed data DataFrame to the function
        file_name="custos_combustivel_agregado_final.xlsx",
        mime="application/vnd.ms-excel"
    )    

