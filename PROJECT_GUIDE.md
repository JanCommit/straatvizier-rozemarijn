# StraatVizier --- technische projectgids

## 1. Doel van het project

StraatVizier is een Streamlit-dashboard voor het analyseren en
visualiseren van Telraam-verkeersdata. De applicatie leest opgeslagen
meetgegevens uit Supabase, past kwaliteits- en periodefilters toe en
toont verkeersintensiteiten en autosnelheden in verschillende
tijdsweergaven.

De code is bewust opgesplitst in vier lagen:

1.  **Applicatie en gebruikersinterface** --- `app.py` en
    `src/straatvizier/ui/`
2.  **Analyse en datavorming** --- `analysis.py`, `data_helpers.py`,
    `speed_helpers.py`, `traffic_helpers.py`
3.  **Data-opslag en configuratie** --- `database.py`,
    `segment_config.py`, `config/segments.yaml`
4.  **Onderhoud, import en validatie** --- `scripts/`,
    `check_cameras.py`, `inspect_telraam_speed_data.py`

`app.py` is de orkestrator: het verbindt deze onderdelen, maar zoveel
mogelijk detailcode zit in gespecialiseerde modules.

------------------------------------------------------------------------

## 2. Projectstructuur

``` text
StraatVizier/
├── app.py
├── check_cameras.py
├── inspect_telraam_speed_data.py
├── requirements.txt
├── config/
│   └── segments.yaml
├── scripts/
│   ├── backfill.py
│   ├── backfill_2019.py
│   ├── backfill_coupure_links_2019.py
│   ├── backfill_previous.py
│   ├── backfill_segment.py
│   ├── backfill_speed_history.py
│   ├── inspect_segment_history.py
│   ├── inspect_sensor_history.py
│   ├── test_analysis.py
│   ├── test_database.py
│   ├── test_supabase.py
│   ├── test_telraam_api.py
│   ├── update_recent.py
│   ├── validate_speed_percentiles.py
│   └── validate_speed_percentiles_multisegment.py
├── src/
│   └── straatvizier/
│       ├── analysis.py
│       ├── data_helpers.py
│       ├── database.py
│       ├── period_state.py
│       ├── segment_config.py
│       ├── speed_helpers.py
│       ├── traffic_helpers.py
│       ├── traffic_hover_helpers.py
│       └── ui/
│           ├── chart_helpers.py
│           ├── header.py
│           ├── sidebar.py
│           ├── speed_chart.py
│           ├── speed_figure.py
│           ├── traffic_chart.py
│           └── traffic_figure.py
└── .github/
    └── workflows/
        └── update-data.yml
```

`__init__.py`-bestanden maken van de mappen Python-packages. Ze bevatten
momenteel geen eigen applicatielogica.

------------------------------------------------------------------------

## 3. Datastroom in één oogopslag

De normale dashboardstroom is:

``` text
Gebruiker
   ↓
sidebar.py + app.py
   ↓
segment_config.py / period_state.py
   ↓
database.py
   ↓
Supabase / PostgreSQL RPC's
   ↓
data_helpers.py / speed_helpers.py / traffic_helpers.py
   ↓
traffic_chart.py / speed_chart.py
   ↓
traffic_figure.py / speed_figure.py
   ↓
Plotly
   ↓
Streamlit-dashboard
```

Voor verkeersdata worden dagelijkse, uurlijkse en profielgegevens zo
veel mogelijk reeds gericht uit Supabase opgehaald. De applicatie hoeft
daardoor niet telkens de volledige historische uurdata naar Streamlit te
laden.

De periodieke invoerstroom is afzonderlijk:

``` text
GitHub Actions
   ↓
scripts/update_recent.py
   ↓
Telraam API
   ↓
transformatie
   ↓
Supabase UPSERT
   ↓
dashboard leest bijgewerkte data
```

------------------------------------------------------------------------

# 4. Kernbestanden

