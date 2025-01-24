# Installation og Drift

## Introduktion
**OS2BorgerPC admin-site** er designet som et Docker-image. Bygning og publicering håndteres af en [GitHub-pipeline](https://github.com/OS2borgerPC/os2borgerpc-admin-site/actions/workflows/docker-image.yml), som uploader Docker-image'et til [GitHub Packages](https://github.com/orgs/OS2borgerPC/packages?repo_name=os2borgerpc-admin-site). Her kan du finde image-tags og URLs.

Konfiguration sker via miljøvariabler (beskrevet nedenfor) og omfatter desuden specifikationer for driftskrav. En `compose.yaml`-fil leveres som reference til udvikling og konfiguration.

**Bemærk:** `compose.yaml` er ikke opdateret til at understøtte nye cron job-endpoints. Til produktion anbefales en alternativ opsætning.

---

## Oversigt over Miljøvariabler

| Variabel                     | Forklaring                                                                 | Standardværdi   | Påkrævet |
|------------------------------|----------------------------------------------------------------------------|-----------------|----------|
| `ADMIN_USERNAME`             | Brugernavn for admin-bruger                                               | Ingen           | Ja       |
| `ADMIN_PASSWORD`             | Adgangskode for admin-bruger                                              | Ingen           | Ja       |
| `ADMIN_EMAIL`                | Email for admin-bruger                                                    | Ingen           | Ja       |
| `DB_HOST`                    | Databasevært                                                              | Ingen           | Ja       |
| `DB_PORT`                    | Databaseport                                                              | Ingen           | Ja       |
| `DB_USER`                    | Brugernavn til databasen                                                  | Ingen           | Ja       |
| `DB_PASSWORD`                | Adgangskode til databasen                                                 | Ingen           | Ja       |
| `DB_NAME`                    | Navn på databasen                                                         | Ingen           | Ja       |
| `CORE_SCRIPT_VERSION_TAG`    | Version af de globale scripts                                             | Ingen           | Ja       |
| `CORE_SCRIPT_COMMIT_HASH`    | Matchende commit-hash for scripts                                         | Ingen           | Nej      |
| `HTTPS_GUARANTEED`           | Aktiverer behandling af HTTP som HTTPS bag proxy                         | false           | Nej      |
| `PC_IMAGE_RELEASES_URL`      | URL til download af BorgerPC ISO images                                   | Ingen           | Nej      |
| `KIOSK_IMAGE_RELEASES_URL`   | URL til download af Kiosk ISO images                                      | Ingen           | Nej      |

---

## Drift Anbefalinger

For at understøtte leverandører og kommuner i at sætte OS2BorgerPC admin-site i drift samt håndtere opgraderinger anbefales følgende fremgangsmåde:

### Drift Opsætning
1. **Undgå brug af `docker-compose` i produktion:**
   - `docker-compose` er velegnet til udvikling, men anbefales ikke til produktion.
   - Brug en orkestreringsløsning som Kubernetes eller Docker Swarm til at håndtere containere.

2. **Ønskes brug af docker-compose alligevel eller sammen med Docker Swarm:**
   - Lav ny docker-compose fil med udgangspunkt i `compose.yaml`
   - Fjern unødvendige services som `frontend` og tilpas `cron-service` som beskrevet nedenfor.
   - Konfigurer admin-site til at pege på et specifikt Docker-image-tag, f.eks.:
     ```yaml
     image: ghcr.io/os2borgerpc/os2borgerpc-admin-site:<specific-tag>
     ```
   - Indstil miljøvariabler i henhold til dokumentationen.

3. **Volumenhåndtering:**
   - Sørg for at mount persistente volumes til `/media` for at sikre, at scripts og andre uploads bevares mellem genstarter.
   - Eksempel:
     ```yaml
     volumes:
       - admin-media:/media
     ```

4. **Sikkerhed:**
   - Angiv en stærk `SECRET_KEY` i miljøvariablerne.
   - Begræns `ALLOWED_HOSTS` til de domæner, der skal have adgang til admin-site.

### Opgradering af Admin-Site
1. **Forberedelse:**
   - Gennemgå release-notes for den nye version.
   - Test opgraderingen i et udviklings- eller staging-miljø.

2. **Opdatering:**
   - Opdater Docker-image-tagget til den ønskede version i din orkestreringsopsætning.
   - Genstart admin-site-containere for at anvende ændringerne.

3. **Validering:**
   - Bekræft, at opgraderingen er succesfuld ved at teste kernefunktionalitet.
   - Tjek logfiler for fejl eller advarsler.

### Fejlfinding
- Hvis der opstår problemer under opgradering, kan du rulle tilbage til det tidligere Docker-image-tag.
- Kontroller logfiler i admin-site-containere for detaljerede fejlmeddelelser.

---

## Bootstrapping
For at initialisere admin-site og få adgang til Djangos administrationsside (`<base URL>/admin`), skal en admin-bruger oprettes med følgende miljøvariabler:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_EMAIL`

**Bemærk:** `ADMIN_EMAIL` anvendes af Djangos indbyggede brugerhåndtering. Den oprettede admin-bruger kan også administrere sites og klienter.

---

## Database
Konfiguration af databaseforbindelsen sker via følgende miljøvariabler:

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

Se `compose.yaml` for eksempler.

---

## Scripts
Scripts gemmes i Djangos mediamappe (`/media`). For at sikre persistens mellem genstarter skal en persistent volume mountes på denne sti.

### Globale Scripts
Globale scripts downloades fra [OS2's core-script repository](https://github.com/OS2borgerPC/os2borgerpc-core-scripts) under opstart. Konfiguration sker med:

- `CORE_SCRIPT_VERSION_TAG`: Version af de globale scripts (fx `v1.2.0`).
- `CORE_SCRIPT_COMMIT_HASH`: Matchende commit-hash for versionen (valgfrit, men anbefalet).

#### Sådan Finder du Commit-Hash
1. Gå til [commit-historik](https://github.com/OS2borgerPC/os2borgerpc-core-scripts/commits/main).
2. Find det commit, der matcher versionstagget.
3. Kopiér commit-hash.

#### Opdatering af Globale Scripts
1. Opdater `CORE_SCRIPT_VERSION_TAG` og `CORE_SCRIPT_COMMIT_HASH`.
2. Genstart containeren.

**Bemærk:** Eksisterende scripts fjernes ikke automatisk og skal ryddes manuelt via SQL eller `/admin`.

---

## Cron Jobs
Admin-site understøtter to cron jobs:

1. **`check_notifications`**: Sender notifikationer. *(Forslag: `*/10 * * * *`)*
2. **`clean_up_database`**: Rydder op i databasen. *(Forslag: `0 19 * * 6`)*

### Kørsel af Cron Jobs
Via HTTP:
```bash
curl http://admin-site-url:8080/jobs/check_notifications -f
curl http://admin-site-url:8080/jobs/clean_up_database -f
```

Manuelt fra container:
```bash
/code/admin_site/manage.py check_notifications
/code/admin_site/manage.py clean_up_database
```

---

## Diverse Konfigurationsparametre

- **`HTTPS_GUARANTEED`**: 
  - true | false (default: false).
  - Aktiverer middleware for behandling af HTTP som HTTPS bag en proxy.

- **`PC_IMAGE_RELEASES_URL`** og **`KIOSK_IMAGE_RELEASES_URL`**:
  - URLs til download af BorgerPC ISO images.

---
