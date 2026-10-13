from datetime import datetime
import os
import re
from fpdf import FPDF
import pandas as pd
import requests
import streamlit as st
from google import genai
from google.genai import types
from streamlit_geolocation import streamlit_geolocation

# Configuração da página
st.set_page_config(
    page_title="Agente de Inspeção de Pavimentos", page_icon="🛣️", layout="wide"
)

st.title(
    "🛣️ Agente de Diagnóstico e Reabilitação de Pavimentos (Normas LNEC / IP)"
)
st.write(
    "Carrega a fotografia da patologia. O agente deteta automaticamente a"
    " patologia, estima a área, obtém as coordenadas GPS e a **morada real** do"
    " local, gerando o relatório técnico em PDF."
)

# Inicializar o cliente Gemini
client = genai.Client()


# Função para obter a morada legível a partir do GPS (Geocodificação Reversa)
def obter_morada_reversa(lat, lon):
  try:
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
    headers = {"User-Agent": "AgentePavimentosApp/1.0"}
    response = requests.get(url, headers=headers, timeout=4)
    if response.status_code == 200:
      data = response.json()
      return data.get(
          "display_name", f"Latitude {lat}, Longitude {lon} (Portugal)"
      )
  except Exception:
    pass
  return f"Latitude {lat}, Longitude {lon} (Portugal)"


# 1. Obter a localização automática do dispositivo (GPS) e Morada
st.sidebar.subheader("📍 Localização e Morada Real")
loc = streamlit_geolocation()

localizacao_str = "Localização não detetada (Ativa o GPS no browser)"
lat_val, lon_val = None, None

if loc and loc.get("latitude") and loc.get("longitude"):
  lat_val = loc.get("latitude")
  lon_val = loc.get("longitude")
  localizacao_str = obter_morada_reversa(lat_val, lon_val)
  st.sidebar.success("Localização e morada detetadas com sucesso!")

  df_mapa = pd.DataFrame({"lat": [lat_val], "lon": [lon_val]})
  st.sidebar.map(df_mapa, zoom=16, use_container_width=True)
else:
  st.sidebar.info(
      "Ativa a localização no browser para obter a rua e coordenadas GPS."
  )

# Data atual do sistema em tempo real (DD/MM/AAAA)
agora = datetime.now()
data_atual = f"{agora.day:02d}/{agora.month:02d}/{agora.year}"


# Função segura com fallback de modelos para evitar erros 503/429
def chamar_gemini_com_fallback(
    prompt, imagem_bytes=None, mime_type=None, system_instruction=None
):
  modelos_a_tentar = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-3.8-flash"]

  config = types.GenerateContentConfig(temperature=0.2)
  if system_instruction:
    config.system_instruction = system_instruction

  contents = []
  if imagem_bytes and mime_type:
    contents.append(types.Part.from_bytes(data=imagem_bytes, mime_type=mime_type))
  contents.append(prompt)

  for modelo in modelos_a_tentar:
    try:
      response = client.models.generate_content(
          model=modelo, contents=contents, config=config
      )
      return response.text
    except Exception as e:
      if (
          "503" in str(e)
          or "UNAVAILABLE" in str(e)
          or "429" in str(e)
          or "NOT_FOUND" in str(e)
      ):
        continue
      else:
        raise e
  raise Exception(
      "Servidores temporariamente ocupados ou limite de cota atingido. Tenta"
      " novamente em instantes."
  )


# Análise Inteligente Integrada (Identifica patologia, severidade e área automaticamente)
def analisar_patologia_automaticamente(
    imagem_bytes, mime_type, classe_trafego, localizacao, data_envio
):
  system_instruction = f"""Tu és um Engenheiro Civil perito em pavimentação flexível e patologias de pavimentos betuminosos em Portugal, com profundo conhecimento das normas do LNEC e Infraestruturas de Portugal (IP).

    REGRAS OBRIGATÓRIAS:
    1. Utiliza estritamente a Data de Avaliação: {data_envio}.
    2. Analisa a imagem para identificar autonomamente:
       - A patologia exata (ex: Fendilhamento por fadiga, Deformação/RUT, Desagregação, Buracos/Cavas).
       - O nível de severidade (Baixa, Média, Alta).
       - Uma estimativa rigorosa da área afetada em metros quadrados (m²).
    3. Calcula o orçamento paramétrico com base na área estimada e preços de mercado em Portugal (incluindo fresagem, emulsão C60B3 e mistura betuminosa AC 14 surf).
    4. Estrutura o relatório detalhadamente em Markdown.

    Estrutura obrigatória:
    1. **Cabeçalho Técnico:** Data: {data_envio} | Local: {localizacao} | Tráfego: {classe_trafego}
    2. **Diagnóstico e Identificação Automática:** Patologia detetada, severidade e área estimada (m²).
    3. **Causa Provável:** Fundamentação técnica considerando o tráfego e o meio envolvente.
    4. **Método de Reparação Recomendado (Normas LNEC/IP):** Espessuras, fresagem e camadas de desgaste.
    5. **Materiais e Equipamentos Necessários:** Especificações reais (ex: emulsão C60B3, betume).
    6. **Estimativa Orçamental Paramétrica:** Custos detalhados em euros (€).
    7. **Manutenção Preventiva / Corretiva Futura.**"""

  prompt = f"""Analisa esta fotografia de pavimento e gera o relatório técnico completo considerando:
    - Categoria de Tráfego: {classe_trafego}
    - Localização / Morada: {localizacao}
    - Data da Avaliação: {data_envio}"""

  return chamar_gemini_com_fallback(
      prompt, imagem_bytes, mime_type, system_instruction
  )


