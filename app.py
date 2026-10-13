from datetime import datetime
import os
from fpdf import FPDF
import pandas as pd
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

# Configuração da página
st.set_page_config(
    page_title="Agente Especialista de Pavimentos", page_icon="🛣️", layout="wide"
)

st.title(
    "🛣️ Agente Especialista de Pavimentos (Motor Autónomo Normativo LNEC / IP)"
)
st.write(
    "Sistema autónomo criado de raiz com base nas normas portuguesas (LNEC,"
    " JAE, IP). Cálculos baseados em parâmetros reais de engenharia, sem"
    " localizações predefinidas."
)

# 1. Obter a localização automática do dispositivo (GPS)
st.sidebar.subheader("📍 Geolocalização e Mapa")
loc = streamlit_geolocation()

localizacao_str = "Localização não detetada (Ativa o GPS no browser)"
lat_val, lon_val = None, None

if loc and loc.get("latitude") and loc.get("longitude"):
  lat_val = loc.get("latitude")
  lon_val = loc.get("longitude")
  localizacao_str = (
      f"Coordenadas GPS: Latitude {lat_val}, Longitude {lon_val} (Portugal)"
  )
  st.sidebar.success("Localização obtida com sucesso!")

  df_mapa = pd.DataFrame({"lat": [lat_val], "lon": [lon_val]})
  st.sidebar.map(df_mapa, zoom=15, use_container_width=True)
else:
  st.sidebar.info(
      "GPS inativo ou não permitido. Nenhuma localização pré-definida aplicada."
  )

# Data atual do sistema obtida de forma blindada (DD/MM/AAAA)
agora = datetime.now()
data_atual = f"{agora.day:02d}/{agora.month:02d}/{agora.year}"


