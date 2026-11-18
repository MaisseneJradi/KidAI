# Dataset KidAI — statistiques

Fichier : `data/processed/kidai_dataset.parquet` (régénéré par `dvc repro`).

- **20 911** lignes  **2 243** questions de base
- test : 0 / 217 lignes annotées
- accord des annotateurs : {"annotees_A": 0, "annotees_B": 0, "communes": 0, "kappa": null}
- relecture des traductions : {"echantillon": 499, "relues": 0}

## Par source

| source | test | train | val | total |
|---|---:|---:|---:|---:|
| kidbench | 54 | 8 295 | 924 | 9 273 |
| minorbench | 32 | 2 262 | 249 | 2 543 |
| orbench | 72 | 6 084 | 672 | 6 828 |
| safechild | 36 | 1 404 | 162 | 1 602 |
| synthetic | 23 | 576 | 66 | 665 |
| total | 217 | 18 621 | 2 073 | 20 911 |

## Par langue

| lang | test | train | val | total |
|---|---:|---:|---:|---:|
| ar | 70 | 6 067 | 672 | 6 809 |
| en | 66 | 6 132 | 684 | 6 882 |
| fr | 81 | 6 422 | 717 | 7 220 |
| total | 217 | 18 621 | 2 073 | 20 911 |

## Par tranche d'âge

| tranche | test | train | val | total |
|---|---:|---:|---:|---:|
| 12-14 | 106 | 6 200 | 689 | 6 995 |
| 6-8 | 105 | 6 211 | 693 | 7 009 |
| 9-11 | 6 | 6 210 | 691 | 6 907 |
| total | 217 | 18 621 | 2 073 | 20 911 |

## Par niveau de risque (dérivé de la source)

| ground_truth_harm | test | train | val | total |
|---|---:|---:|---:|---:|
| borderline | 105 | 11 929 | 1 348 | 13 382 |
| safe | 26 | 1 139 | 86 | 1 251 |
| unsafe | 86 | 5 553 | 639 | 6 278 |
| total | 217 | 18 621 | 2 073 | 20 911 |

## Par sujet

| topic | test | train | val | total |
|---|---:|---:|---:|---:|
| culture | 5 | 120 | 10 | 135 |
| curiosite | 16 | 1 542 | 123 | 1 681 |
| danger | 10 | 810 | 66 | 886 |
| discrimination | 24 | 1 563 | 234 | 1 821 |
| ecole | 4 | 783 | 54 | 841 |
| emotions | 22 | 2 002 | 221 | 2 245 |
| illegal | 22 | 2 118 | 270 | 2 410 |
| langage | 18 | 450 | 54 | 522 |
| maths | 0 | 41 | 6 | 47 |
| morale | 22 | 1 857 | 216 | 2 095 |
| numerique | 16 | 1 700 | 201 | 1 917 |
| relations | 12 | 940 | 47 | 999 |
| sante | 10 | 821 | 84 | 915 |
| sciences | 6 | 157 | 22 | 185 |
| sexualite | 16 | 1 719 | 249 | 1 984 |
| substances | 6 | 396 | 27 | 429 |
| violence | 8 | 1 602 | 189 | 1 799 |
| total | 217 | 18 621 | 2 073 | 20 911 |

## Risque × source (questions de base)

| source | borderline | safe | unsafe | total |
|---|---:|---:|---:|---:|
| kidbench | 553 | 50 | 0 | 603 |
| minorbench | 0 | 0 | 298 | 298 |
| orbench | 499 | 0 | 300 | 799 |
| safechild | 53 | 0 | 141 | 194 |
| synthetic | 110 | 239 | 0 | 349 |
| total | 1 215 | 289 | 739 | 2 243 |

## Jeu de test : action attendue × tranche d'âge

| action | 12-14 | 6-8 | 9-11 | total |
|---|---:|---:|---:|---:|
| — | 106 | 105 | 6 | 217 |
| total | 106 | 105 | 6 | 217 |

## T-HSAB (derja, fichier séparé)

| label | test | train | val | total |
|---|---:|---:|---:|---:|
| abusive | 111 | 892 | 111 | 1 114 |
| hate | 106 | 856 | 106 | 1 068 |
| normal | 378 | 3 026 | 378 | 3 782 |
| total | 595 | 4 774 | 595 | 5 964 |

## PKU-SafeRLHF (préférences, fichier séparé)

| generator | test | train | total |
|---|---:|---:|---:|
| Alpaca-7B | 3 036 | 27 393 | 30 429 |
| Alpaca2-7B | 2 848 | 25 564 | 28 412 |
| Alpaca3-8B | 2 327 | 20 950 | 23 277 |
| total | 8 211 | 73 907 | 82 118 |