## `app.py`

**Rol:** hoofdprogramma en orkestrator van het Streamlit-dashboard.

Dit bestand:

-   configureert Streamlit;
-   voegt `src/` toe aan het Python-pad;
-   definieert gecachete database-oproepen;
-   laat de globale filters renderen;
-   bepaalt de beschikbare periode voor hoofdstraat en eventuele
    vergelijkingsstraat;
-   beheert de toegepaste periodeselectie;
-   haalt de benodigde verkeers- of snelheidsdata op;
-   bereidt de gegevens per richting en per straat voor;
-   roept uiteindelijk `build_traffic_figure()` of
    `build_speed_figure()` aan.

### Belangrijk

`app.py` hoort vooral de **workflow** te bepalen. Nieuwe
gespecialiseerde berekeningen of Plotly-details horen bij voorkeur niet
rechtstreeks hier terecht te komen als daar al een passende module voor
bestaat.

De databasefuncties worden met `st.cache_data` gecachet. De huidige TTL
is 86.400 seconden (24 uur). Bij wijzigingen aan de databron of bij
debugging moet men dus rekening houden met Streamlit-caching.

------------------------------------------------------------------------

## `src/straatvizier/database.py`

**Rol:** centrale toegang tot de StraatVizier-data in Supabase.

Belangrijkste functies:

-   `get_streets()` --- haalt bekende straten en segmenten op.
-   `get_measurement_bounds()` --- bepaalt eerste en laatste beschikbare
    meting zonder de volledige historie te laden.
-   `get_daily_traffic()` --- vraagt dagelijkse verkeersaggregaten op.
-   `get_hourly_traffic()` --- vraagt gefilterde uurdata op.
-   `get_hour_profile()` --- haalt het 24-uursprofiel op.
-   `get_daily_speed()` / `get_hourly_speed()` /
    `get_speed_hour_profile()` --- snelheidsvarianten.
-   `speed_percentile()` --- berekent een percentiel uit een
    snelheidshistogram.
-   `sum_speed_histograms()` --- combineert histogrammen.
-   `aggregate_speed_period()` --- aggregeert snelheid over een periode.
-   `get_speed_week_profile()` / `get_speed_year_profile()` --- bouwen
    snelheidsprofielen.

### Belangrijk

De module gebruikt `SUPABASE_URL` en `SUPABASE_SECRET_KEY` uit `.env` of
de runtime-omgeving. Secrets horen nooit in Git.

Een belangrijk ontwerpprincipe is dat zware verkeersaggregatie waar
mogelijk door PostgreSQL/Supabase-RPC's gebeurt. Dit beperkt de
hoeveelheid data die naar Streamlit wordt gestuurd.

De snelheid wordt afgeleid uit Telraam-snelheidshistogrammen.
Percentielen zoals V50, V85 en V95 zijn dus histogramgebaseerde
schattingen, geen individuele voertuigmetingen.

------------------------------------------------------------------------

## `src/straatvizier/analysis.py`

**Rol:** algemene verkeersanalyse op DataFrames.

Belangrijkste onderdelen:

-   `MODES` koppelt de Nederlandse UI-namen aan datakolommen (`car`,
    `bike`, `heavy`, `pedestrian`).
-   `prepare_measurements()` converteert UTC-tijd naar `Europe/Brussels`
    en voegt lokale datum en uur toe.
-   `filter_measurements()` filtert op uurvenster en minimale uptime.
-   `add_combined_mode()` telt geselecteerde vervoersmodi samen.
-   `daily_selected_traffic()` maakt dagtotalen.
-   week-, maand- en jaarfuncties berekenen gemiddeld dagelijks verkeer
    over geldige dagen.
-   `add_missing_days_as_gaps()` en `add_rolling_average()` ondersteunen
    correcte tijdreeksen en trends.

### Interpretatie

