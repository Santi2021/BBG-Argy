# ARG Terminal 📊

Bloomberg-style financial terminal for Argentine markets.

**Live data from:** data912 (Milton) · BondTerminal · Ecovalores · dolarapi · yfinance

---

## Deploy en Streamlit Cloud (gratis)

### 1. Crear repo en GitHub

1. Andá a [github.com/new](https://github.com/new)
2. Nombre: `arg-terminal` (o el que quieras)
3. **Public** (necesario para el free tier de Streamlit Cloud)
4. Click **Create repository**

### 2. Subir los archivos

En tu PC, abrí CMD en la carpeta del proyecto y ejecutá:

```bash
git init
git add .
git commit -m "Initial: ARG Terminal"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/arg-terminal.git
git push -u origin main
```

> Reemplazá `TU_USUARIO` con tu usuario de GitHub.

### 3. Deploy en Streamlit Cloud

1. Entrá a [share.streamlit.io](https://share.streamlit.io)
2. Sign in con tu cuenta de GitHub
3. Click **New app**
4. Seleccioná el repo `arg-terminal`, branch `main`, archivo `app.py`
5. Click **Deploy** → en ~2 minutos tenés tu URL

Tu URL va a ser algo como:
```
https://TU_USUARIO-arg-terminal-app-XXXXX.streamlit.app
```

---

## Correr local

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

---

## Estructura

```
arg-terminal/
├── app.py              # Entry point + CSS Bloomberg
├── data.py             # Todas las fuentes de datos (cacheadas 60s)
├── requirements.txt
├── tabs/
│   ├── overview.py     # KPIs globales + FX + commodities
│   ├── argentina.py    # Acciones, CEDEARs, tipos de cambio, ADRs
│   ├── bonos.py        # BondTerminal: soberanos, corp, prov + riesgo país
│   ├── futuros.py      # Ecovalores: futuros dólar + curva TNA + curva TIR
│   ├── mundo.py        # Índices globales + sectores S&P + commodities
│   └── watchlist.py    # Watchlist personalizable con sparklines
```

---

## Fuentes de datos

| Fuente | Datos | Método |
|--------|-------|--------|
| [data912.com](https://data912.com) | Acciones, CEDEARs, MEP/CCL, Bonos ARS | API pública |
| [bondterminal.com](https://bondterminal.com) | Bonos USD soberanos/corp/prov, Riesgo País | API pública |
| [dolarapi.com](https://dolarapi.com) | Todos los tipos de cambio | API pública |
| [Ecovalores](https://bonos.ecovalores.com.ar/eco/) | Futuros dólar, Curva TNA, Curva TIR | Scraping HTML |
| [yfinance](https://github.com/ranaroussi/yfinance) | Índices globales, FX, Commodities, Sectores | Librería |

Todos los datos se cachean por **60 segundos**.