# --- CLASSE PDF PROFISSIONAL COM MARGENS RIGOROSAS ---
class PDF(FPDF):

  def header(self):
    self.set_font("helvetica", "B", 10)
    self.set_text_color(20, 50, 90)
    self.cell(
        0,
        6,
        "RELATÓRIO TÉCNICO DE INSPEÇÃO E REABILITAÇÃO DE PAVIMENTOS",
        0,
        1,
        "C",
    )
    self.set_font("helvetica", "I", 8)
    self.set_text_color(100, 100, 100)
    self.cell(
        0,
        5,
        "Normas LNEC / IP - Inspeção Multimodal por Inteligência Artificial",
        0,
        1,
        "C",
    )
    self.ln(4)

  def footer(self):
    self.set_y(-12)
    self.set_font("helvetica", "I", 8)
    self.set_text_color(120, 120, 120)
    self.cell(
        0,
        10,
        f"Página {self.page_no()} | Agente Especialista de Pavimentos",
        0,
        0,
        "C",
    )


def gerar_pdf_relatorio(texto_relatorio):
  pdf = PDF(orientation="P", unit="mm", format="A4")
  pdf.set_auto_page_break(auto=True, margin=15)
  pdf.add_page()

  pdf.set_left_margin(15)
  pdf.set_right_margin(15)
  largura_util = 180

  for linha in texto_relatorio.split("\n"):
    linha_limpa = linha.strip()

    if linha_limpa.startswith("### "):
      continue

    if linha_limpa.startswith("#### "):
      pdf.ln(4)
      pdf.set_font("helvetica", "B", 10)
      pdf.set_text_color(20, 50, 90)
      titulo = linha_limpa.replace("#### ", "").replace("**", "")
      pdf.cell(
          largura_util,
          6,
          titulo.encode("latin-1", "replace").decode("latin-1"),
          0,
          1,
          "L",
      )
      pdf.set_font("helvetica", size=9)
      pdf.set_text_color(0, 0, 0)
    elif linha_limpa.startswith("- "):
      pdf.set_font("helvetica", size=9)
      pdf.set_text_color(0, 0, 0)
      item = "  * " + linha_limpa.replace("- ", "").replace("**", "")
      pdf.multi_cell(
          largura_util, 5, item.encode("latin-1", "replace").decode("latin-1")
      )
    elif linha_limpa != "":
      pdf.set_font("helvetica", size=9)
      pdf.set_text_color(0, 0, 0)
      texto = linha_limpa.replace("**", "")
      pdf.multi_cell(
          largura_util, 5, texto.encode("latin-1", "replace").decode("latin-1")
      )
    else:
      pdf.ln(2)

  return bytes(pdf.output())


# --- INTERFACE DO UTILIZADOR ---
col1, col2 = st.columns([1, 1])

with col1:
  uploaded_file = st.file_uploader(
      "Escolhe a fotografia da patologia...", type=["jpg", "jpeg", "png"]
  )

  if uploaded_file is not None:
    st.image(
        uploaded_file, caption="Fotografia da Patologia", use_container_width=True
    )
    image_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type

with col2:
  opcoes_trafego = [
      "Tráfego Ligeiro / Caminho Agrícola / Loteamento Habitacional (T6/T5)",
      "Tráfego Médio / Estrada Municipal / Arruamento Urbano Principal (T4/T3)",
      "Tráfego Pesado / Estrada Nacional / Zona Industrial (T2)",
      "Tráfego Muito Pesado / Itinerário Principal (IP/IC) ou Autoestrada (T1/T0)",
  ]
  classe_trafego = st.selectbox(
      "Tipo de Tráfego / Categoria da Via:", opcoes_trafego
  )

  st.text_input("Localização / Morada Detetada:", value=localizacao_str)
  st.info(f"📅 Data da Análise (Sistema): {data_atual}")
  st.markdown(
      "ℹ️ **Nota:** A identificação da patologia, severidade e área é feita"
      " automaticamente pela IA a partir da fotografia."
  )

if uploaded_file is not None:
  if st.button("Gerar Relatório Técnico Automático (LNEC / IP)"):
    with st.spinner(
        "A analisar imagem, a obter morada e a calcular parâmetros de"
        " engenharia..."
    ):
      try:
        relatorio_final = analisar_patologia_automaticamente(
            image_bytes, mime_type, classe_trafego, localizacao_str, data_atual
        )

        st.markdown("---")
        st.markdown(
            "### Relatório Técnico e Orçamental (IA + Normas LNEC/IP)"
        )
        st.markdown(relatorio_final)

        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        pdf_filename = f"{timestamp_str}_PDRV.pdf"
        pdf_bytes = gerar_pdf_relatorio(relatorio_final)

        st.download_button(
            label="📥 Descarregar Relatório em PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
        )

      except Exception as e:
        st.error(f"Erro ao processar a imagem: {e}")