Een dag is niet automatisch geldig omdat er één meting bestaat. Het
aantal vereiste geldige meeturen wordt verderop via `min_hours`
toegepast.

Ontbrekende periodes worden bewust als gaten behandeld. Grafieklijnen
mogen niet visueel over ontbrekende meetperioden heen verbinden.

------------------------------------------------------------------------

## `src/straatvizier/data_helpers.py`

**Rol:** voorbereidende helpers voor verkeersweergaven.

-   `valid_daily()` houdt alleen dagen met voldoende geldige uren over.
-   `weighted_avg_uptime()` berekent uptime gewogen volgens het aantal
    meeturen.
-   `weekly_data()`, `monthly_data()` en `yearly_data()` maken complete
    tijdassen, inclusief ontbrekende perioden.
-   `hourly_with_gaps()` vult de uurindex aan zodat ontbrekende uren als
    echte gaten in de grafiek verschijnen.

Deze module vormt de brug tussen de ruwe/gesommeerde analyse en de
gegevensstructuur die de grafieken nodig hebben.

------------------------------------------------------------------------

## `src/straatvizier/traffic_helpers.py`

**Rol:** kleine vertaallaag tussen sidebar-keuzes en verkeerslogica.

-   `requested_directions()` vertaalt de gekozen richtingsoptie naar
    interne richtingscodes.
-   `traffic_label_for()` bepaalt een leesbaar label voor de gekozen
    vervoersmodi.
-   `mode_flags()` zet geselecteerde modi om naar booleans voor
    database-oproepen.

Dit bestand bevat bewust eenvoudige, herbruikbare UI-naar-datalogica.

------------------------------------------------------------------------

## `src/straatvizier/period_state.py`

**Rol:** beheer van de Streamlit-session-state voor de periodekiezer.

-   `initialize_period_state()` initialiseert/reset de periode wanneer
    de relevante straatcontext verandert.
-   `apply_period_state()` neemt de geselecteerde periode effectief in
    gebruik.
-   `reset_period_state()` zet de volledige beschikbare periode terug.

### Waarom dit apart bestaat

Streamlit voert het script opnieuw uit bij widgetinteractie. De
geselecteerde periode en de werkelijk toegepaste periode worden daarom
bewust apart beheerd. Zo verandert een grafiek pas wanneer de gebruiker
de periode toepast.

------------------------------------------------------------------------

## `src/straatvizier/segment_config.py`

**Rol:** lezen en interpreteren van straatgebonden configuratie uit
`config/segments.yaml`.

-   `load_direction_config()` leest richtinglabels en sensorhistoriek.
-   `direction_label()` maakt leesbare labels voor A→B en B→A.
-   `sensor_history_label()` maakt een compacte tekst van de
    sensorhistoriek.

`DIRECTION_CONFIG` wordt bij import uit YAML opgebouwd.

------------------------------------------------------------------------

# 5. Verkeersgrafieken

## `src/straatvizier/traffic_hover_helpers.py`

**Rol:** bepaalt de tijdsaanduiding bovenaan de unified hover voor
verkeersgrafieken.

Per weergave wordt een `x` plus leesbaar Nederlands tijdlabel gemaakt,
bijvoorbeeld:

-   uur → datum + uurperiode;
-   dag → datum;
-   week → maandag-zondagperiode;
-   maand → maandnaam + jaar;
-   jaar → jaar;
-   24u-profiel → uurperiode;
-   weekprofiel → volledige weekdag;
-   jaarprofiel → volledige maandnaam.

Dit bestand bepaalt dus vooral **wat de gebruiker als tijdcontext in de
hover leest**, niet de verkeerswaarde zelf.

------------------------------------------------------------------------

## `src/straatvizier/ui/chart_helpers.py`

**Rol:** gedeelde Plotly- en labelhelpers.

Bevat:

-   Nederlandse maandnamen;
-   Nederlandse maandafkortingen;
-   weekdagafkortingen en volledige weekdagnamen;
-   formattering van uurperioden en maanden;
-   `add_time_hover_carrier()`.

