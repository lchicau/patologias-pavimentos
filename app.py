from datetime import datetime
import os
import re
from fpdf import FPDF
import pandas as pd
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
    "Carrega a fotografia de uma patologia. O agente obtém a tua localização"
    " real com mapa interativo, a data do sistema e gera o relatório técnico"
    " com PDF formatado."
)

# Inicializar o cliente Gemini
client = genai.Client()

# 1. Obter a localização automática do dispositivo (GPS) e mostrar mapa
st.sidebar.subheader("📍 Geolocalização e Mapa")
loc = streamlit_geolocation()

localizacao_str = "Localização não detetada (Ativa o GPS no browser)"
if loc and loc.get("latitude") and loc.get("longitude"):
  lat = loc.get("latitude")
  lon = loc.get("longitude")
  localizacao_str = (
      f"Coordenadas GPS: Latitude {lat}, Longitude {lon} (Portugal)"
  )
  st.sidebar.success("Localização obtida com sucesso!")

  # Criar dataframe e mostrar mapa interativo na barra lateral
  df_mapa = pd.DataFrame({"lat": [lat], "lon": [lon]})
  st.sidebar.map(df_mapa, zoom=15, use_container_width=True)
else:
  st.sidebar.info(
      "Permite o acesso à localização no browser para visualizar o mapa."
  )

# Obter a data atual do sistema em tempo real (Formato: DD/MM/AAAA)
data_atual = datetime.now().strftime("%d/%m/%Y")


# Função para estimar a área com base na imagem
def estimar_area_por_imagem(imagem_bytes, mime_type):
  prompt = (
      "Analisa esta fotografia de uma patologia num pavimento. Estima"
      " unicamente a área aproximada afetada em metros quadrados (m²)."
      " Responde apenas com o valor numérico (ex: 12.5), sem texto adicional."
  )
  try:
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            types.Part.from_bytes(data=imagem_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(temperature=0.1),
    )
    nums = re.findall(r"\d+\.?\d*", response.text)
    return float(nums[0]) if nums else 10.0
  except Exception:
    return 10.0


# Classe para construção do PDF estruturado
class PDF(FPDF):

  def header(self):
    self.set_font("helvetica", "B", 12)
    self.cell(
        0, 10, "Relatório Técnico - Inspeção de Pavimentos (LNEC/IP)", 0, 1, "C"
    )
    self.ln(5)

  def footer(self):
    self.set_y(-15)
    self.set_font("helvetica", "I", 8)
    self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")


def gerar_pdf_relatorio(texto_relatorio):
  pdf = PDF()
  pdf.add_page()
  pdf.set_font("helvetica", size=10)

  for linha in texto_relatorio.split("\n"):
    linha_limpa = (
        linha.replace("**", "").replace("#", "").replace("###", "").strip()
    )
    if linha_limpa == "":
      pdf.ln(4)
    else:
      pdf.multi_cell(
          0,
          6,
          linha_limpa.encode("latin-1", "replace").decode("latin-1"),
      )
  return bytes(pdf.output())


# Função principal de análise técnica com restrição estricta de dados reais
def analisar_patologia(
    imagem_bytes, mime_type, area_m2, classe_trafego, localizacao, data_envio
):
  system_instruction = f"""Tu és um Engenheiro Civil perito em pavimentação flexível e patologias de pavimentos betuminosos, com profundo conhecimento das normativas e especificações técnicas aplicáveis em Portugal (LNEC, antiga JAE e Infraestruturas de Portugal, I.P. - IP).

    REGRAS OBRIGATÓRIAS E INEGOCIÁVEIS:
    1. Utiliza RIGOROSAMENTE a Data de Avaliação fornecida ({data_envio}). É estritamente proibido inventar datas passadas, futuras ou fictícias.
    2. Considera o contexto climático e geográfico da localização exata obtida por GPS fornecida.
    3. Baseia a análise exclusivamente nos dados reais fornecidos pelo utilizador e pelo sistema (imagem, área, tráfego, GPS e data atual).

    Gera um relatório técnico detalhado em Markdown com a seguinte estrutura:
    1. **Cabeçalho Técnico:** Incluindo obrigatoriamente a Data de Avaliação: {data_envio} e as Coordenadas GPS fornecidas.
    2. **Identificação da Patologia:** Nome técnico e nível de severidade (Baixa, Média, Alta).
    3. **Causa Provável:** Análise técnica fundamentada tendo em conta a ação do tráfego e o clima local da região.
    4. **Método de Reparação Recomendado (Normas LNEC/IP):** Procedimento passo a passo alinhado com as especificações nacionais.
    5. **Manutenção Preventiva / Corretiva Futura:** Recomendações específicas para preservação da infraestrutura.
    6. **Materiais e Equipamentos Necessários:** Especificações técnicas reais dos materiais (ex: betume 35/50 ou 50/70, emulsão C60B3).
    7. **Estimativa de Custos:** Baseada estritamente na área fornecida, aplicando preços médios de mercado em Portugal."""

  prompt = f"""Analisa esta patologia num pavimento betuminoso utilizando apenas os seguintes dados reais e atuais:
    - Data da Avaliação: {data_envio}
    - Área estimada afetada: {area_m2} m²
    - Classe de Tráfego da via: {classe_trafego}
    - Localização / Coordenadas GPS: {localizacao}"""

  response = client.models.generate_content(
      model="gemini-3.8-flash",
      contents=[
          types.Part.from_bytes(data=imagem_bytes, mime_type=mime_type),
          prompt,
      ],
      config=types.GenerateContentConfig(
          system_instruction=system_instruction,
          temperature=0.2,
      ),
  )
  return response.text


# Interface do Utilizador
col1, col2 = st.columns([1, 1])

with col1:
  uploaded_file = st.file_uploader(
      "Escolhe uma fotografia...", type=["jpg", "jpeg", "png"]
  )

  if "area_estimada" not in st.session_state:
    st.session_state.area_estimada = 10.0

  if uploaded_file is not None:
    st.image(
        uploaded_file, caption="Fotografia da Patologia", use_container_width=True
    )

    image_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type

    if st.button("🔄 Reestimar Área por IA"):
      with st.spinner("A estimar área através da imagem..."):
        st.session_state.area_estimada = estimar_area_por_imagem(
            image_bytes, mime_type
        )
        st.rerun()

  area_m2 = st.number_input(
      "Área estimada da patologia (m²):",
      min_value=0.1,
      value=float(st.session_state.area_estimada),
      step=0.5,
  )

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

  st.text_input(
      "Localização Detetada (GPS do Dispositivo):", value=localizacao_str
  )
  st.info(f"📅 Data da Análise (Sistema): {data_atual}")

if uploaded_file is not None:
  if st.button("Gerar Relatório Técnico Completo (LNEC / IP)"):
    with st.spinner(
        "A processar imagem, coordenadas GPS, data real e especificações"
        " LNEC/IP..."
    ):
      try:
        relatorio = analisar_patologia(
            image_bytes,
            mime_type,
            area_m2,
            classe_trafego,
            localizacao_str,
            data_atual,
        )
        st.markdown("---")
        st.markdown("### Relatório Técnico e Orçamental Adaptado")
        st.markdown(relatorio)

        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        pdf_filename = f"{timestamp_str}_PDRV.pdf"
        pdf_bytes = gerar_pdf_relatorio(relatorio)

        st.download_button(
            label="📥 Descarregar Relatório em PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
        )

      except Exception as e:
        st.error(f"Erro ao processar a imagem: {e}")