# --- CLASSE DO AGENTE ESPECIALISTA (CÁLCULO PARAMÉTRICO REAL) ---
class AgenteEspecialistaPavimentos:

  def __init__(
      self, patologia, severidade, area_m2, classe_trafego, localizacao, data
  ):
    self.patologia = patologia
    self.severidade = severidade
    self.area_m2 = area_m2
    self.classe_trafego = classe_trafego
    self.localizacao = localizacao
    self.data = data

  def gerar_diagnostico(self):
    diagnosticos = {
        "Fendilhamento por Fadiga (CRA)": (
            "Apresenta rede de fissuras interligadas em forma de crosta de"
            " tartaruga, indício claro de fadiga da estrutura do pavimento sob"
            " acções repetidas de carga e/ou enfraquecimento da fundação."
        ),
        "Deformação Permanente / Abatimento (RUT)": (
            "Regista sulcos ou abatimentos longitudinais na trajetória das"
            " rodas, resultantes da consolidação plástica ou corte nas camadas"
            " inferiores ou instabilidade da mistura betuminosa."
        ),
        "Desagregação / Perda de Material (RAV)": (
            "Observa-se perda de agregado na superfície e desgaste da matriz"
            " betuminosa, potenciado por envelhecimento do ligante e acção"
            " meteorológica."
        ),
        "Buracos / Cavas (POT)": (
            "Cavidade de gume vivo com remoção total de material das camadas"
            " superiores e penetração de água na base, exigindo intervenção"
            " imediata."
        ),
    }
    return diagnosticos.get(
        self.patologia, "Patologia estrutural ou superficial identificada."
    )

  def calcular_reparacao(self):
    if self.severidade == "Alta" or "Buracos" in self.patologia:
      espessura_cm = 6.0
      espessura_str = "6 cm"
      camada_aplicacao = (
          "Fresagem de 6 cm, varrimento mecânico, aplicação de emulsão"
          " betuminosa de pitada C60B3 (taxa de 0.6 kg/m²) e Execução de Camada"
          " de Desgaste em Betão Bituminoso (AC 14 surf) com betume modificado"
          " PmB 45/80-50."
      )
    else:
      espessura_cm = 4.0
      espessura_str = "4 cm"
      camada_aplicacao = (
          "Fresagem de desbastamento de 4 cm, rega de colagem com emulsão"
          " catiónica C60B3 (0.5 kg/m²) e aplicação de nova camada de desgaste"
          " (AC 14 surf)."
      )
    return espessura_cm, espessura_str, camada_aplicacao

  def calcular_orcamento_parametrico(self):
    espessura_cm, _, _ = self.calcular_reparacao()
    espessura_m = espessura_cm / 100.0

    volume_m3 = self.area_m2 * espessura_m
    massa_ton = volume_m3 * 2.45

    custo_fresagem = self.area_m2 * espessura_cm * 1.10
    custo_mistura = massa_ton * 95.00
    custo_emulsao = self.area_m2 * 1.65
    custo_seguranca = 120.00

    custo_total = (
        custo_fresagem + custo_mistura + custo_emulsao + custo_seguranca
    )

    return (
        volume_m3,
        massa_ton,
        custo_fresagem,
        custo_mistura,
        custo_emulsao,
        custo_seguranca,
        custo_total,
    )

  def compilar_relatorio(self):
    diag = self.gerar_diagnostico()
    _, espessura_str, metodo = self.calcular_reparacao()
    vol, massa, tf, tm, te, ts, total = self.calcular_orcamento_parametrico()

    relatorio = f"""### RELATÓRIO TÉCNICO DE INSPEÇÃO E REABILITAÇÃO DE PAVIMENTOS
#### 1. Cabeçalho Técnico
- Data da Avaliação: {self.data}
- Localização / Coordenadas: {self.localizacao}
- Área Afetada Intervenção: {self.area_m2} m²
- Categoria de Tráfego: {self.classe_trafego}

#### 2. Identificação da Patologia e Severidade
- Tipologia: {self.patologia}
- Nível de Severidade: {self.severidade}
- Diagnóstico Técnico: {diag}

#### 3. Análise de Causas Prováveis
A patologia decorre da conjugação entre as solicitações impostas pelo tráfego ({self.classe_trafego}) e a suscetibilidade térmica/pluviométrica da região, provocando fadiga ou deformação plástica nas camadas betuminosas.

#### 4. Método de Reparação Recomendado (Normas LNEC / IP)
- Espessura de Intervenção: {espessura_str}
- Procedimento Executivo: {metodo}

#### 5. Materiais e Equipamentos Necessários
- Emulsão Betuminosa: Emulsão catiónica de rotura rápida C60B3.
- Mistura Bituminosa: Betão bituminoso a quente (AC 14 surf).
- Equipamentos: Fresadora autopropulsada, vassoura mecânica, cilindro compactador de pneus e cilindro metálico vibratório.

#### 6. Estimativa Orçamental Paramétrica (Cálculo com Base em Quantidades)
- Volume de Material a Fresar: {vol:.2f} m³
- Massa de Mistura Bituminosa Necessária: {massa:.2f} toneladas
- Fresagem de Pavimento: {tf:.2f} €
- Fornecimento e Aplicação de Mistura Bituminosa (AC 14 surf): {tm:.2f} €
- Rega de Colagem (Emulsão C60B3): {te:.2f} €
- Sinalização Temporária e Segurança Local: {ts:.2f} €
- ESTIMATIVA ORÇAMENTAL TOTAL: {total:.2f} € (IVA não incluído)

#### 7. Recomendações de Manutenção Preventiva
- Monitorização semestral após a intervenção para deteção precoce de fissuração de junta.
- Garantir a desobstrução e eficiência dos órgãos de drenagem superficial adjacentes (valetas e aquedutos)."""

    return relatorio


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
        "Normas LNEC / IP - Motor Autónomo de Engenharia Civil",
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
        f"Página {self.page_no()} | Processado por Motor Autónomo de Engenharia",
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

  patologia_selecionada = st.selectbox(
      "Patologia Observada na Imagem:",
      [
          "Fendilhamento por Fadiga (CRA)",
          "Deformação Permanente / Abatimento (RUT)",
          "Desagregação / Perda de Material (RAV)",
          "Buracos / Cavas (POT)",
      ],
  )

  severidade_selecionada = st.selectbox(
      "Nível de Severidade:", ["Baixa", "Média", "Alta"]
  )

  area_m2 = st.number_input(
      "Área estimada da patologia (m²):",
      min_value=0.1,
      value=10.0,
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
  if st.button("Gerar Relatório Técnico Autónomo (LNEC / IP)"):
    with st.spinner(
        "A calcular parâmetros de engenharia e a gerar PDF estruturado..."
    ):
      try:
        agente = AgenteEspecialistaPavimentos(
            patologia=patologia_selecionada,
            severidade=severidade_selecionada,
            area_m2=area_m2,
            classe_trafego=classe_trafego,
            localizacao=localizacao_str,
            data=data_atual,
        )

        relatorio_final = agente.compilar_relatorio()

        st.markdown("---")
        st.markdown("### Relatório Técnico e Orçamental (Motor LNEC/IP)")
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
        st.error(f"Erro ao gerar o relatório: {e}")
