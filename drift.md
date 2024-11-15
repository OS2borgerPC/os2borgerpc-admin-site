# Installation og drift

OS2BorgerPC admin-site bygges som et docker image. Der er opsat en [bygge-pipeline i github](https://github.com/OS2borgerPC/os2borgerpc-admin-site/actions/workflows/docker-image.yml), som bygger docker image'et.
Det publiceres til [GitHub Packages](https://github.com/orgs/OS2borgerPC/packages?repo_name=os2borgerpc-admin-site), hvor image-tags og URL kan ses.

Konfigurationen af admin site gøres via miljøvariabler, som er beskrevet nedenunder.\
Udover konfigurationsparametre beskrives også andre krav til drift.

`compose.yaml` bruges til udvikling, men kan også bruges som et eksempel på en fuld konfiguration. Compose er dog ikke opdateret til at bruge de nye cron job endpoints beskrevet nedenunder, men laver istedet et seperat image, som kalder dem. Dette er fint til udvikling, men anbefales ikke til drift.

## <a name="bootstrapping"></a> Bootstrapping
For at kunne begynde at bruge admin-site samt tilgå Djangos administartionsside (`<base URL>/admin`) skal man have en admin bruger. Der er som default ikke nogen admin bruger, så for at kunne oprette nye brugere/første site, skal admin brugeren oprettes.\
For at gøre dette nemt, oprettes en admin bruger ved første start, med følgende miljøvariabler:
- ADMIN_USERNAME
- ADMIN_PASSWORD
- ADMIN_EMAIL

Admin email tilhører Django's indbyggede brugerhåndtering.

Admin-brugeren kan også logge ind som en aldmindelig bruger, som kan administrere sites/klienter.

## Database
Miljøvariabler til konfiguration af forbindelse til databasen som bruges af Django:
- DB_HOST
- DB_PORT
- DB_USER
- DB_PASSWORD
- DB_NAME

Se `compose.yaml` for eksempel på opsætning af disse.

## Scripts

Scripts gemmes i Django's media-mappe `/media`, og der skal derfor mountes en (persistent) volume ind på denne sti, for at scripts persisteres mellem genstart. Hvis dette ikke gøres, vil fejlbeskeden `<Kan ikke vise koden - upload venligst igen.>` ses, når man klikker ind på et givent scripts `Kode`-tab.

### Globale
Globale scripts hentes fra [OS2's core-script repository](https://github.com/OS2borgerPC/os2borgerpc-core-scripts) under opstart. Versionen der hentes konfigures via to miljøvariabler:

```
CORE_SCRIPT_COMMIT_HASH
CORE_SCRIPT_VERSION_TAG
```

`CORE_SCRIPT_VERSION_TAG` er den version af globale scripts man gerne vil bruge. Versionen vises i brugergrænsefladen i slutningen af navnet på hvert script. De mulige versioner kan ses det i linkede core-script repository.\
`CORE_SCRIPT_COMMIT_HASH` er det commit hash som hører til `CORE_SCRIPT_VERSION_TAG`. Når man har valgt sin version, skal man således finde det tilhørende commit hash, og angive det her. Commit-hash kan ses på github under commit-historik (det skal være det fulde hash, og ikke den forkortede udgave). En anden nem måde at få commit-hash på, er ved kun at angive version og udelade commit-hash, så vil admin-site under opstart printe en fejl til loggen, hvor commit-hash også står i.

Brugen af commit-hash er en sikkerhedsforanstaltning der gør, at der ikke kan laves om i scripts, når først de har fået et versions-tag (f.eks. v1.2.0). Hvis det ændrer sig, vil admin site opdage det, og nægte at starte, før de to (commit-hash og version) stemmer overens.

Et versions-tag bør aldrig ændre commit-hash. Det vil kun ske, hvis der laves om i et eksisterende release af scripts, hvor modificerede scripts udgives med et eksisterende versionsnummer, og derved overskriver det tidligere release.\
Dette scenarie opdages ikke, hvis commit-hash ikke også angives, så admin-site kan melde fejl.

#### Installation af ny version af globale scripts

Hvis man angiver en anden version af globale scripts og genstarter admin-site, installeres denne version af globale scripts ved siden af de eksisterende (scripts er navngivet med versionsnummer, så man kan stadig skelne mellem versionerne). De gamle scripts beholdes, for at der ikke fjernes scripts som bruges af en gruppe/computer.

Dette betyder at scripts vil akkumulere over tid, hver gang man angiver en nyere version af scripts.\
Hvis man vil rydde op i (ældre releases af) scripts, skal man gøre det manuelt. Dette vil typisk gøres via SQL, ved at tilgå den kørende database-container. Det anbefales også at fjerne evt. scripts der ikke bruges, fra mappen `/media/script_uploads` i den kørende container. Denne mappe indeholder selve scriptet, mens databasen indeholder metadata om scriptet.\
Oprydning kan også gøres gennem [Django's administrations-side](https://docs.djangoproject.com/en/4.2/ref/contrib/admin/), som tilgås via URL-stien `/admin` fra en browser. Dette vil dog være en langsommelig, manuel proces, hvis der skal fjernes flere scripts.

Fjerner man alle scripts og genstarter, får man ryddet helt op, så kun den version man har angivet vil være installeret. Mappen `/media/script_uploads` (i docker-containeren) skal dog stadig ryddes op i manuelt.

## Cron jobs
Der findes to cron jobs, som benyttes til notifikationer, samt til løbende at rydde op i databasen.

De ligger under path `/jobs/` på port `8080`, og kan køres med f.eks `curl`:
```bash
curl http://admin-site-url:8080/jobs/check_notifications -f
curl http://admin-site-url:8080/jobs/clean_up_database -f
```
Foreslag til cron schedule (crontab syntax):

`check_notifications` - `*/10 * * * *`\
`clean_up_database` - `0 19 * * 6`

### Baggrundsviden
Python scripts afvikles for at udføre cron jobs, og de ligger i admin-site image.
De er implementeret som Django commands, og kaldes derfor med `manage.py <cmd-navn>`.

Hvis man opretter forbindelse til en kørende admin-site container, kan jobbene udføres herfra med følgende kommandoer:
```bash
/code/admin_site/manage.py check_notifications
/code/admin_site/manage.py clean_up_database
```
Det er også denne måde jobs køres på, når de køres via HTTP kald som beskrevet ovenover.

## Diverse
- HTTPS_GUARANTEED true | false - default: false\
Indsætter middleware i Django der slår sikkerhed fra, så alle requests stoles på (HTTP betragtes på samme måde som HTTPS).
Dette er f.eks. brugbart hvis app'en driftes bag en proxy der terminerer TLS (som f.eks nginx), da Django ellers vil se login-requests som et forsøg på CSRF.\
Det er valgfrit at sætte denne parameter. Hvis den ikke sættes, vil den automatisk have værdien false.