# Installation og drift

OS2BorgerPC admin-site bygges som et docker image.\
Konfigurationer sættes via miljøvariabler, og er beskrevet nedenunder.

## Cron jobs
Cron jobs benyttes til notifikationer samt til løbende at rydde op i databasen.

Der findes to jobs son ligger under path `/jobs/` på port `8080`. De kan køres med `curl`:
```bash
curl http://admin-site-url:8080/jobs/check_notifications -f
curl http://admin-site-url:8080/jobs/clean_up_database -f
```
Foreslag til cron schedule:

`check_notifications` - `*/10 * * * *`\
`clean_up_database` - `0 19 * * 6`

### Baggrundsviden
Python scripts afvikles for at udføre cron jobs, og ligger i admin-site image.
Disse er implementeret som Django commands, og kaldes derfor med `manage.py <cmd-navn>`.

Hvis man opretter forbindelse til en kørende admin-site container, kan jobbene udføres herfra med følgende kommandoer:
```bash
/code/admin_site/manage.py check_notifications
/code/admin_site/manage.py clean_up_database
```

Det er også denne måde jobs køres på, når de køres via HTTP kald som beskrevet ovenover.

## Konfiguration

### Bootstrapping
For at kunne tilgå Djangos administartionsside (\<base URL\>/admin) skal man have en admin bruger. Der er som default ikke nogen admin bruger, så for at kunne oprette nye brugere/første site, skal admin brugeren oprettes.
For at gøre dette nemt, oprettes en admin bruger ved første start med følgende:
- ADMIN_USERNAME
- ADMIN_PASSWORD
- ADMIN_EMAIL

Admin email tilhører Django's indbyggede brugerhåndtering. Brugeren vil stadig blive oprettet, hvis den efterlades tom.

Admin-brugeren kan også logge ind som en aldmindelig bruger, som kan administrere sites/klienter.

### Database
Konfiguration af forbindelse til databasen som bruges af Django.
- DB_HOST
- DB_PORT
- DB_USER
- DB_PASSWORD
- DB_NAME

### Diverse
- HTTPS_GUARANTEED true|false\
Indsætter middleware i Django der slår sikkerhed fra, så alle requests stoles på (HTTP betragtes på samme måde som HTTPS).
Dette er f.eks. brugbart hvis app'en driftes bag en proxy der terminerer TLS (som f.eks nginx), da Django ellers vil se login-requests som et forsøg på CSRF.



## Opdatering af klient
TODO beskriv hvordan URL skal sættes i PC config for at opdatere klient - f.eks beskriv hvilken URL man skal bruge for beholde opførslen med at den altid installerer den nyeste taggede version (ikke seneste commit).

## [Konfiguration af *customer admins*](admin_site/static/docs/configuring_customer_admins.pdf)