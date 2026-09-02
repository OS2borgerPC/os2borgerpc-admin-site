# Kørsel af tests

## Kort version

```bash
docker compose up -d os2borgerpc-admin
docker exec bpc_admin_site_django python manage.py test system account
```

## Hvad der faktisk kræves

Testene starter **ikke** webserveren (gunicorn på :9999/:8080) og bruger den
ikke. Django's test runner rejser i stedet selv en midlertidig testdatabase
(`test_bpc`), kører alle migrationer i den, kører testene og sletter den til
sidst.

Der er derfor to krav:

1. **En database skal køre.** `settings.py` er hardkodet til PostgreSQL - der er
   ingen SQLite-fallback. I dev-opsætningen er det containeren
   `bpc_admin_site_db`. DB-brugeren skal kunne oprette en database (test runner
   laver `test_<DB_NAME>`).
2. **Et Django-miljø at køre `manage.py test` i** - med afhængighederne
   installeret og adgang til databasen. Nemmest er web-containeren
   (`bpc_admin_site_django`): den *kører* ganske vist, men testene bruger kun
   dens Python-miljø, ikke dens gunicorn.

`docker exec` kræver, at containeren kører, så start den om nødvendigt først
med `docker compose up -d os2borgerpc-admin` (den trækker `db` med op).

## Nyttige varianter

```bash
# Kun sikkerheds-regressionstestene, udførligt:
docker exec bpc_admin_site_django python manage.py test system.tests_security --verbosity=2

# Én testklasse eller -metode:
docker exec bpc_admin_site_django python manage.py test \
  system.tests_security.APIKeyDeleteScopingTests

# Hele system- + account-suiten:
docker exec bpc_admin_site_django python manage.py test system account
```

## Uden container

Kører du Django lokalt, så fra `admin_site/`-mappen med `DB_*`-miljøvariabler
sat mod en PostgreSQL, du har adgang til:

```bash
cd admin_site && python manage.py test system.tests_security
```

## Relaterede tjek

```bash
# Konfigurations-/import-tjek (fanger fx en fjernet import):
docker exec bpc_admin_site_django python manage.py check

# Manglende migrationer (fejler i CI hvis en model er ændret uden migration):
docker exec bpc_admin_site_django python manage.py makemigrations --check --dry-run
```