### Hover-carrier

De hover-carrier is een onzichtbare Plotly-trace die uitsluitend dient
om in `hovermode="x unified"` één centrale, vetgedrukte tijdsaanduiding
te tonen.

De trace bevat geen verkeersdata. Ze is een technische UI-oplossing en
mag niet zomaar verwijderd worden omdat ze onzichtbaar lijkt.

De carrier gebruikt intern `y=0`. Bij automatische y-asschaling moet
daarom worden voorkomen dat deze technische nulwaarde de zichtbare
schaal afdwingt; `traffic_figure.py` houdt daar expliciet rekening mee
wanneer "Y-as vanaf 0" uit staat.

------------------------------------------------------------------------

## `src/straatvizier/ui/traffic_chart.py`

**Rol:** voegt de eigenlijke verkeersseries voor één gekozen weergave
toe aan een Plotly-figuur.

De centrale functie `add_view()` behandelt de verschillende
tijdsweergaven:

-   Per uur
-   Per dag
-   Per week
-   Per maand
-   Per jaar
-   24u-profiel
-   Weekprofiel
-   Jaarprofiel

Hier wordt bepaald welke datareeks wordt getekend, hoe ontbrekende data
wordt behandeld, welke statistiek in de hover verschijnt en wanneer een
voortschrijdend gemiddelde wordt toegevoegd.

### Scheiding met `traffic_figure.py`

`traffic_chart.py` gaat vooral over **de inhoud van de traces**.\
`traffic_figure.py` gaat vooral over **de volledige figuur en layout**.

------------------------------------------------------------------------

## `src/straatvizier/ui/traffic_figure.py`

**Rol:** bouwt de volledige Plotly-verkeersfiguur.

Deze module bepaalt onder andere:

-   één of twee subplotrijen;
-   vergelijking "onder elkaar" versus "samen in één grafiek";
-   straat- en richtingsseries;
-   hover-carriers;
-   linker en gespiegelde rechter y-as;
-   y-as vanaf nul of data-afhankelijke schaal;
-   x-as-titels;
-   subplot-titels;
-   legend, marges, hoogte en grid.

### Technische aandachtspunten

Voor de rechter y-as worden onzichtbare dummy-traces gebruikt omdat
Plotly de secundaire as anders niet altijd zichtbaar maakt.

Bij "Y-as vanaf 0" uit wordt de range bepaald uit echte zichtbare
primaire traces. De onzichtbare hover-carrier op `y=0` wordt
uitgesloten, zodat nul niet onterecht in beeld blijft.

Bij vergelijking onder elkaar is extra verticale ruimte nodig tussen de
bovenste x-as-titel en de titel van de onderste straat.

------------------------------------------------------------------------

# 6. Snelheid

## `src/straatvizier/speed_helpers.py`

**Rol:** maakt snelheidsdata geschikt voor de acht dashboardweergaven en
voor hoverlabels.

-   `valid_daily_speed()` filtert dagen volgens minimum aantal geldige
    uren.
-   `speed_view_data()` kiest/aggeregeert de juiste dataset voor de
    gekozen weergave.
-   `speed_time_hover_data()` maakt de Nederlandse tijdlabels voor
    unified hover.

Voor week- en jaarprofielen gebruikt deze module gespecialiseerde
aggregatiefuncties uit `database.py`.

------------------------------------------------------------------------

## `src/straatvizier/ui/speed_chart.py`

**Rol:** voegt de zichtbare snelheidstraces aan de figuur toe.

Belangrijkste functie: `add_speed_traces()`.

De grafiek werkt met snelheidspercentielen zoals V50, V85 en V95 en
toont daarnaast relevante metadata zoals het aantal auto's dat in de
snelheidsverdeling zit.

Kleuren voor hoofdstraat, vergelijking en trends zijn hier gedefinieerd.

