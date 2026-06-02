
# Workload Analyzer

Aplicație pentru **caracterizarea volumului de lucru** și **evaluarea performanței unui sistem software**.

Proiectul este potrivit pentru tema:
**Tehnici de caracterizare a volumului de lucru**  
din cadrul materiei **Modelarea și evaluarea performanțelor**.

## Ce face aplicația

Aplicația analizează date despre activitatea unui sistem software, de exemplu log-uri de cereri către un server web sau date generate sintetic.

Funcționalități principale:

- încărcare fișier CSV cu date despre workload;
- generare workload sintetic: constant, cu vârfuri sau periodic;
- validare și preprocesare automată a datelor;
- calcul indicatori generali:
  - număr total de cereri;
  - cereri/minut;
  - vârf maxim;
  - timp mediu de răspuns;
  - mediană;
  - P90, P95, P99;
  - rată de eroare;
  - CPU mediu;
  - memorie medie;
- analiză pe tipuri de cereri;
- analiză temporală;
- detectare anomalii;
- corelații între volum, CPU, memorie și timp de răspuns;
- clasificare automată a workload-ului;
- comparație între două workload-uri;
- export raport HTML, PDF și CSV.

## Cum se rulează

1. Instalează Python 3.10+.

2. Deschide terminalul în folderul proiectului.

3. Instalează dependențele:

```bash
pip install -r requirements.txt
```

4. Rulează aplicația:

```bash
streamlit run app.py
```

5. Se va deschide aplicația în browser.

## Format CSV acceptat

Coloane obligatorii:

```text
timestamp, request_type, response_time_ms, cpu_usage, memory_usage, status_code
```

Coloane opționale:

```text
user_id, request_size_kb, response_size_kb, server_id
```

## Exemplu de date

```csv
timestamp,request_type,response_time_ms,cpu_usage,memory_usage,status_code
2026-06-01 10:00:01,login,120,35,48,200
2026-06-01 10:00:03,search,450,62,55,200
2026-06-01 10:00:04,checkout,900,78,70,500
```

## Relevanța cu tema proiectului

Tema proiectului este „Tehnici de caracterizare a volumului de lucru”.

Aplicația este relevantă deoarece realizează caracterizarea workload-ului prin:

- măsurarea volumului de cereri;
- analiza ratei de sosire;
- analiza distribuției tipurilor de cereri;
- calculul timpilor de răspuns și al percentilelor;
- identificarea perioadelor de vârf;
- corelarea încărcării cu degradarea performanței;
- identificarea anomaliilor;
- clasificarea workload-ului.

Astfel, aplicația nu este doar un dashboard, ci un instrument de analiză a comportamentului unui sistem software sub diferite niveluri de încărcare.
