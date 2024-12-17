# Importações necessárias
from validate_docbr import CPF
import streamlit as st
import pandas as pd
#from validate_docbr import CPF
from datetime import datetime
import io
import sqlite3
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import textwrap
import csv

def limpar_banco_dados():
    conn = sqlite3.connect('certificados.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM certificados')
    conn.commit()
    conn.close()

# Configuração inicial do tema escuro
st.set_page_config(
    page_title="Gerador de Certificados", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Configuração do tema escuro
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
    }
    </style>
""", unsafe_allow_html=True)

# Função para criar banco de dados
def criar_banco_dados():
    conn = sqlite3.connect('certificados.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificados (
            Nome TEXT,
            CPF TEXT PRIMARY KEY,
            Curso TEXT,
            Instrutor TEXT,
            Cargo TEXT,
            Data TEXT,
            Logo BLOB
        )
    ''')
    conn.commit()
    conn.close()

# Função para salvar certificado no banco de dados
def salvar_certificado(nome, cpf, curso, instrutor, cargo, logo_bytes=None):
    conn = sqlite3.connect('certificados.db')
    cursor = conn.cursor()
    
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    
    cursor.execute('''
        INSERT OR REPLACE INTO certificados 
        (Nome, CPF, Curso, Instrutor, Cargo, Data, Logo) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (nome, cpf_limpo, curso, instrutor, cargo, str(datetime.now()), logo_bytes))
    
    conn.commit()
    conn.close()

# Função para carregar dados do banco
def carregar_dados():
    conn = sqlite3.connect('certificados.db')
    df = pd.read_sql_query("SELECT * FROM certificados", conn)
    conn.close()
    df['CPF'] = df['CPF'].astype(str)
    return df

# Função para carregar logo
def carregar_logo(cpf):
    conn = sqlite3.connect('certificados.db')
    cursor = conn.cursor()
    
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    
    cursor.execute('SELECT Logo FROM certificados WHERE CPF = ?', (cpf_limpo,))
    resultado = cursor.fetchone()
    conn.close()
    
    return resultado[0] if resultado and resultado[0] is not None else None

# Criar banco de dados inicialmente
criar_banco_dados()

# Validação de CPF
def validar_cpf(cpf_numero):
    cpf = CPF()
    return cpf.validate(cpf_numero)

# Formatar CPF
def formatar_cpf(cpf):
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

# Formatar data
def formatar_data(data):
    meses = {
        1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
        5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
        9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    return f"{data.day} de {meses[data.month]} de {data.year}"

# Geração de certificado PDF
def quebrar_linha_curso(texto, largura_maxima=35):
    linhas = textwrap.wrap(texto, width=largura_maxima)
    return linhas

def gerar_certificado_pdf(nome, cpf, curso, instrutor, cargo, logo_bytes=None):
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Configurações de margem
        margem = 50
        area_util_width = width - 2*margem
        area_util_height = height - 2*margem

        # Fundo branco
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, width, height, fill=True)

        # Moldura externa
        c.setStrokeColorRGB(0.6, 0.6, 0.6)
        c.setLineWidth(3)
        c.rect(margem, margem, area_util_width, area_util_height)

        # Moldura interna
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(1)
        c.rect(margem + 20, margem + 20, area_util_width - 40, area_util_height - 40)

        # Adicionar logo se existir
        if logo_bytes:
            try:
                logo_img = ImageReader(io.BytesIO(logo_bytes))
                logo_width = 150  # Largura fixa
                logo_height = 155  # Altura fixa
                
                # Posicionar logo no centro, mais baixo dentro da moldura
                logo_x = (width - logo_width) / 2
                logo_y = height - margem - 155
                
                c.drawImage(logo_img, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
            except Exception as e:
                st.warning(f"Erro ao carregar logo: {e}")
            
        # Título
        c.setFont("Helvetica-Bold", 36)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(width / 2, height - 220, "CERTIFICADO")

        # Subtítulo
        c.setFont("Helvetica", 18)
        c.drawCentredString(width / 2, height - 260, "Certificamos que")

        # Preparar linhas do curso com quebra
        linhas_curso = quebrar_linha_curso(curso)
        curso_formatado = '\n'.join(linhas_curso).upper()

        # Conteúdo principal
        c.setFont("Helvetica", 16)
        y_posicao = height - 320

        # Linhas de texto centralizadas
        textos = [
            nome.upper(),
            f"CPF: {formatar_cpf(cpf)}",
            "Concluiu o curso de:",
            curso_formatado,
            f"Ministrado por {instrutor}"
        ]

        # Define fonte para o nome do aluno como "Helvetica-Bold"
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, y_posicao, textos[0])
        y_posicao -= 30 

        # Define fonte para o restante do texto como "Helvetica"
        c.setFont("Helvetica", 16)

        for texto in textos[1:]:
            if '\n' in texto:
                for linha in texto.split('\n'):
                    c.drawCentredString(width / 2, y_posicao, linha)
                    y_posicao -= 30
            else:
                c.drawCentredString(width / 2, y_posicao, texto)
                y_posicao -= 30
        
        # Linha de assinatura
        c.setStrokeColorRGB(0, 0, 0)
        c.line(width / 2 - 100, 175, width / 2 + 100, 175)
        
        # Nome e cargo do instrutor na linha de assinatura
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, 155, f"{instrutor}")
        c.drawCentredString(width / 2, 140, f"{cargo}")

        # Data de emissão
        c.setFont("Helvetica", 10)
        data_formatada = formatar_data(datetime.now())
        c.drawCentredString(width / 2, 80, f"Emitido em {data_formatada}")

        c.save()
        buffer.seek(0)
        return buffer

    except Exception as e:
        st.error(f"Erro ao gerar certificado: {e}")
        return None

# Função para calcular carga horária
def calcular_carga_horaria(curso):
    carga_padrao = 40  # Definir uma carga horária padrão
    return carga_padrao

# Função principal
def main():
    st.title("Gerador de Certificados")
    
    # Criar abas
    tab1, tab2, tab3 = st.tabs(["Gerar Certificado", "Consultar/Reimprimir", "Editar Dados do Aluno"])
    
    with tab1:
        st.header("Gerar Novo Certificado")
        if st.button("Limpar Base de Dados"):
            limpar_banco_dados()
            st.success("Base de dados limpa com sucesso!")
        # Campos de input
        nome = st.text_input("Nome Completo")
        cpf = st.text_input("CPF")
        curso = st.text_input("Curso")
        instrutor = st.text_input("Instrutor")
        cargo = st.text_input("Cargo do Instrutor")
        
        logo = st.file_uploader("Carregar Logo (opcional)", type=['png', 'jpg', 'jpeg'])
        
        # Botão para gerar certificado
        if st.button("Gerar Certificado"):
            # Validações
            if not all([nome, cpf, curso, instrutor, cargo]):
                st.error("Por favor, preencha todos os campos obrigatórios.")
            elif not validar_cpf(cpf):
                st.error("CPF inválido. Por favor, digite um CPF válido.")
            else:
                # Processar logo
                logo_bytes = None
                if logo:
                    try:
                        logo_bytes = logo.read()
                    except Exception as e:
                        st.error(f"Erro ao processar a logo: {e}")
                
                # Gerar certificado
                try:
                    pdf = gerar_certificado_pdf(
                        nome=nome, 
                        cpf=cpf, 
                        curso=curso, 
                        instrutor=instrutor, 
                        cargo=cargo, 
                        logo_bytes=logo_bytes
                    )

                    # Salva os dados no banco de dados, independente do resultado da geração do PDF
                    salvar_certificado(nome, cpf, curso, instrutor, cargo, logo_bytes)
                    
                    if pdf:
                        # Botão de download
                        st.download_button(
                            label="Baixar Certificado",
                            data=pdf,
                            file_name=f"certificado_{nome}_{cpf}.pdf",
                            mime="application/pdf"
                        )
                        
                        st.success("Certificado gerado com sucesso!")
                    else:
                        st.error("Falha ao gerar o certificado.")
                
                except Exception as e:
                    st.error(f"Erro ao gerar o certificado: {e}")
    
    with tab2:
        st.header("Consultar e Reimprimir Certificados")
        
        # Carregar dados existentes
        try:
            df = carregar_dados()
            
            if df.empty:
                st.warning("Nenhum certificado encontrado no banco de dados.")
            else:
                # Campo de busca
                busca = st.text_input("Buscar por Nome ou CPF:")
                
                # Filtrar dataframe
                if busca:
                    df_filtrado = df[
                        (df['Nome'].str.contains(busca, case=False, na=False)) | 
                        (df['CPF'].str.contains(busca, case=False, na=False))
                    ]
                else:
                    df_filtrado = df
                
                # Exibir dataframe
                if not df_filtrado.empty:
                    st.dataframe(df_filtrado[['Nome', 'CPF', 'Curso', 'Data']])
                    
                    # Seleção de certificados para reimprimir
                    certificados_selecionados = st.multiselect(
                        "Selecione os certificados para reimprimir", 
                        df_filtrado['Nome'].tolist()
                    )
                    
                    # Botão de reimprimir certificados selecionados
                    if st.button("Reimprimir Certificados Selecionados"):
                        for nome_selecionado in certificados_selecionados:
                            # Encontrar dados do certificado
                            row = df_filtrado[df_filtrado['Nome'] == nome_selecionado].iloc[0]
                            
                            # Gerar PDF do certificado
                            pdf = gerar_certificado_pdf(
                                nome=row['Nome'], 
                                cpf=row['CPF'], 
                                curso=row['Curso'], 
                                instrutor=row.get('Instrutor', ''), 
                                cargo=row.get('Cargo', ''), 
                                logo_bytes=carregar_logo(row['CPF'])
                            )
                            
                            # Botão de download para cada certificado
                            st.download_button(
                                label=f"Baixar Certificado - {row['Nome']}",
                                data=pdf,
                                file_name=f"certificado_{row['Nome']}_{row['CPF']}.pdf",
                                mime="application/pdf"
                            )
                else:
                    st.warning("Nenhum certificado encontrado com esse filtro.")
        
        except Exception as e:
            st.error(f"Erro ao carregar certificados: {str(e)}")
    
    with tab3:
        st.header("Editar Dados do Aluno")
    
        # Carregar dados existentes
        df = carregar_dados()
        
        if df.empty:
            st.warning("Nenhum certificado encontrado no banco de dados.")
        else:
            # Campo de busca
            busca_edicao = st.text_input("Buscar Aluno por Nome ou CPF para Edição")
            
            # Filtrar dataframe
            if busca_edicao:
                df_filtrado_edicao = df[
                    (df['Nome'].str.contains(busca_edicao, case=False, na=False)) | 
                    (df['CPF'].str.contains(busca_edicao, case=False, na=False))
                ]
            else:
                df_filtrado_edicao = df
            
            # Exibir resultados da busca
            if not df_filtrado_edicao.empty:
                # Selecionar aluno para edição
                aluno_selecionado = st.selectbox(
                    "Selecione o Aluno", 
                    df_filtrado_edicao['Nome'].tolist()
                )
                
                # Encontrar dados do aluno selecionado
                aluno_dados = df_filtrado_edicao[df_filtrado_edicao['Nome'] == aluno_selecionado].iloc[0]
                
                # Formulário de edição
                with st.form(key='edicao_aluno'):
                    novo_nome = st.text_input("Nome", value=str(aluno_dados['Nome']), key="edit_nome")
                    novo_cpf = st.text_input("CPF", value=str(aluno_dados['CPF']), key="edit_cpf", disabled=True)
                    novo_curso = st.text_input("Curso", value=str(aluno_dados['Curso']), key="edit_curso")
                    novo_instrutor = st.text_input("Instrutor", value=str(aluno_dados.get('Instrutor', '')), key="edit_instrutor")
                    novo_cargo = st.text_input("Cargo do Instrutor", value=str(aluno_dados.get('Cargo', '')), key="edit_cargo")
                    
                    # Botão de salvar
                    botao_salvar = st.form_submit_button("Salvar Alterações")
                    
                    if botao_salvar:
                        # Atualizar no banco de dados
                        try:
                            conn = sqlite3.connect('certificados.db')
                            cursor = conn.cursor()
                            
                            cursor.execute('''
                                UPDATE certificados 
                                SET Nome=?, Curso=?, Instrutor=?, Cargo=? 
                                WHERE CPF=?
                            ''', (novo_nome, novo_curso, novo_instrutor, novo_cargo, novo_cpf))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success("Dados atualizados com sucesso!")
                            
                            # Recarregar dados
                            st.experimental_rerun()
                        
                        except Exception as e:
                            st.error(f"Erro ao atualizar dados: {e}")
                            if conn:
                                conn.rollback()
            else:
                st.warning("Nenhum aluno encontrado.")

# Importante: Adicionar esta linha para rodar o aplicativo
if __name__ == "__main__":
    main()