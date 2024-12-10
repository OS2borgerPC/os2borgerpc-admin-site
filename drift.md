# Installation og Drift

**OS2BorgerPC admin-site** bygges som et Docker-image. En [bygge-pipeline på GitHub](https://github.com/OS2borgerPC/os2borgerpc-admin-site/actions/workflows/docker-image.yml) bygger og publicerer Docker-image'et til [GitHub Packages](https://github.com/orgs/OS2borgerPC/packages?repo_name=os2borgerpc-admin-site). Her kan du finde image-tags og URL.

Konfigurationen af admin-site sker via miljøvariabler, som er beskrevet nedenfor. Derudover beskrives også øvrige driftskrav.

En `compose.yaml`-fil er inkluderet til udviklingsbrug og kan bruges som reference for fuld konfiguration. Bemærk, at denne ikke er opdateret til de nye cron job-endpoints, men bruger i stedet et separat image til at udføre dem. Dette fungerer til udvikling, men anbefales ikke til produktion.

---

## Bootstrapping

For at komme i gang med admin-site og få adgang til Djangos administrationsside (`<base URL>/admin`), skal der oprettes en admin-bruger. Da der som standard ikke er nogen admin-bruger, skal denne oprettes ved første opstart med følgende miljøvariabler:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_EMAIL`

*Bemærk:* `ADMIN_EMAIL` er en del af Djangos indbyggede brugerhåndtering. 

Den oprettede admin-bruger kan også logge ind som almindelig bruger og administrere sites/klienter.

---

## Database

Følgende miljøvariabler bruges til at konfigurere databaseforbindelsen:

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

Se `compose.yaml` for eksempler på opsætning.

---

## Scripts

Scripts gemmes i Djangos mediamappe (`/media`). For at sikre persistens mellem genstarter skal en *persistent volume* mountes på denne sti. Hvis dette ikke gøres, vil fejlbeskeden `<Kan ikke vise koden - upload venligst igen.>` (bl.a.) opstå, når man forsøger at åbne et scripts `Kode`-tab.

### Globale Scripts

Globale scripts hentes automatisk fra [OS2's core-script repository](https://github.com/OS2borgerPC/os2borgerpc-core-scripts) under opstart. Følgende miljøvariabler bruges til at konfigurere versionen:

- **`CORE_SCRIPT_VERSION_TAG`**  
  Angiver den ønskede version af de globale scripts, som vises i brugergrænsefladen. Tilgængelige versioner kan ses i det linkede repository. Eksempel: `v1.2.0`.

- **`CORE_SCRIPT_COMMIT_HASH`**  
  Sikrer, at versionstagget matcher det tilsvarende commit. Dette er en sikkerhedsforanstaltning, der forhindrer utilsigtede ændringer i scripts med samme versionstag.  

#### Sådan Finder du Commit-Hash
Når du har valgt en version (fx `v1.2.0`), skal du finde det tilsvarende commit-hash:  
1. Gå til [repositoryets commit-historik](https://github.com/OS2borgerPC/os2borgerpc-core-scripts/commits/main).  
2. Find det commit, der matcher versionstagget. Dette angives typisk i commit-beskederne eller release-noterne.  
3. Kopiér commit-hash i fuld længde (fx `3a5c9d8f4e6e7fabc1234567890abcdef1234567`).  

Alternativt kan du undlade at angive `CORE_SCRIPT_COMMIT_HASH`. Ved opstart vil admin-site logge en fejl med det forventede commit-hash, som du derefter kan kopiere.

#### Installation af Ny Version af Globale Scripts

For at installere en ny version af globale scripts:  
1. **Opdater miljøvariablerne**:  
   - Sæt `CORE_SCRIPT_VERSION_TAG` til den ønskede version (fx `v1.3.0`).  
   - Angiv det tilsvarende `CORE_SCRIPT_COMMIT_HASH`.  
2. **Genstart admin-site**:  
   Genstart containeren for at aktivere ændringerne. Dette downloader og installerer den nye version af scripts.

**Bemærk:**  
- Eksisterende scripts fjernes ikke automatisk og forbliver tilgængelige. Dette sikrer, at ældre scripts stadig kan bruges af eksisterende grupper eller computere.  
- Hvis du ønsker at rydde op i gamle scripts, skal dette gøres manuelt (se afsnittet [Rydning af Scripts](#cleanup-scripts)).  

Når du har installeret en ny version, vil scripts være navngivet med deres versionsnummer. Dette gør det muligt at skelne mellem forskellige versioner og sikre kompatibilitet.  

#### <a name="cleanup-scripts"></a>  Rydning af Scripts

For at rydde op:
1. Slet scripts via SQL eller Djangos administrationsside (`/admin`).
2. Fjern filer fra `/media/script_uploads`.

---

## Cron Jobs

To cron jobs understøttes:

- **`check_notifications`**: Sender notifikationer. *(Forslag til schedule: `*/10 * * * *`)*
- **`clean_up_database`**: Rydder op i databasen. *(Forslag til schedule: `0 19 * * 6`)*

**Sådan køres jobs via HTTP:**
```bash
curl http://admin-site-url:8080/jobs/check_notifications -f
curl http://admin-site-url:8080/jobs/clean_up_database -f
```

**Baggrundsviden:** Cron jobs er implementeret som Django-commands og kaldes via `manage.py`. De kan også udføres manuelt fra en kørende container:
```bash
/code/admin_site/manage.py check_notifications
/code/admin_site/manage.py clean_up_database
```

## Diverse
- `HTTPS_GUARANTEED`: true | false (default: false)
Hvis `true`, aktiveres middleware i Django, der slår sikkerhed fra og behandler HTTP som HTTPS. Brug denne parameter, hvis app'en kører bag en proxy, der terminerer TLS (f.eks. Nginx), for at undgå CSRF-fejl.
Hvis parameteren ikke angives, er default-værdien `false`.
