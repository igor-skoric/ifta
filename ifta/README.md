# IFTA Workspace - Quick Start

Ovaj dokument je kratak "runbook" za lokalni rad: virtual environment, pokretanje aplikacije i Samsara sync.

## 1) Aktivacija virtual environment (Windows)

### CMD
```cmd
cd d:\projects\IFTA\ifta
.venv\Scripts\activate
```

### PowerShell
```powershell
cd d:\projects\IFTA\ifta
.\venv\Scripts\Activate.ps1
```

## 2) Instalacija dependencies (ako je potrebno)

```cmd
pip install -r requirements.txt
```

## 3) Environment varijable (CMD)

Privremeno (samo trenutni CMD prozor):

```cmd
set SAMSARA_API_TOKEN=your_token_here
set SAMSARA_API_BASE_URL=https://api.samsara.com
set SAMSARA_TRIPS_DAYS_BACK=14
set SAMSARA_TRIPS_INCREMENTAL_OVERLAP_MS=7200000
```

- **`SAMSARA_TRIPS_DAYS_BACK`**: samo prvi sync (ili „Trips full window“) — koliko dana unazad da se povuku tripovi odjednom.
- **Inkrementalni sync** (podrazumevani „Sync trips“): čuva se kraj poslednjeg prozora u bazi; sledeći sync traži samo od `(kraj − overlap)` do sada — ne vuče celu istoriju.
- **`SAMSARA_TRIPS_INCREMENTAL_OVERLAP_MS`**: podrazumevano 2h (7200000 ms) da se ne propuste tripovi na granici vremena.

Trajno (važi za nove CMD prozore):

```cmd
setx SAMSARA_API_TOKEN "your_token_here"
setx SAMSARA_API_BASE_URL "https://api.samsara.com"
setx SAMSARA_TRIPS_DAYS_BACK "14"
setx SAMSARA_TRIPS_INCREMENTAL_OVERLAP_MS "7200000"
```

Provera:

```cmd
echo %SAMSARA_API_TOKEN%
```

## 4) Migracije

```cmd
python manage.py migrate
```

## 5) Pokretanje aplikacije

```cmd
python manage.py runserver
```

App URL-ovi:

- Dashboard: `http://127.0.0.1:8000/`
- Leave calendar: `http://127.0.0.1:8000/leave/`
- Leave balances: `http://127.0.0.1:8000/leave/balances/`
- Samsara: `http://127.0.0.1:8000/samsara/`

## 6) Samsara sync & GPS

API token mora imati scope **Read Vehicle Statistics** (za trips, locations feed i GPS stats).

Opciono u `.env`:

```cmd
set SAMSARA_GPS_CACHE_SECONDS=30
```

Na dispatch truck detail (`/dispatch/trucks/<id>/`) prikazuje se **Live GPS** iz Samsara (locations feed, fallback `vehicle stats?types=gps`). Unit broj u dispatch-u = vehicle name u Samsari.

Sync se radi iz UI na `http://127.0.0.1:8000/samsara/`:

- `Sync vehicles`
- `Sync drivers`
- `Sync trips (incremental)` — samo novi tripovi od poslednjeg uspešnog prozora (plus overlap).
- `Trips full window` — ponovo `SAMSARA_TRIPS_DAYS_BACK` dana za sva vozila (sporije; npr. posle dugog prekida).

Napomena:

- Ako je `SAMSARA_API_TOKEN` pogrešan/nedostaje, sync run će biti upisan sa error statusom.
- Ako si radio `setx`, obavezno otvori novi terminal pre pokretanja.

## 7) Statistik modul

Za import i sheet mapiranje pogledaj postojeći dokument:

- `statistic/IMPORT_SHEETS.md`

TV ekrani (kratki linkovi):

- Grid: `/statistics/1/` ili `/1/`
- Ranking: `/statistics/2/` ili `/2/`
- Weather: `/statistics/3/` ili `/3/`

## 8) Deploy na server (bezbednost)

Kopiraj `ifta/.env.example` u `ifta/.env` na serveru (`.env` **ne ide u git**). Minimum u CMD (privremeno):

```cmd
set DJANGO_DEBUG=false
set DJANGO_SECRET_KEY=<nasumican-dugi-string>
set ALLOWED_HOSTS=ifta.rs.itbranch.rs
set CSRF_TRUSTED_ORIGINS=https://ifta.rs.itbranch.rs
set DJANGO_USE_HTTPS=true
set TRUST_X_FORWARDED_FOR=true
```

Generiši tajni ključ:

