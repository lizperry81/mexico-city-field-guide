# Mexico City research: ten-area foundation · 10 November 2026

**Status: substantive draft, not exhaustive or editorially approved.** This branch does not alter the live app or `main`.

## Actual work completed
A cumulative downloadable V69 application/database package was produced from the user's V68 application ZIP. It includes **10 historical area dossiers, 71 new atomic claim records, 35 source records based on actually inspected institutional/publisher pages or selected article sections, 13 historical visual records or archive targets, 16 bibliography follow-up leads, 30 taught site stops, and a coverage audit for each area**. V69 also adds an offline-cache version and an interactive ten-area research explorer to the app's Research Library. The full ZIP, standalone JSON, six CSVs and relational SQLite database are attached to the automation run in ChatGPT; **this branch currently stores an area and research index, not the full bundled V69 app/database**.

The actual V68 app carried **9** geographical area IDs. They were retained. A new **Xochimilco research subarea** is nested under the existing `south` area to give 10 research dossiers without inventing a duplicate in the core app. The `south` research dossier covers **Cuicuilco and Ciudad Universitaria**, while the Xochimilco research dossier covers canals/chinampas. Roma and Condesa remain one current app ID, with separate subdivision histories discussed in its dossier.

| Dossier | Existing app ID | Key lens |
| --- | --- | --- |
| Centro Histórico, Templo Mayor and Zócalo | centro | Mexica sacred precinct, conquest, colonial capital, urban archaeology |
| Tlatelolco | tlatelolco | Independent merchant city, colonial college, 1968 and testimony |
| Chapultepec + museum landscape | chapul | Pre-Hispanic hill, water, warfare, imperial and national museums |
| Teotihuacán excursion | teo | Ancient urbanism, residential compounds, uncertain population |
| Coyoacán | coyo | Indigenous place, early colonial governance, modern artists |
| Roma + Condesa | roma | Porfirian land subdivision vs 1920s Hipódromo planning |
| Cuicuilco + Ciudad Universitaria | south | Early urbanism, volcano, modern public university design |
| San Ángel | sanangel | Carmelite estate, Reforma liberal, O’Gorman studio modernism |
| Paseo de la Reforma | reforma | Empire and nationalism, urban statues, protests, Revolution monument |
| Xochimilco (nested South) | south | Working chinampa agriculture, community life and water pressures |

## Scholar-first research, examined page-level evidence
- **Centro**: INAH Templo Mayor and Project histories, INAH Cathedral catalogue, INAH 2021 Zócalo archaeology abstract, UNESCO designation.
- **Tlatelolco**: INAH site with detailed building descriptions and 1473 history, UNAM M68 museum and 2018 historical collection announcement, INAH archaeological journal listing.
- **Chapultepec**: INAH castle building history, UNAM article on 1964 National Museum of Anthropology and collection provenance, INAH research on Indigenous settlement San Miguel Chapultepec.
- **Teotihuacán**: INAH site and avenue materials, George Cowgill's Cambridge University Press published chapter summary and TOC. The book itself was **not** read.
- **Coyoacán**: INAH protected-historic-zone chronology and CDMX government Casa Azul museum history.
- **Roma/Condesa**: INAH journal abstract by Manuel Perló Cohen (1988), Andrew Konove urban history article abstract, city Parque México history.
- **South**: INAH Cuicuilco institutional overview, UNESCO UNAM campus profile, 2026 INAH journal abstract on colonial reuse at Cuicuilco.
- **San Ángel**: INAH comprehensive El Carmen institutional description, INBAL Rivera–Kahlo studio history.
- **Reforma**: Louise Noelle Gras's 2025 UNAM article `Academia XXII 16(31), pp.143–161`. The article PDF was opened and visually checked on sample pages; selected parts of pp.143–148 were read, **not** a whole-article scholarly audit. City museum and site-operator monument histories separately consulted.
- **Xochimilco**: UNESCO dual listing and chinampa integrity/conservation description; 2025 INAH archaeology abstract on Late Postclassic domestic units.

## Images
Only **catalog or archive leads**, not free-to-reproduce images. Precisely identified leads include INAH's 1978 Raúl Arana Coyolxauhqui photographs, a 1906 Library of Congress San Francisco Street/Zócalo stereograph, a 1900 Library of Congress **Viga Canal** stereograph (not Xochimilco), and an IIE-UNAM Luis Márquez Romay photograph of `El Caballito`, inventory **08-765625**, reproduced as fig.1 in Noelle's 2025 article. Permissions, image downloads and precise Then/Now viewpoints are pending.

## Essential caveats
Neither 1,145 earlier app claims nor 327 inherited research-source records have been independently re-audited. All new claims are tagged `publication_ready=false`. An abstract is not full text, a source count is not proof of completeness, and page IDs matter. No historical image rights were cleared. The inherited 9-area app passed its existing integrity script; V69 new JavaScript and service worker passed syntax checks. A browser visual QA was blocked in the execution environment; do not describe the updated app as visually tested or deployed.

## Next research passes
1. Full text and page/figure extraction from specialist excavation reports and scholarly monographs; audit existing claims for false inference.
2. Expand **each** area's currently sparse primary sources, material-culture dossiers and archival maps.
3. Itemize and clear rights for archival images; align historical viewpoints with modern map coordinates.
4. Seek perspectives of present-day communities—especially chinamperos and Indigenous city residents—with attribution and consent.
5. Audit changing museum admissions, accessibility, public transport and visitor hours separately.
