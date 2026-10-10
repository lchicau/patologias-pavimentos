import os
import streamlit as st
from google import genai
from google.genai import types

# Configuração da página
st.set_page_config(
    page_title="Agente de Inspeção de Pavimentos", page_icon="🛣️", layout="wide"
)

st.title(
    "🛣️ Agente de Diagnóstico e Reabilitação de Pavimentos (Normas LNEC / IP)"
)
st.write(
    "Carrega a fotografia de uma patologia num pavimento betuminoso. O agente"
    " adaptará a análise considerando o tipo de tráfego, as especificações"
    " LNEC/IP e os fatores climáticos e geográficos da região."
)

# Inicializar o cliente Gemini (certifica-te de definir a variável de ambiente GEMINI_API_KEY)
client = genai.Client()


def analisar_patologia(
    imagem_bytes, mime_type, area_m2, classe_trafego, localizacao
):
  system_instruction = """Tu és um Engenheiro Civil perito em pavimentação flexível e patologias de pavimentos betuminosos, com profundo conhecimento das normativas e especificações técnicas aplicáveis em Portugal, nomeadamente os manuais e cadernos de encargos do LNEC, da antiga Junta Autónoma de Estradas (JAE) e da Infraestruturas de Portugal, I.P. (IP).

    Ao analisar a patologia, deves considerar OBRIGATORIAMENTE:
    1. A classe de tráfego indicada pelo utilizador.
    2. O contexto climático e geográfico da localização indicada (temperaturas máximas/mínimas, amplitude térmica diurna/anual, pluviosidade e riscos de deformação plástica ou fendilhamento térmico).

    Geras um relatório técnico detalhado em Markdown com as seguintes secções:
    1. **Identificação da Patologia:** Nome técnico e nível de severidade (Baixa, Média, Alta) de acordo com a terminologia técnica nacional.
    2. **Causa Provável:** Análise técnica fundamentada, relacionando o aspeto visual com a ação do tráfego e os fatores climáticos locais.
    3. **Método de Reparação Recomendado (Normas LNEC/IP):** Procedimento passo a passo adaptado à classe de tráfego (ex: profundidade de fresagem, necessidade de ligantes modificados com polímeros, betão betuminoso AC surf/binder).
    4. **Manutenção Preventiva / Corretiva Futura:** Recomendações de drenagem, selagem e preservação específicas para as condições do clima local.
    5. **Materiais e Equipamentos Necessários:** Especificações técnicas dos materiais (ex: classe de penetração do betume 35/50 ou 50/70, emulsão C60B3) ajustados ao tráfego e clima.
    6. **Estimativa de Custos:** Baseada na área fornecida, aplicando preços médios de mercado em Portugal."""

  prompt = f"""Analisa esta patologia num pavimento betuminoso.
    - Área estimada afetada: {area_m2} m²
    - Classe de Tráfego da via: {classe_trafego}
    - Localização / Região geográfica: {localizacao} (Considera as condições climáticas típicas desta zona em Portugal)"""

  response = client.models.generate_content(
      model="gemini-2.5-flash",
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
  area_m2 = st.number_input(
      "Área estimada da patologia (m²):", min_value=1.0, value=10.0, step=1.0
  )

with col2:
  # Seleção do Tipo de Tráfego segundo normativas
  opcoes_trafego = [
      "Tráfego Ligeiro / Caminho Agrícola / Loteamento Habitacional (T6/T5)",
      "Tráfego Médio / Estrada Municipal / Arruamento Urbano Principal (T4/T3)",
      "Tráfego Pesado / Estrada Nacional / Zona Industrial (T2)",
      "Tráfego Muito Pesado / Itinerário Principal (IP/IC) ou Autoestrada (T1/T0)",
  ]
  classe_trafego = st.selectbox(
      "Tipo de Tráfego / Categoria da Via:", opcoes_trafego
  )

  # Localização para contextuar dados climáticos (predefinido para Évora/Alentejo)
  localizacao = st.text_input(
      "Localização do Pavimento (Região / Concelho):",
      value="Évora, Alentejo Central",
  )

if uploaded_file is not None:
  st.image(
      uploaded_file, caption="Fotografia da Patologia", use_container_width=True
  )

  if st.button("Gerar Relatório Técnico Completo (LNEC / IP)"):
    with st.spinner(
        "A analisar a imagem, cruzando dados de tráfego e condições climáticas"
        " locais..."
    ):
      image_bytes = uploaded_file.getvalue()
      mime_type = uploaded_file.type
      try:
        relatorio = analisar_patologia(
            image_bytes, mime_type, area_m2, classe_trafego, localizacao
        )
        st.markdown("---")
        st.markdown("### Relatório Técnico e Orçamental Adaptado")
        st.markdown(relatorio)
      except Exception as e:
        st.error(f"Erro ao processar a imagem: {e}")