# Statistika – uvoz sheetova (reminder)

Kratki podsetnik za **nedeljni upsert** (LIVEBOARD + DISPATCHER) i **istorijski uvoz** u odabranu ISO nedelju.

## Šta treba znati

- Podaci u bazi su po **ISO godini** i **broju nedelje** (1–53), u istoj vremenskoj zoni kao i automatski sync (`STATISTIC_WEEK_TIMEZONE` u settings, podrazumevano Chicago).
- **Živi sync** (`sync_sheets_once` / scheduler) uvijek piše u **tekuću** nedelju.
- Za **stari sheet** moraš imati: Google **Sheet ID** (iz URL-a), **range** i **tab** kao za živi sheet, te odluku **koja ISO nedelja** tom snimku odgovara.

Sheet ID iz URL-a:

`https://docs.google.com/spreadsheets/d/`**`OVDJE_ID`**`/edit`

---

## Jednokratni sync (kao na ekranu / TV)

Iz korijena projekta (`manage.py`):

```bash
python manage.py sync_sheets_once
```

**Šta radi:** pozove `sync_dispatcher_sheet()` pa `sync_weekly_sheet()` – oba koriste `SheetConfig` (`DISPATCHER_SHEET`, `LIVEBOARD`) i **tekuću** ISO nedelju.

---

## Istorijski uvoz u odabranu nedelju

Komanda: `import_statistic_sheet`

### Nedeljni blok (LIVEBOARD)

Koristi `sheet_id`, `sheet_range`, `tab` iz admina za kod `LIVEBOARD`:

```bash
python manage.py import_statistic_sheet weekly --year 2025 --iso-week 12
```

### Dispatcher tabela (DISPATCHER_SHEET)

```bash
python manage.py import_statistic_sheet dispatcher --year 2025 --iso-week 12
```

### Prebijanje sheeta (stari fajl, bez mijenjanja SheetConfig u adminu)

```bash
python manage.py import_statistic_sheet weekly --year 2026 --iso-week 12 --sheet-id 1QbIgXq0CB9uCkxoWMkCNmWiEsh79gG9URukrKHismlA --sheet-range !P1:T9 --tab "MAIN"
```

Ako je tab prazan kao prefiks:

```bash
python manage.py import_statistic_sheet weekly --year 2025 --iso-week 12 --sheet-id STARI_ID --sheet-range "!A1:J50" --tab ""
```

### Opcije

| Opcija | Opis |
|--------|------|
| `--year` | ISO godina nedelje (obavezno za ovu komandu). |
| `--iso-week` | Broj ISO nedelje 1–53 (obavezno). |
| `--sheet-id` | Drugi Google Sheet ID (opciono). |
| `--sheet-range` | Drugi range (opciono). |
| `--tab` | Drugi naziv taba ispred range-a (opciono). |
| `--code` | Drugi `SheetConfig.code` ako nije `LIVEBOARD` / `DISPATCHER_SHEET`. |
| `--touch-config` | Ako navedeš: ažurira se `SheetConfig.last_synced_at`. **Bez** toga: istorijski uvoz ne dira taj timestamp (preporučeno za arhivu). |

---

## Django migracije (statistic app)

Ako mijenjaš modele:

```bash
python manage.py makemigrations statistic
python manage.py migrate statistic
```

---

## Napomena

Ako starog sheet-a nema u Google Drive-u, nema šta API da pročita – onda ostaje ručni unos u adminu ili import iz drugog formata (to nije pokriveno ovim komandama).
