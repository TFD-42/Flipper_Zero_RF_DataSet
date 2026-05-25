# RF Standards & Regulatory References

Reference document for all standards, regulations, and official sources used in this dataset.

## International

| Standard | Scope | Authority |
|----------|-------|-----------|
| ITU Radio Regulations (Article 5) | Global frequency allocation table | ITU (Geneva) |
| ITU-R SM.1538 | Technical ID of radio emissions | ITU-R |
| ITU footnotes 5.150, 5.280, 5.328B, 5.340 | Band-specific conditions | ITU |

## Europe (CEPT/ETSI)

| Standard | Scope | Authority |
|----------|-------|-----------|
| ERC/REC 70-03 | SRD frequency bands & power limits | CEPT/ERC |
| ETSI EN 300 220 | SRD operating in 25-1000 MHz | ETSI |
| ETSI EN 300 328 | Wideband data (2.4 GHz ISM) | ETSI |
| ETSI EN 300 422 | PMSE audio (wireless mics) | ETSI |
| ETSI EN 302 208 | RFID 865-868 MHz | ETSI |
| ETSI EN 303 204 | Network-based SRD | ETSI |
| ECC/DEC/(04)08 | PMR446 harmonisation | CEPT/ECC |
| ECC/DEC/(06)13 | GSM/LTE 900 MHz | CEPT/ECC |
| ECC/DEC/(15)01 | 700 MHz duplex gap harmonisation | CEPT/ECC |
| EU Decision 2018/1538 | Harmonised SRD spectrum | EU Commission |
| TETRA / ETSI EN 300 392 | Trunked radio 380-400 MHz | ETSI |

## France

| Standard | Scope | Authority |
|----------|-------|-----------|
| TNRBF (Table Nationale) | National frequency allocation | ANFR |
| ARCEP decisions | Operator licensing (700/800/900 MHz) | ARCEP |
| Arrete du 30 janvier 2009 | Short range devices | French Government |
| Wize / GRDF spec | Gazpar smart meters (169 MHz) | GRDF/GrDF |

## United States

| Standard | Scope | Authority |
|----------|-------|-----------|
| 47 CFR Part 2.106 | US frequency allocation table | FCC |
| 47 CFR Part 15 | Unlicensed devices (ISM) | FCC |
| 47 CFR Part 18 | ISM equipment | FCC |
| 47 CFR Part 90 | Private land mobile radio | FCC |
| 47 CFR Part 95 | Personal radio services (GMRS, FRS, MURS) | FCC |
| 47 CFR Part 95H | WMTS (608-614 MHz) | FCC |
| NTIA Manual | Federal frequency allocations | NTIA |
| NTIA footnotes G27/G30 | 380-400 MHz federal exclusive | NTIA/IRAC |

## United Kingdom

| Standard | Scope | Authority |
|----------|-------|-----------|
| UK FAT (Freq Allocation Table) | National allocations | Ofcom |
| IR 2030 | SRD licence-exempt use | Ofcom |
| Ofcom auction results (2021) | 700 MHz awards (O2/VMO2) | Ofcom |
| Airwave (380-400 MHz) | TETRA emergency services | Ofcom/Home Office |

## Germany

| Standard | Scope | Authority |
|----------|-------|-----------|
| FreqBZPV | German frequency allocation plan | BNetzA |
| BOS-Digitalfunk | TETRA public safety (380-400 MHz) | BNetzA/BDBOS |
| BNetzA Vfg 10/2019 | SRD 863-870 MHz conditions | BNetzA |

## China

| Standard | Scope | Authority |
|----------|-------|-----------|
| MIIT Radio Regulations | National allocation | MIIT |
| PDT (Police Digital Trunking) | 350-370 MHz trunking | MIIT/MPS |
| GB/T 15945 | Power quality | SAC |
| CN ISM 470-510 MHz | LoRaWAN CN470 | MIIT |

## Russia

| Standard | Scope | Authority |
|----------|-------|-----------|
| GRFC regulations | National allocation | GRFC (Roskomnadzor) |
| Russian ISM 864-870 MHz | SRD band | GRFC |
| LoRaWAN RU864 | 864-870 MHz LoRa | LoRa Alliance + GRFC |

## Spain

| Standard | Scope | Authority |
|----------|-------|-----------|
| CNAF | National frequency allocation table | SETSI |
| CNAF nota UN-31 | SRD conditions | SETSI |

## Italy

| Standard | Scope | Authority |
|----------|-------|-----------|
| PNRF | National frequency allocation plan | MISE/MIMIT |
| AGCOM delibera 231/18/CONS | SRD band conditions | AGCOM |

## Switzerland

| Standard | Scope | Authority |
|----------|-------|-----------|
| NFA (Nationaler Frequenzzuweisungsplan) | National allocation | BAKOM/OFCOM-CH |
| Polycom network | TETRAPOL (not TETRA) 380-400 MHz | BAKOM/fedpol |

## Aviation / Maritime

| Standard | Scope | Authority |
|----------|-------|-----------|
| ICAO Annex 10 Vol. IV | SSR/ADS-B (1030/1090 MHz) | ICAO |
| ICAO Annex 10 Vol. I | DME specifications (incl. Y-mode 36 us) | ICAO |
| DO-260B / ED-102A | ADS-B technical standards | RTCA/EUROCAE |

## Emergency / Safety

| Standard | Scope | Authority |
|----------|-------|-----------|
| COSPAS-SARSAT C/S T.001 | 406.0-406.1 MHz distress beacons | COSPAS-SARSAT |
| ITU Appendix 15 | Distress & safety frequencies | ITU |
| ETSI EN 300 718 | Avalanche beacons 457 kHz | ETSI |
| MICS (402-405 MHz) | Medical implant communication | ITU-R SA.1346 |

## IoT / LPWAN

| Standard | Scope | Authority |
|----------|-------|-----------|
| LoRaWAN Regional Parameters | EU868, US915, CN470, RU864, etc. | LoRa Alliance |
| ETSI EN 303 204 | Network-based SRD | ETSI |
| Sigfox Radio Config | RC1 (EU 868), RC2 (US 902), RC4 (Asia) | Sigfox/UnaBiz |
| IEEE 802.15.4g | SUN PHY (sub-GHz) | IEEE |

## Protocol Databases (Pipeline)

| Database | Content | Used in step |
|----------|---------|-------------|
| rtl_433 protocol list | 200+ device decoders | 04_protocols_db |
| Flipper Zero SubGHz | 26 supported protocols | 04_protocols_db |
| 3GPP band definitions | LTE/NR band numbers & ranges | 03_rf_validation |