------------------------------------------------------------------------

## `src/straatvizier/ui/speed_figure.py`

**Rol:** bouwt de volledige Plotly-figuur voor autosnelheid.

Vergelijkbaar met `traffic_figure.py`, maar specifiek voor snelheid:

-   maakt subplot(s);
-   bereidt data per gekozen view voor;
-   voegt snelheidstraces toe;
-   verzorgt hover;
-   configureert assen, legend en layout;
-   ondersteunt straatvergelijking.

------------------------------------------------------------------------

# 7. Algemene UI

## `src/straatvizier/ui/sidebar.py`

**Rol:** centrale definitie van de globale dashboardfilters.

Hier worden onder andere gekozen:

-   hoofdstraat;
-   vergelijken of niet;
-   vergelijkingsstraat;
-   vergelijkingslayout;
-   analyse-type;
-   vervoersmodi;
-   richting;
-   uurvenster;
-   minimale uptime;
-   minimum geldige uren per dag;
-   y-as vanaf nul.

Wanneer een nieuwe globale gebruikersoptie nodig is, is dit meestal de
eerste plaats om te kijken.

------------------------------------------------------------------------

## `src/straatvizier/ui/header.py`

**Rol:** rendert de vaste/frozen bovenkant van het dashboard.

Deze module zorgt ervoor dat de actuele analysecontext duidelijk
zichtbaar blijft terwijl de gebruiker door de pagina scrolt.

------------------------------------------------------------------------

# 8. Configuratie

## `config/segments.yaml`

**Rol:** menselijke configuratie van de Telraam-segmenten.

Per segment bevat dit bestand:

-   Telraam-segment-ID;
-   straatnaam;
-   betekenis van richting A→B;
-   betekenis van richting B→A;
-   bekende sensorhistoriek.

Dit is de primaire plaats om straatgebonden metadata te onderhouden.

### Belangrijk

Een nieuwe straat toevoegen is meer dan alleen een regel in de UI
toevoegen. Het segment moet ook correct in de databank/data-import
aanwezig zijn.

Sensorhistoriek is informatieve metadata en kan ook echte meetgaten
verklaren wanneer een sensor tussen twee perioden niet actief was.

------------------------------------------------------------------------

# 9. Data-import en onderhoud

## `scripts/update_recent.py`

**Rol:** normale periodieke productie-update.

Dit is het belangrijkste operationele importsysteem. Het:

1.  leest de segmenten uit `segments.yaml`;
2.  haalt recente Telraam-data op;
3.  transformeert de API-records;
4.  maakt straat/segment aan indien nodig;
5.  schrijft de meetgegevens via UPSERT naar Supabase.

`LOOKBACK_DAYS = 7` is bewust: elke run haalt opnieuw een overlap van
zeven dagen op. Daardoor kunnen late of gecorrigeerde Telraam-records
bestaande databasegegevens bijwerken.

De API-aanroep bevat retrylogica voor tijdelijke netwerkfouten, rate
limiting en serverfouten.

------------------------------------------------------------------------

## `.github/workflows/update-data.yml`

**Rol:** automatiseert `scripts/update_recent.py` via GitHub Actions.

De workflow:

-   kan handmatig gestart worden (`workflow_dispatch`);
-   draait ook dagelijks via cron;
-   installeert Python 3.11 en `requirements.txt`;
-   leest Telraam- en Supabase-credentials uit GitHub repository
    secrets;
-   voert `python scripts/update_recent.py` uit.

### Let op

De huidige cronexpressie is:

``` text
30 2 * * *
```

Dat betekent **02:30 UTC**. De comment in het workflowbestand vermeldt
momenteel "04:30 UTC"; die comment komt dus niet overeen met de
feitelijke cronexpressie en verdient correctie wanneer documentatie-only
wijzigingen aan de repository worden gedaan.

------------------------------------------------------------------------

# 10. Historische backfill-scripts

