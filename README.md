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

```bash
git init
git add .
git commit -m "ARG Terminal v2"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/arg-terminal.git
git push -u origin main
```

### 3. Deploy en Streamlit Cloud

1. Entrá a [share.streamlit.io](https://share.streamlit.io)
2. Sign in con GitHub
3. Click **New app** → repo `arg-terminal`, branch `main`, archivo `app.py`
4. Click **Deploy**

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
│   ├── overview.py     # KPIs + índices + commodities + FX
│   ├── argentina.py    # FX, acciones, CEDEARs, ADRs, MEP/CCL
│   ├── bonos.py        # BondTerminal: soberanos, corp, prov + riesgo país
│   ├── futuros.py      # Ecovalores: futuros dólar + curva TNA + curva TIR
│   ├── mundo.py        # Índices globales + sectores S&P + commodities
│   └── watchlist.py    # Watchlist personalizable con sparklines
```
