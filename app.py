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
    "🛣️ Agente de Diagnóstico e Reabilitação de Pavimentos (Arquitetura Multi-Agente"
    " LNEC / IP)"
)
st.write(
    "Carrega a fotografia. Uma equipa de sub-agentes especializados (Inspetor,"
    " Normativo, Orçamentista e Sintetizador) trabalhará em conjunto para gerar"
    " o relatório técnico e o PDF."
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


# Função segura com múltiplos modelos de fallback (evita erros 503)
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
      if "503" in str(e) or "UNAVAILABLE" in str(e) or "NOT_FOUND" in str(e):
        continue
      else:
        raise e
  raise Exception(
      "Os servidores estão temporariamente sobrecarregados. Por favor, tenta"
      " novamente em instantes."
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


# --- PIPELINE DE SUB-AGENTES ESPECIALIZADOS ---


def sub_agente_inspetor(imagem_bytes, mime_type):
  """Sub-Agente 1: Focado exclusivamente na identificação visual e severidade."""
  system_instruction = (
      "Tu és o Agente Inspetor de Visão Artificial especializado em patologias"
      " de pavimentos betuminosos. O teu único trabalho é identificar"
      " tecnicamente a patologia presente na imagem e avaliar o nível de"
      " severidade (Baixa, Média, Alta)."
  )
  prompt = (
      "Identifica a patologia apresentada e avalia o nível de severidade com"
      " rigor técnico."
  )
  return chamar_gemini_com_fallback(
      prompt, imagem_bytes, mime_type, system_instruction
  )


def sub_agente_normativo(diagnostico_inspetor, classe_trafego, localizacao):
  """Sub-Agente 2: Aplica especificações técnicas LNEC / IP e clima."""
  system_instruction = (
      "Tu és o Agente Normativo e Especialista em Vias de Comunicação. Tens"
      " profundo conhecimento das normas do LNEC, antiga JAE e Infraestruturas"
      " de Portugal (IP). O teu trabalho é definir a causa provável e o método"
      " de reparação exato (espessuras de fresagem, ligantes, camadas de"
      " desgaste) tendo em conta a classe de tráfego e o clima da região."
  )
  prompt = f"""Com base no seguinte diagnóstico visual do Inspetor:
    {diagnostico_inspetor}
    
    E considerando:
    - Classe de Tráfego: {classe_trafego}
    - Localização / Clima: {localizacao}
    
    Define a causa provável e o método de reparação em conformidade com as normas LNEC/IP."""
  return chamar_gemini_com_fallback(prompt, system_instruction=system_instruction)


def sub_agente_orcamentista(metodo_reparacao, area_m2):
  """Sub-Agente 3: Calcula quantidades e custos de mercado em Portugal."""
  system_instruction = (
      "Tu és o Agente Orçamentista de Obras Rodoviárias em Portugal. O teu"
      " trabalho é calcular os materiais necessários (betume, emulsão,"
      " misturas betuminosas) e estimar os custos em euros com base na área"
      " fornecida e nos preços médios atuais de mercado."
  )
  prompt = f"""Com base no seguinte método de reparação:
    {metodo_reparacao}
    
    E na área afetada de {area_m2} m², calcula os materiais necessários e apresenta uma estimativa orçamental detalhada em Portugal."""
  return chamar_gemini_com_fallback(prompt, system_instruction=system_instruction)


def sub_agente_sintetizador(
    diagnostico,
    normas,
    orcamento,
    data_envio,
    localizacao,
    area_m2,
    classe_trafego,
):
  """Sub-Agente 4: Compila tudo num relatório final estruturado."""
  system_instruction = (
      "Tu és o Agente Coordenador e Sintetizador de Relatórios Técnicos. Deves"
      " compilar a informação dos sub-agentes num relatório final em Markdown"
      " limpo, profissional e estruturado para engenharia."
  )
  prompt = f"""Compila os dados recolhidos pelos sub-agentes num relatório técnico final com a seguinte estrutura exata:
    1. **Cabeçalho Técnico:** Data de Avaliação: {data_envio} | Coordenadas GPS: {localizacao} | Área: {area_m2} m² | Tráfego: {classe_trafego}
    2. **Diagnóstico e Severidade:** (Resumo do Inspetor) {diagnostico}
    3. **Análise de Causas e Reabilitação (Normas LNEC/IP):** (Resumo Normativo) {normas}
    4. **Orçamentação e Materiais:** (Resumo Orçamentista) {orcamento}
    5. **Recomendações de Manutenção Preventiva.**"""
  return chamar_gemini_com_fallback(prompt, system_instruction=system_instruction)


# --- CLASSE PDF ---
class PDF(FPDF):

  def header(self):
    self.set_font("helvetica", "B", 11)
    self.cell(
        0,
        10,
        "Relatório Técnico Multi-Agente - Inspeção de Pavimentos (LNEC/IP)",
        0,
        1,
        "C",
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
  if st.button("Gerar Relatório Técnico Multi-Agente (LNEC / IP)"):
    # Execução do Pipeline Multi-Agente com feedback visual por etapas
    try:
      with st.spinner("🔍 Agente Inspetor a analisar imagem e patologia..."):
        diag_inspetor = sub_agente_inspetor(image_bytes, mime_type)

      with st.spinner(
          "📚 Agente Normativo a cruzar com normas LNEC/IP e clima..."
      ):
        prescricao_normas = sub_agente_normativo(
            diag_inspetor, classe_trafego, localizacao_str
        )

      with st.spinner(
          "💰 Agente Orçamentista a calcular volumes e custos em Portugal..."
      ):
        orcamento = sub_agente_orcamentista(prescricao_normas, area_m2)

      with st.spinner(
          "📋 Agente Sintetizador a compilar o relatório técnico final..."
      ):
        relatorio_final = sub_agente_sintetizador(
            diag_inspetor,
            prescricao_normas,
            orcamento,
            data_atual,
            localizacao_str,
            area_m2,
            classe_trafego,
        )

      st.markdown("---")
      st.markdown("### Relatório Técnico Multi-Agente (LNEC / IP)")
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
      st.error(f"Erro no pipeline multi-agente: {e}")