Deze scripts zijn geen onderdeel van de normale dashboardrun. Ze dienen
om historische data op te halen of specifieke
datagaten/ontwikkelingssituaties te behandelen.

## `scripts/backfill.py`

Algemene historische backfill op basis van `segments.yaml`, vanaf de
ingestelde startdatum. Werkt per periode/maand en schrijft Telraam-data
naar Supabase.

## `scripts/backfill_speed_history.py`

Historische backfill specifiek gericht op beschikbare
snelheidshistogrammen. Controleert of een maand al snelheidsdata bevat
voordat opnieuw wordt opgehaald.

## `scripts/backfill_2019.py`

Gerichte historische import voor in het script vastgelegde
segmenten/periodes uit 2019.

## `scripts/backfill_coupure_links_2019.py`

Specifieke 2019-backfill voor de in het script gedefinieerde Coupure
Links-doelen.

## `scripts/backfill_segment.py`

Ouder/gericht backfillscript voor één hardgecodeerd segment
(`Rozemarijnstraat`, Telraam-segment 155073).

## `scripts/backfill_previous.py`

Een eerdere variant van de algemene backfilllogica. Behandel dit als
historisch/onderhoudsgereedschap tenzij bewust opnieuw gebruikt.

### Praktische regel

Gebruik voor normale dagelijkse updates **`update_recent.py`**.\
Gebruik backfills alleen bewust voor historische aanvulling of herstel,
en controleer eerst segment, periode en bestaande data.

------------------------------------------------------------------------

# 11. Inspectie- en diagnosescripts

## `check_cameras.py`

Vraagt voor een vaste lijst Telraam-segmenten de camera/sensorinstances
op en print onder andere hardwareversie, status en actieve perioden.

Nuttig om sensorwissels of sensorhistoriek te onderzoeken. Het bevat
eenvoudige afhandeling van HTTP 429 rate limiting.

## `inspect_telraam_speed_data.py`

Direct diagnostisch script tegen de Telraam traffic API voor één
hardgecodeerd segment en tijdvak.

Het toont:

-   beschikbare velden;
-   velden waarvan de naam `speed` bevat;
-   de inhoud van de snelheidshistogrammen per uurrecord.

Gebruik dit om de ruwe Telraam-API-respons te begrijpen, niet als
onderdeel van de dashboardrun.

## `scripts/inspect_segment_history.py`

Inspecteert historische Telraam-records voor een ingesteld segment en
periode.

## `scripts/inspect_sensor_history.py`

Uitgebreidere sensorhistorie-inspectie op basis van `segments.yaml`.
Haalt camera-instances op, interpreteert actieve perioden en kan
overlappende/aansluitende perioden samenvatten.

------------------------------------------------------------------------

# 12. Test- en validatiescripts

## `scripts/test_analysis.py`

Handmatige/technische controle van analysefuncties en verwachte
resultaten.

## `scripts/test_database.py`

Controle van databasefuncties tegen de beschikbare Supabase-data.

## `scripts/test_supabase.py`

Kleine connectiviteitstest voor Supabase en de ingestelde credentials.

## `scripts/test_telraam_api.py`

Kleine connectiviteitstest voor de Telraam API en API-key.

## `scripts/validate_speed_percentiles.py`

Valideert de berekening van snelheidspercentielen uit opgeslagen
histogramdata voor een gerichte situatie.

## `scripts/validate_speed_percentiles_multisegment.py`

Dezelfde soort validatie over meerdere segmenten, nuttig om te
controleren of de histogram-/percentiellogica niet slechts voor één
straat correct lijkt.

### Opmerking

Deze bestanden heten `test_*.py`, maar vormen geen formele
pytest-testsuite. Ze zijn vooral uitvoerbare controle- en
diagnosescripts.

------------------------------------------------------------------------

# 13. Overige bestanden

## `requirements.txt`

Python-afhankelijkheden van het project:

