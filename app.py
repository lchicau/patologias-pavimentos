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
    "Carrega a fotografia. O sistema executa a análise integrada multi-perspetiva"
    " num único pedido otimizado para poupar cota da API."
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

  df_mapa = pd.DataFrame({"lat": [lat], "lon": [lon]})
  st.sidebar.map(df_mapa, zoom=15, use_container_width=True)
else:
  st.sidebar.info(
      "Permite o acesso à localização no browser para visualizar o mapa."
  )

# Obter a data atual do sistema em tempo real (Formato: DD/MM/AAAA)
data_atual = datetime.now().strftime("%d/%m/%Y")


# Função segura com múltiplos modelos de fallback (evita erros 503 e otimiza chamadas)
def chamar_gemini_com_fallback(
    prompt, imagem_bytes=None, mime_type=None, system_instruction=None
):
  modelos_a_tentar = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

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
          or "NOT_FOUND" in str(e)
          or "429" in str(e)
      ):
        continue
      else:
        raise e
  raise Exception(
      "Limite de quota atingido ou servidores sobrecarregados. Por favor,"
      " aguarda alguns minutos."
  )


# Função para estimar a área com base na imagem
def estimar_area_por_imagem(imagem_bytes, mime_type):
  prompt = (
      "Analisa esta fotografia de uma patologia num pavimento. Estima"
      " unicamente a área aproximada afetada em metros quadrados (m²)."
      " Responde apenas com o valor numérico (ex: 12.5), sem texto adicional."
  )
  try:
    texto_resposta = chamar_gemini_com_fallback(
        prompt, imagem_bytes, mime_type
    )
    nums = re.findall(r"\d+\.?\d*", texto_resposta)
    return float(nums[0]) if nums else 10.0
  except Exception:
    return 10.0


# --- CLASSE PDF ---
class PDF(FPDF):

  def header(self):
    self.set_font("helvetica", "B", 11)
    self.cell(
        0, 10, "Relatório Técnico - Inspeção de Pavimentos (LNEC/IP)", 0, 1, "C"
    )
    self.ln(3)

  def footer(self):
    self.set_y(-12)
    self.set_font("helvetica", "I", 8)
    self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")


def gerar_pdf_relatorio(texto_relatorio):
  pdf = PDF(orientation="P", unit="mm", format="A4")
  pdf.set_auto_page_break(auto=True, margin=15)
  pdf.add_page()
  pdf.set_left_margin(10)
  pdf.set_right_margin(10)
  pdf.set_font("helvetica", size=9)
  largura_util = 190

  for linha in texto_relatorio.split("\n"):
    linha_limpa = (
        linha.replace("**", "").replace("#", "").replace("###", "").strip()
    )
    if linha_limpa == "":
      pdf.ln(3)
    else:
      pdf.multi_cell(
          largura_util,
          5,
          linha_limpa.encode("latin-1", "replace").decode("latin-1"),
      )
  return bytes(pdf.output())


# Função de Análise Integrada (Substitui múltiplas chamadas por uma única altamente estruturada)
def analisar_patologia_integrada(
    imagem_bytes, mime_type, area_m2, classe_trafego, localizacao, data_envio
):
  system_instruction = f"""Tu és uma equipa multidisciplinar de engenharia rodoviária em Portugal, englobando um Agente Inspetor (Visão), um Agente Normativo (especialista LNEC, antiga JAE e Infraestruturas de Portugal - IP) e um Agente Orçamentista.

    REGRAS OBRIGATÓRIAS E INEGOCIÁVEIS:
    1. Utiliza RIGOROSAMENTE a Data de Avaliação fornecida ({data_envio}). É estritamente proibido inventar datas.
    2. Considera o contexto climático e geográfico da localização exata obtida por GPS fornecida.
    3. Executa a análise combinada (Diagnóstico Visual -> Reabilitação Normativa LNEC/IP -> Quantidades e Custos de Mercado) num único relatório detalhado em Markdown.

    Estrutura obrigatória do relatório:
    1. **Cabeçalho Técnico:** Data de Avaliação: {data_envio} | Coordenadas GPS: {localizacao} | Área: {area_m2} m² | Tráfego: {classe_trafego}
    2. **Diagnóstico e Nível de Severidade:** Identificação técnica da patologia e grau de urgência.
    3. **Causa Provável:** Análise fundamentada cruzando tráfego e clima local.
    4. **Método de Reparação Recomendado (Normas LNEC/IP):** Procedimento passo a passo alinhado com as especificações nacionais.
    5. **Materiais e Equipamentos Necessários:** Especificações técnicas reais dos materiais (ex: betume 35/50 ou 50/70, emulsão C60B3).
    6. **Estimativa de Custos:** Baseada estritamente na área de {area_m2} m², aplicando preços médios de mercado em Portugal.
    7. **Manutenção Preventiva / Corretiva Futura.**"""

  prompt = f"""Analisa esta patologia num pavimento betuminoso utilizando apenas os seguintes dados reais e atuais:
    - Data da Avaliação: {data_envio}
    - Área estimada afetada: {area_m2} m²
    - Classe de Tráfego da via: {classe_trafego}
    - Localização / Coordenadas GPS: {localizacao}"""

  return chamar_gemini_com_fallback(
      prompt, imagem_bytes, mime_type, system_instruction
  )


# --- INTERFACE DO UTILIZADOR ---
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
  if st.button("Gerar Relatório Técnico Integrado (LNEC / IP)"):
    with st.spinner(
        "A processar análise multidisciplinar (Inspetor, Normativo e"
        " Orçamentista)..."
    ):
      try:
        relatorio_final = analisar_patologia_integrada(
            image_bytes,
            mime_type,
            area_m2,
            classe_trafego,
            localizacao_str,
            data_atual,
        )

        st.markdown("---")
        st.markdown("### Relatório Técnico e Orçamental (LNEC / IP)")
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
        st.error(f"Erro ao processar o relatório: {e}")
