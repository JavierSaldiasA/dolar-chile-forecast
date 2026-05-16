# 🇨🇱💵 Estimador del Precio del Dólar en Chile

Proyecto de Machine Learning para predecir el tipo de cambio USD/CLP utilizando datos macroeconómicos y técnicos.

## 📊 Objetivo

Construir un modelo predictivo que estime el precio del dólar en Chile a corto plazo, utilizando técnicas de análisis de series temporales y machine learning.

## 🗂️ Estructura del Proyecto
```
dolar-chile-forecast/
├── data/              # Datos crudos y procesados
├── notebooks/         # Análisis exploratorios en Jupyter
├── src/               # Código fuente modular
├── models/            # Modelos entrenados guardados
├── reports/           # Reportes y visualizaciones
└── tests/             # Pruebas unitarias
```
## 🚀 Instalación
```
# 1. Clonar el repositorio
git clone https://github.com/JavierSaldiasA/dolar-chile-forecast.git

# 2. Entrar a la carpeta
cd dolar-chile-forecast

# 3. Crear entorno virtual
python -m venv venv

# 4. Activar entorno virtual
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 5. Instalar dependencias
pip install -r requirements.txt
```

## 📈 Roadmap
```
✅ Fase 1: Recolección de datos
[ ] Fase 2: Análisis Exploratorio (EDA)
[ ] Fase 3: Feature Engineering
[ ] Fase 4: Modelado y Evaluación
[ ] Fase 5: Dashboard y API
```
## 🏛️ BCCH Data Collector Pro

Aplicacion interactiva con interfaz grafica (Streamlit) para buscar, seleccionar y descargar series de datos del **Banco Central de Chile** de forma profesional.

### ✨ Caracteristicas

| Funcionalidad | Descripcion |
|---------------|-------------|
| 🔍 **Buscador de series** | Busca por palabra clave con filtros por frecuencia (diaria, mensual, trimestral, anual) |
| ✅ **Seleccion multiple** | Marca series con checkboxes persistentes y agregalas a un carrito |
| 📝 **IDs directos** | Ingresa Series ID manualmente sin necesidad de buscar |
| 📁 **Carga CSV** | Sube un archivo CSV con multiples Series ID |
| 🧠 **Autodeteccion de frecuencia** | Detecta automaticamente la frecuencia desde la ultima letra del ID (D, M, Q, A) |
| 📊 **Agregacion inteligente** | Cambia la frecuencia de salida: diaria → mensual, mensual → anual, etc. |
| 🩹 **Imputacion de NaN** | Rellena valores faltantes con forward fill, backward fill, interpolacion, etc. |
| 📈 **Variacion** | Calcula variacion en periodos (mensual, anual, etc.) |
| 📁 **Formato de salida** | CSV o Excel (.xlsx), archivo unico o separado por serie |

### 🚀 Como usar la app

```
# Ejecutar la app
streamlit run app_data_collector.py
```

## 👤 Autor
Javier Saldías A.