-   `requests` --- HTTP-verkeer naar Telraam;
-   `python-dotenv` --- lokale `.env` laden;
-   `python-dateutil` --- datumrekenwerk;
-   `supabase` --- Supabase-client;
-   `PyYAML` --- `segments.yaml` lezen;
-   `streamlit` --- dashboard;
-   `pandas` --- data-analyse;
-   `plotly` --- interactieve grafieken.

## `.env`

Niet in de gedeelde project-ZIP en niet in Git bewaren.

Bevat lokaal minstens:

``` text
TELRAAM_API_KEY=...
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
```

## `.env.example`

Kan als veilig sjabloon dienen voor de namen van vereiste environment
variables, zonder echte secrets.

------------------------------------------------------------------------

# 14. Belangrijke ontwerpkeuzes

## Lokale tijd

Telraam-/database-timestamps worden waar nodig geïnterpreteerd vanuit
UTC en voor analyse omgezet naar:

``` text
Europe/Brussels
```

Dit is belangrijk voor daggrenzen, uurfilters en zomer-/wintertijd.

## Uptime

`min_uptime` bepaalt welke meeturen voldoende betrouwbaar zijn om mee te
tellen.

Daarnaast bepaalt `min_hours` hoeveel geldige uren een dag minimaal
nodig heeft om in dag-/week-/maand-/jaarstatistieken te worden
opgenomen.

Dit zijn twee verschillende kwaliteitsfilters.

## Ontbrekende data

Ontbrekende dagen/uren worden bewust in tijdassen ingevoegd als lege
waarden. Hierdoor tekent Plotly geen misleidende doorlopende lijn over
meetgaten.

## Richtingen

Intern worden onder andere `both`, `ab` en `ba` gebruikt. De menselijke
betekenis van A→B en B→A staat per straat in `segments.yaml`.

## Verkeersmodi

De gebruiker kan afzonderlijke of gecombineerde modi kiezen. De interne
basisvelden zijn:

``` text
car
bike
heavy
pedestrian
```

## Snelheid

Snelheidsanalyse is gebaseerd op aantallen auto's in snelheidsbins.
V50/V85/V95 zijn daaruit berekende percentielen en moeten als
indicatieve verdelingsstatistieken worden geïnterpreteerd.

## Unified hover

De grafieken gebruiken `hovermode="x unified"`. Een aparte onzichtbare
carrier-trace levert de centrale tijdsaanduiding zodat tijd niet bij
iedere zichtbare reeks herhaald hoeft te worden.

------------------------------------------------------------------------

# 15. Waar moet ik zijn als ik iets wil wijzigen?

  ------------------------------------------------------------------------------
  Gewenste wijziging                  Begin hier
  ----------------------------------- ------------------------------------------
  Nieuwe straat/segmentmetadata       `config/segments.yaml`

  Richtinglabels wijzigen             `config/segments.yaml`,
                                      `segment_config.py`

  Sensorhistoriek wijzigen            `config/segments.yaml`

  Sidebarfilter wijzigen/toevoegen    `ui/sidebar.py`

  Periodeselectiegedrag wijzigen      `period_state.py`, daarna `app.py`

  Data anders uit Supabase ophalen    `database.py`

  Verkeersaggregatie wijzigen         `analysis.py`, `data_helpers.py`

  Vervoersmodi/richtingskeuze         `traffic_helpers.py`
  vertalen                            

  Verkeers-hovertekst wijzigen        `traffic_hover_helpers.py`,
                                      `ui/chart_helpers.py`

  Verkeerstrace/statistiek wijzigen   `ui/traffic_chart.py`

  Verkeerslayout/assen/subplots       `ui/traffic_figure.py`
  wijzigen                            

  Snelheidsaggregatie/viewdata        `speed_helpers.py`, eventueel
  wijzigen                            `database.py`

  Snelheidstraces wijzigen            `ui/speed_chart.py`

  Snelheidslayout wijzigen            `ui/speed_figure.py`

  Frozen header wijzigen              `ui/header.py`

  Normale data-update wijzigen        `scripts/update_recent.py`

  Historische data aanvullen          `scripts/backfill*.py`

  Sensorwissels onderzoeken           `scripts/inspect_sensor_history.py`,
                                      `check_cameras.py`

  Ruwe snelheidsvelden onderzoeken    `inspect_telraam_speed_data.py`

  Snelheidspercentielen controleren   `scripts/validate_speed_percentiles*.py`

  Automatische updateplanning         `.github/workflows/update-data.yml`
  wijzigen                            
  ------------------------------------------------------------------------------

