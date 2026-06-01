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

Kopiraj `.env.example` u `.env` na serveru i podesi vrednosti. Minimum:

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

Napomene:

- `/api/statistic/` više nije javan — potreban login, TV IP/token, ili `statistics.view` permisija.
- `DEBUG=false` uključuje secure cookies i HSTS (uz HTTPS).
- `statistic/secrets/service_account.json` ne sme u git (već je u `.gitignore`).