```cmd
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**TV bez prijave:** dodaj IP TV uređaja u `STATISTICS_TV_ALLOWED_IPS` (npr. `192.168.0.50`) ili postavi `STATISTICS_TV_TOKEN` i otvori `/statistics/1/?tv_token=...`. Ne uključuj `STATISTICS_TV_PUBLIC_READ=true` na javnom internetu.

**Provera pre deploya:**

```cmd
python manage.py check --deploy
```

### Dizajn / CSS ne radi na produkciji (samo HTML)

Uzrok: `DJANGO_DEBUG=false` — Django ne servira statiku kao na `runserver`-u. Treba **build Tailwind** + **collectstatic** (WhiteNoise servira iz `staticfiles/`).

Proveri DEBUG:

```bash
python manage.py shell -c "from django.conf import settings; print('DEBUG=', settings.DEBUG)"
grep DJANGO_DEBUG .env
```

Na serveru (iz foldera sa `manage.py`):

```bash
cd theme && npm ci && npm run build && cd ..
python manage.py collectstatic --noinput
# restart Python app u cPanel-u
```

U browseru (F12 → Network): da li `/static/css/dist/styles.css` vraća **200** ili **404**?

Ako `python manage.py tailwind build` postoji, može i to umesto `npm run build`.

Napomene:

- `/api/statistic/` više nije javan — potreban login, TV IP/token, ili `statistics.view` permisija.
- `DEBUG=false` uključuje secure cookies i HSTS (uz HTTPS).
- `statistic/secrets/service_account.json` ne sme u git (već je u `.gitignore`).

## 9) Linux produkcija (labvit / cPanel)

Repozitorijum je u `/home/labvit/IFTA`, Django projekat u **`/home/labvit/IFTA/ifta`** (tu je `manage.py`).

```bash
source /home/labvit/virtualenv/IFTA/3.11/bin/activate
cd /home/labvit/IFTA/ifta

# 1) .env (obavezno pre prvog pokretanja)
cp .env.example .env
nano .env   # DJANGO_SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, putanja do service_account.json

# 2) Google Sheets credential (nije u git-u)
mkdir -p statistic/secrets
# upload: statistic/secrets/service_account.json

# 3) dependencies, baza, static
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy

# 4) superuser (jednom)
python manage.py createsuperuser
```

**Python app / Passenger (cPanel):**

| Polje | Vrednost |
|--------|----------|
| Application root | `/home/labvit/IFTA` |
| Application startup file | `passenger_wsgi.py` |
| Application entry point | `application` |
| Python version | 3.11 |

U repou je `passenger_wsgi.py` u korenu (pored foldera `ifta/`). **Ne koristi** stari obrazac:

```python
# POGREŠNO — izaziva "populate() isn't reentrant"
wsgi = imp.load_source('wsgi', 'ifta/wsgi.py')
```

Posle deploya: **Restart** Python app u cPanel-u. Ako i dalje vidiš staru grešku, u File Manageru otvori `/home/labvit/IFTA/passenger_wsgi.py` i proveri da je zamenjen novim fajlom iz gita.

**Česte greške posle deploya:**

| Poruka | Rešenje |
|--------|---------|
| `Set DJANGO_SECRET_KEY...` | U `.env`: `DJANGO_DEBUG=false` i pravi `DJANGO_SECRET_KEY` (ne `django-insecure-...`) |
| `Service account file not found` | Postavi `GOOGLE_SERVICE_ACCOUNT_FILE=/home/labvit/IFTA/ifta/statistic/secrets/service_account.json` i upload fajla |
| `python: can't open file 'manage.py'` | `cd /home/labvit/IFTA/ifta` (ne samo `IFTA`) |
| `DisallowedHost` | Dodaj domen u `ALLOWED_HOSTS` u `.env` |
| `403 CSRF` | Dodaj `https://tvoj-domen` u `CSRF_TRUSTED_ORIGINS` |
| TV/statistics prazno | Uloguj se na TV ili dodaj IP u `STATISTICS_TV_ALLOWED_IPS` |

Ako dobiješ grešku, pošalji **ceo traceback** (ne samo `activate && cd`).

### `table "app_employee" already exists` pri `migrate`

**Uzrok:** stari migration fajlovi na serveru (bez `git pull`) ili pogrešno obrisana baza. Django uvek čita migracije iz **koda na disku**, ne iz stare baze.

**1) Proveri da server ima novi kod** (prva linija `0009` mora imati `Database: no-op`):

```bash
head -3 ifta/ifta/migrations/0009_employee_equipmentitem.py
# ili, ako je layout ravniji:
head -3 ifta/migrations/0009_employee_equipmentitem.py
```

Ako vidiš običan `CreateModel` bez `SeparateDatabaseAndState` → uradi `git pull` (deploy najnovijeg commita).

**2) Obriši celu SQLite bazu na pravoj putanji** (i WAL fajlove):

```bash
source /home/labvit/virtualenv/IFTA/3.11/bin/activate
cd /home/labvit/IFTA/ifta   # gde je manage.py

python -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])"

# Obriši TAČNO taj fajl +:
rm -f db.sqlite3 db.sqlite3-wal db.sqlite3-shm
```

**3) Čist migrate** (ako je migrate pukao na pola, ponovo obriši `db.sqlite3*` pa):

```bash
python manage.py migrate
python manage.py createsuperuser
```

Ako je `office.0006` ostao upisan u `django_migrations` a tabele nisu kreirane:

```bash
rm -f db.sqlite3 db.sqlite3-wal db.sqlite3-shm
python manage.py migrate
```

**Ne briši** foldere `*/migrations/` iz koda — to nisu podaci, to je šema aplikacije.