------------------------------------------------------------------------

# 16. Richtlijn voor toekomstige codecomments

Comments en docstrings moeten vooral uitleggen **waarom** iets gebeurt,
niet letterlijk herhalen **wat** de Python-regel doet.

Goed commentaar is bijvoorbeeld nuttig bij:

-   Telraam-specifieke interpretaties;
-   A→B/B→A-richtingen;
-   UTC versus Belgische lokale tijd;
-   uptime- en geldige-dagcriteria;
-   ontbrekende perioden;
-   histogramgebaseerde snelheidspercentielen;
-   onzichtbare Plotly hover- of secondary-y-traces;
-   Streamlit session-state;
-   caching;
-   database-RPC's;
-   historische scripts die slechts voor een specifieke
    migratie/backfill bestaan.

Voorbeeld van nuttig commentaar:

``` python
# Deze onzichtbare trace bevat geen verkeersdata.
# Ze activeert alleen de rechter secondary_y-as, omdat Plotly
# die zonder gekoppelde trace soms niet rendert.
```

Minder nuttig:

``` python
# Loop over directions.
for direction in directions:
```

Voor publieke of inhoudelijk belangrijke functies verdient een korte
docstring de voorkeur. Voor een technisch uitzonderingsblok binnen een
functie is een gerichte inline comment meestal duidelijker.

------------------------------------------------------------------------

# 17. Onderhoudsregels

1.  **Wijzig configuratie, analyse, data-ophaling en visualisatie niet
    tegelijk** wanneer dat niet noodzakelijk is.
2.  Test een functionele wijziging eerst lokaal vóór push/deployment.
3.  Houd secrets uitsluitend in `.env` of GitHub Secrets.
4.  Gebruik `update_recent.py` voor normale updates; voer historische
    backfills alleen bewust uit.
5.  Behoud gaten in ontbrekende meetdata.
6.  Controleer bij wijzigingen aan tijdlogica altijd UTC én
    `Europe/Brussels`.
7.  Controleer bij wijzigingen aan hoverlogica alle relevante
    tijdsweergaven.
8.  Behandel onzichtbare Plotly-traces niet automatisch als overbodige
    code.
9.  Houd `app.py` als orkestrator; plaats gespecialiseerde logica in de
    bestaande passende module.
10. Werk deze gids bij wanneer verantwoordelijkheden van bestanden
    wezenlijk veranderen.

------------------------------------------------------------------------

## 18. Korte mentale kaart

Wanneer je later opnieuw in het project duikt, volstaat meestal deze
indeling:

``` text
app.py
    = welke workflow voert het dashboard uit?

database.py
    = welke data halen we op?

analysis.py / *_helpers.py
    = hoe interpreteren en vormen we die data?

ui/*_chart.py
    = welke reeksen tekenen we?

ui/*_figure.py
    = hoe ziet de volledige grafiek eruit?

sidebar.py / header.py
    = hoe bedient en leest de gebruiker het dashboard?

segments.yaml
    = wat weten we over de straten en sensoren?

scripts/update_recent.py
    = hoe komt nieuwe Telraam-data in Supabase?

scripts/backfill*.py
    = hoe vullen/herstellen we historische data?
```

Dat is de kernarchitectuur van StraatVizier.
