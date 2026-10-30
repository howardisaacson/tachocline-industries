# 0022. Store GFZ definitive Kp apart from the SWPC estimated index

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Howard Isaacson

## Context
The year ring and the 11-year ring need Kp older than the SWPC real-time files. Those files are an estimated product. GFZ Helmholtz Centre publishes the planetary Kp index since 1932 in one text file, including nowcasts that are later replaced by definitive values. The file also carries sunspot numbers under a different, non-commercial license.

Putting GFZ rows into `planetary_kp_3h` would make one column mean two products. A quiet estimated hour and a definitive hour would be indistinguishable.

## Options considered
### A. Upsert GFZ into `planetary_kp_3h`
- Pros: the existing `GET /api/kp-3h` route and the year ring need no new name.
- Cons: estimated and definitive Kp share a key. A later SWPC poll can overwrite a definitive value, or the reverse.
### B. A separate `gfz_kp_3h` table and `GET /api/kp-gfz`
- Pros: the SWPC table stays what its comment already says. Each GFZ row can say whether it is still a nowcast. The sunspot column can be left out.
- Cons: two Kp routes. The page has to choose which one a ring uses.

## Decision
We will use **option B**. The daily poller reads `https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt`, stores Kp and ap, and does not store the sunspot number. `definitive` is true when the file flag `D` is 1 or 2. The public day ring keeps the 1-minute SWPC estimate. The 30-day, 1-year, and 11-year rings read `GET /api/kp-gfz`.

## Consequences
- Easier: the long rings can fill from a cited archive. A nowcast is labeled and can be replaced on the next daily upsert.
- Harder: the health panel must ignore `gfz-%`, because a daily file would otherwise look hours old. The 5-minute SWPC Kp route is still the live estimate.

## How to explain this in an interview
"SWPC's real-time Kp and GFZ's definitive Kp are different products, so they do not share a table. The live hero uses the 1-minute estimate. The longer clocks use the GFZ file, which has a flag for rows that are still nowcasts. I left the sunspot column out because that series has a non-commercial license."

## Learn more
- GFZ, [Kp file since 1932](https://kp.gfz.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt)
- GFZ Data Services, [Geomagnetic Kp index, 10.5880/Kp.0001](https://doi.org/10.5880/Kp.0001)
- Matzka et al., [The geomagnetic Kp index, 10.1029/2020SW002641](https://doi.org/10.1029/2020SW002641)
