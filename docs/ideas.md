# Ideas backlog

Product and science ideas. An idea becomes work when it gets a Roadmap item and, if significant, an ADR.

## Howard's comments (2026-10-20)
Summarised faithfully; [Hn] tags are referenced from [ROADMAP.md](ROADMAP.md).

| # | Comment | Where it lives |
|---|---|---|
| H1 | Create a GitHub repo from the beginning. | ADR 0010, Phase 0 |
| H2 | When we deploy, consider Google / AWS / other, so cloud becomes a resume skill. | ADR 0011, Phase 4 |
| H3 | Need a TI graphic with solar themes: eclipse, prominence, plage, faculae, sunspots, magnetic disconnections, flares, sub-surface loops, magnetic activity, satellites. Being made separately; goes in `assets/brand/`. | Phase 0/3 |
| H4 | Website design: don't start from scratch. Study 5 design-renowned sites and 5 highly rated scientific sites. | ADR 0013, Phase 3 |
| H5 | Always provide mobile and web-browser specs. | ADR 0012, AGENTS.md §5 |
| H6 | Use open-source data on a set of satellites over time. Value-add: predicting how long satellites stay in orbit / de-orbit due to solar activity. | Phase 2 + 5 |
| H7 | Bring in domain knowledge of other stars' activity (California Planet Search; S-index, Ca II H&K), e.g. a Sun-as-a-star comparison. | Phase 5 |
| H8 | "Impact of flare XX on power plants / power grids" feature. | Phase 5 |
| H9 | Use Rust where it fits, so Howard learns how and when. | ADR 0015, Phase 5 |
| H10 | jump2 uses a set of Docker containers, SkyPortal uses two: when do we need more than one? | ADR 0014 |
| H11 | Include satellite altitude data. Value-add: predicting when flares/storms inflate the thermosphere and cause drag and de-orbiting (Feb 2022 Starlink loss as an example). | Phase 2 + 5 |

## Feature ideas, fleshed out

### 1. Storm drag and satellite lifetime **[H6][H11]** (flagship)
- **Why it matters:** geomagnetic storms heat and expand the thermosphere, raising air density and drag on low-orbit satellites ([NOAA SWPC: Satellite Drag](https://www.swpc.noaa.gov/impacts/satellite-drag)).
- **Verified case study:** on **3 Feb 2022** SpaceX launched **49 Starlink** satellites into a low (~210 km perigee) staging orbit during minor (G1) geomagnetic storm conditions. SpaceX reported drag **up to 50% higher** than on previous launches, and **38** satellites re-entered within days. Studies attribute the loss to the storm combined with the very low insertion altitude and the satellites' low mass-to-area ratio.
  - Sources: SpaceX statement of 2022-02-08 (as reproduced by Japan's MIC: <https://www.soumu.go.jp/main_content/000794765.pdf>); "The Thermosphere Is a Drag: The 2022 Starlink Incident…" (2022, *Space Weather*), doi:[10.1029/2022SW003330](https://doi.org/10.1029/2022SW003330); Baruah et al., "The Loss of Starlink Satellites in February 2022…" (2024, *Space Weather*), doi:[10.1029/2023SW003716](https://doi.org/10.1029/2023SW003716).
  - These were checked via search results; the publisher pages block automated fetches (HTTP 403).
- **Data:** CelesTrak GP history (altitude from mean motion, BSTAR drag term), SWPC Kp/Dst/F10.7, CelesTrak decayed-objects table for ground truth.
- **Model path:** empirical correlation (decay rate vs Kp/F10.7) → a physics-lite integrator with NRLMSIS density (`pymsis`) → compare against actual decays. Clearly label predictions as predictions.
- **Visual:** altitude-vs-time per satellite with storm periods shaded; a "re-entry outlook" table.

### 2. Sun-as-a-star **[H7]**
- Put today's solar activity (sunspot number, F10.7, possibly a Ca II H&K–based solar S-index from published sources) in context with **stellar activity cycles** of Sun-like stars (Mount Wilson / CPS S-index time series).
- Story: "the tachocline-driven dynamo is not unique to the Sun." Howard's research domain gives this real authority.
- Needs: identify which stellar datasets are public and citable (to research). Unverified details are not to be published.

### 3. Space weather and power grids **[H8]**
- Explain how geomagnetic storms induce currents in long conductors (GICs) that can stress transformers, using NOAA's G-scale ([SWPC: Electric power transmission](https://www.swpc.noaa.gov/impacts/electric-power-transmission), [NOAA scales](https://www.swpc.noaa.gov/noaa-scales-explanation)).
- Feature: for a given flare/CME event (from DONKI), show the chain flare → CME → arrival → Kp/G-level → typical grid impacts at that level. **Framing:** educational and based on published scale descriptions, not a prediction of actual damage. Note that flares (X-rays) mainly affect HF radio; grid effects come from geomagnetic storms, usually CME-driven.
- Historic examples to research and verify before use (e.g., the March 1989 Québec blackout).

### 4. Other ideas
- Live ISS / satellite ground tracks over Berkeley; next-pass predictions (CelesTrak + SGP4).
- SatNOGS "listen to a satellite": the latest observation's waterfall and audio.
- Aurora probability map (SWPC OVATION) with mobile "will I see it tonight?" view.
- GOES/SDO image of the Sun next to the X-ray flux curve.
- FIRMS fire detections map for California.
