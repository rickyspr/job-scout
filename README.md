# job-scout

Bevakar karriärsidor och jobbflöden efter nya **tech-sommarjobb och summer internships i
Stockholm, Linköping/Norrköping, Södertälje eller på distans**, och skickar en Telegram-notis
inom några minuter efter att annonsen publicerats.

Systemet läser direkt från företagens rekryteringssystem (Teamtailor, Workday, Lever,
Greenhouse, Ashby, SmartRecruiters, Eightfold, Jobylon, SuccessFactors, Deel) och från
Arbetsförmedlingens JobStream och The Hub. Annonserna fångas därför upp innan de hamnar på
Indeed eller LinkedIn.

Som komplement läses också [EarlyCareers](https://earlycareers.fabifont.dev/), databasen bakom
[european-tech-internships-2026](https://github.com/LorenzoLaCorte/european-tech-internships-2026).
Den fylls på med LinkedIn-annonser en gång i veckan, så den ligger dagar efter de andra källorna, men
den hittar företag som inte finns i `sources.yaml`.

## Så fungerar det

```
sources.yaml ──► scout/sources/*  ──► filter.py ──► nytt? ──► Telegram
(företag + ATS)   (en modul per ATS)   (filters.yaml)  (state/)
```

- **Pollning:** varannan minut. Några tunga källor pollas mer sällan (`interval` i `sources.yaml`).
- **Första gången en källa lyckas** skickas en sammanfattning av alla matchande jobb som redan är
  öppna. Därefter kommer en notis per nytt jobb.
- **Samma annons från flera källor** (t.ex. JobStream och Ericssons egen sida) ger bara en notis.
- **Om en källa misslyckas 15 gånger i rad** (ca 30 min) får du en varning, och ett nytt meddelande
  när den fungerar igen.
- **Sedda jobb** sparas i `state/` och committas till branchen `state`, så att historiken på `main`
  hålls ren.

## Komma igång

### 1. Telegram-bot (ca 5 min)

1. Installera Telegram på mobilen och skapa ett konto.
2. Sök upp **@BotFather**, skicka `/newbot` och följ instruktionerna. Du får en **token** som ser ut
   som `123456:ABC-...`.
3. Kör lokalt:
   ```sh
   pip install -r requirements.txt
   python -m scout telegram-setup
   ```
   Klistra in token. Skicka sedan `/start` till din nya bot i Telegram. Skriptet skriver ut ditt
   **chat id** och skickar ett testmeddelande.
4. Tips: öppna chatten med boten och slå på notisljud, så att du inte missar något.

### 2. GitHub Actions

1. Gör repot **publikt**. Publika repon har obegränsat antal Actions-minuter.
2. Gå till *Settings → Secrets and variables → Actions* och lägg till `TELEGRAM_BOT_TOKEN` och
   `TELEGRAM_CHAT_ID`.
3. Gå till *Actions → scout → Run workflow* för att starta första körningen direkt. Därefter
   håller cron igång den.

Varje körning pollar i en loop i ca 5,5 timmar. Cron var 30:e minut fungerar som vakthund, och
tack vare `concurrency` startar nästa körning så fort den förra är klar. GitHubs cron kan vara sen,
men det spelar ingen roll här eftersom pollningen sker inuti körningen.

## Kommandon

```sh
python -m scout check                # hämta alla källor och visa vad som matchar (ingen state, inga notiser)
python -m scout check saab sectra    # bara vissa källor
python -m scout check voi --all      # visa alla jobb från en källa, inte bara matchningar
python -m scout run --dry-run        # en riktig pollning, men skriv ut meddelanden istället för att skicka
python -m scout run --loop 60        # polla i 60 minuter (kräver TELEGRAM_*-variablerna)
python -m pytest tests
```

## Lägga till ett företag

Öppna en jobbannons på företagets karriärsida och titta på URL:en eller ansök-knappen. En lista
över vad olika adresser betyder finns överst i `sources.yaml`. Lägg sedan till en rad, till exempel:

```yaml
- {key: mittbolag, name: Mitt Bolag, type: teamtailor, slug: mittbolag}
```

Kör `python -m scout check mittbolag --all` för att se att det fungerar.

## Justera filtret

Allt ligger i `filters.yaml`:

| Sektion | Styr |
|---|---|
| `job_type` | Ord som gör att ett jobb räknas som sommarjobb eller internship |
| `exclude_title` | Ord i titeln som utesluter jobbet, t.ex. exjobb |
| `non_tech_title` | Internships inom marknad, sälj, HR och liknande, som utesluts |
| `locations` | Orter som räknas som träff |
| `tech` | Ord som visar att ett jobb är tech (används bara för breda källor som JobStream) |

## Flytta till en VPS

```sh
python -m scout run --loop 525600   # ett år; kör under systemd eller i Docker
```

Utelämna `--commit`, så sparas state bara lokalt i `state/`.
