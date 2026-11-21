# T-REx base cleaning: everything dropped

Test 04 run-02. The rule (scripts/fir/clean_base.py): a base entity is dropped when its whole name is one stopword (not all-caps, not a contraction fragment like Ain or Don), one number, or punctuation, unless a document fact uses it; its base facts go with it. Generic lower-case words are reported, never dropped. Wikidata IDs: the T-REx export we use stores names only, so each ID is either exact (from the entity's own Wikipedia article, where one of its facts came from it) or a label-search candidate marked not verified.

## Summary

| | Base (T-REx) | Built graph (base + documents) |
|---|---|---|
| Entities dropped | 60 | 59 |
| Facts dropped | 107 | 102 |
| Base entities left with no facts, dropped | 5 | 5 |
| Nodes | 1,560,412 -> 1,560,240 | 1,579,423 -> 1,579,257 |
| Edges | 2,430,832 -> 2,430,618 | 2,466,675 -> 2,466,471 |
| Facts | 1,215,416 -> 1,215,309 | 1,230,691 -> 1,230,589 |
| SUPERSEDES edges removed | 0 | 0 |

By category (base): {'number': 59, 'stopword': 1}. Kept because documents use them: 90210 (in the built graph). Document links that pointed to a dropped entity: 1 (90210 -> 90210). Base entities left with no facts and dropped with them: 5 (those named in the facts below: natural number, tetrode).

## The dropped entities and their facts

### 005 (number, 2 facts)

Wikidata: [Q4545526](https://www.wikidata.org/wiki/Q4545526) (1981 video game; from Wikipedia article '005')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 005 | genre | stealth game | 005 |
| 005 | platform | arcade game | 005 |

### 01011001 (number, 1 fact)

Wikidata: [Q974456](https://www.wikidata.org/wiki/Q974456) (2008 studio album by Ayreon; from Wikipedia article '01011001')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 01011001 | performer | Ayreon | 01011001 |

### 013 (number, 2 facts)

Wikidata: [Q2319846](https://www.wikidata.org/wiki/Q2319846) (Music venue in Tilburg, the Netherlands; from Wikipedia article '013')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 013 | country | Netherlands | 013 |
| 013 | located in the administrative territorial entity | Tilburg | 013 |

### 020120 (number, 1 fact)

Wikidata: [Q4545556](https://www.wikidata.org/wiki/Q4545556) (2002 live album by The Mad Capsule Markets; from Wikipedia article '020120')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 020120 | instance of | live album | 020120 |

### 0304 (number, 2 facts)

Wikidata: [Q3055389](https://www.wikidata.org/wiki/Q3055389) (2003 studio album by Jewel; from Wikipedia article '0304')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 0304 | instance of | studio album | 0304 |
| 0304 | record label | Atlantic Records | 0304 |

### 04092001 (number, 1 fact)

Wikidata: [Q4545566](https://www.wikidata.org/wiki/Q4545566) (2005 live album by Boris and Merzbow; from Wikipedia article '04092001')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 04092001 | instance of | live album | 04092001 |

### 1011001 (number, 2 facts)

Wikidata: [Q234019](https://www.wikidata.org/wiki/Q234019) (Dutch singer and musician; from Wikipedia article 'Anneke van Giersbergen')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 1011001 | performer | Ayreon | Anneke van Giersbergen |
| 1011001 | instance of | studio album | 01011001 |

### 11001001 (number, 2 facts)

Wikidata: [Q901789](https://www.wikidata.org/wiki/Q901789) (15th episode of the 1st season of Star Trek: The Next Generation; from Wikipedia article '11001001')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 11001001 | country of origin | United States | 11001001 |
| 11001001 | country of origin | American | 11001001 |

### 144000 (number, 1 fact)

Wikidata: [Q2807787](https://www.wikidata.org/wiki/Q2807787) (Natural number; from Wikipedia article '144000 (number)')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 144000 | instance of | natural number | 144000 (number) |

### 1600 (number, 1 fact)

Wikidata: [Q6720](https://www.wikidata.org/wiki/Q6720) (Calendar year; from Wikipedia article '1600')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 1600 | instance of | leap year | 1600 |

### 181920 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 181920 | performer | Namie Amuro | 181920 |
| 181920 | record label | avex trax | 181920 |

### 1901 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 1901 | part of | CE | 1901 |
| 1901 | part of | AD | 1901 |

### 1902 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 1902 | part of | AD | 1902 |
| 1902 | part of | CE | 1902 |

### 1943 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 1943 | part of | CE | 1943 |
| 1943 | part of | AD | 1943 |

### 2004 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2004 | instance of | leap year | 2004 |

### 2008 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2008 | instance of | leap year | 2008 |

### 2012 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2012 | instance of | leap year | 2012 |

### 2016 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2016 | instance of | leap year | 2016 |

### 2020 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2020 | instance of | leap year | 2020 |

### 2024 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2024 | instance of | leap year | 2024 |

### 2028 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2028 | instance of | leap year | 2028 |

### 2032 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2032 | instance of | leap year | 2032 |

### 2036 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2036 | instance of | leap year | 2036 |

### 2541 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2541 | instance of | EP | 2541 |

### 2666 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 2666 | original language of film or tv show | Spanish | 2666 |

### 285 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 285 | instance of | manuscript | Uncial 0285 |

### 35007 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 35007 | genre | space rock | 35007 |
| 35007 | country of origin | Netherlands | 35007 |

### 4444444444 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 4444444444 | director | Takashi Shimizu | Katasumi and 4444444444 |
| 4444444444 | screenwriter | Takashi Shimizu | Katasumi and 4444444444 |

### 45365 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 45365 | genre | documentary film | 45365 |

### 456132015 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 456132015 | instance of | EP | 456132015 |

### 522666 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 522666 | director | David Nutter | 522666 |
| 522666 | screenwriter | Glen Morgan | 522666 |

### 65001 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 65001 | instance of | character encoding | Code page |

### 6502 (number, 6 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 6502 | subclass of | CPU | Hudson Soft HuC6280 |
| 6502 | subclass of | microprocessor | Chuck Peddle |
| 6502 | instance of | microprocessor | Chuck Peddle |
| 6502 | instance of | CPU | Hudson Soft HuC6280 |
| 6502 | instance of | MPU | WDC 65816/65802 |
| 6502 | subclass of | MPU | WDC 65816/65802 |

### 65802 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 65802 | subclass of | microprocessor | Apple Assembly Line |

### 65816 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 65816 | subclass of | microprocessor | Apple Assembly Line |
| 65816 | subclass of | MPU | WDC 65816/65802 |

### 68000 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 68000 | subclass of | m68k | Xcopilot |

### 68020 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 68020 | instance of | CPU | Miracle Systems |

### 68030 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 68030 | instance of | CPU | Amiga 3000 |

### 68040 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 68040 | instance of | processing unit | VMac |
| 68040 | instance of | CPU | NeXT Laser Printer |

### 68060 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 68060 | instance of | CPU | Amiga 4000T |

### 6809 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 6809 | subclass of | CPU | Aamber Pegasus |

### 68881 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 68881 | subclass of | floating point unit | Motorola 68030 |
| 68881 | subclass of | FPU | Macintosh IIx |

### 68882 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 68882 | subclass of | floating point unit | Motorola 68030 |
| 68882 | subclass of | FPU | Macintosh IIci |

### 72826 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 72826 | country of origin | American | 72826 |

### 7554 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 7554 | instance of | video game | 7554 |

### 8051 (number, 2 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 8051 | subclass of | microcontroller | Keil (company) |
| 8051 | subclass of | MCU | MCU 8051 IDE |

### 8085 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 8085 | subclass of | microprocessor | Z-DOS |

### 8086 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 8086 | instance of | microprocessor | Masatoshi Shima |

### 8088 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 8088 | subclass of | CPU | Imagineering Australia |

### 8701 (number, 4 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 8701 | record label | Arista Records | 8701 |
| 8701 | country of origin | American | 8701 |
| 8701 | country of origin | United States | 8701 |
| 8701 | instance of | studio album | 8701 |

### 893239 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 893239 | country of origin | Japan | 893239 |

### 8974 (number, 1 fact)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 8974 | subclass of | tetrode | 8974 |

### 90125 (number, 4 facts)

Wikidata: no Wikidata match by label

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 90125 | genre | progressive rock | Halcyon (Orbital song) |
| 90125 | instance of | studio album | Big Generator |
| 90125 | record label | Atco Records | 90125 |
| 90125 | record label | Atco | Big Generator |

### 90210 (number, 5 facts)

Wikidata: [Q4924406](https://www.wikidata.org/wiki/Q4924406) (American actor (born 1985); from Wikipedia article 'Blake Hood')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 90210 | country of origin | US | E4 (TV channel) |
| 90210 | genre | soap opera | Blake Hood |
| 90210 | country of origin | United States | We're Not in Kansas Anymore |
| 90210 | original language of film or tv show | English | Terri Hawkes |
| 90210 | country of origin | American | Make It Right |

### 91025 (number, 1 fact)

Wikidata: [Q9286874](https://www.wikidata.org/wiki/Q9286874) (American rock band; from Wikipedia article '91025')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 91025 | instance of | EP | 91025 |

### 94124 (number, 1 fact)

Wikidata: [Q4645942](https://www.wikidata.org/wiki/Q4645942) (1995 EP by Zip Code Rapists; from Wikipedia article '94124')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| 94124 | instance of | EP | 94124 |

### ONE (number, 2 facts)

Wikidata: [Q4206809](https://www.wikidata.org/wiki/Q4206809) (Asian pay television channel; from Wikipedia article 'ONE TV ASIA')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| ONE | owned by | Sony Pictures Entertainment | ONE TV ASIA |
| ONE | owned by | Sony | GEM TV ASIA |

### Seventeen (number, 6 facts)

Wikidata: [Q606680](https://www.wikidata.org/wiki/Q606680) (American magazine (1999–2008); from Wikipedia article 'Cosmogirl')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| Seventeen | owned by | Hearst | Cosmogirl |
| Seventeen | country of origin | American | Seventeen (Serafin novel) |
| Seventeen | owned by | Hearst Corporation | Hearst Tower (Manhattan) |
| Seventeen | country of origin | United States | Seventeen (Tarkington novel) |
| Seventeen | original language of film or tv show | English | Farrukh Khan Pitafi |
| Seventeen | country of origin | US | Shan Serafin |

### Zero (number, 5 facts)

Wikidata: [Q8025310](https://www.wikidata.org/wiki/Q8025310) (Add-on to Flight Simulator 2004; from Wikipedia article 'Wings of Power II: WWII Fighters')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| Zero | participated in conflict | WWII | Wings of Power II: WWII Fighters |
| Zero | participated in conflict | World War 2 | Brewster F2A Buffalo |
| Zero | participated in conflict | World War II | Jiro Horikoshi |
| Zero | participated in conflict | Second World War | 1944: The Loop Master |
| Zero | participated in conflict | II | Wings of Power II: WWII Fighters |

### Themselves (stopword, 6 facts)

Wikidata: [Q2416781](https://www.wikidata.org/wiki/Q2416781) (American hip-hop group; from Wikipedia article 'Themselves')

| Subject | Relation | Object | Wikipedia article |
|---|---|---|---|
| Themselves | record label | Anticon | Themselves |
| Themselves | country of origin | US | Too Big to Fail (book) |
| Themselves | country of origin | American | The Free Houdini |
| Themselves | genre | underground hip hop | Themselves |
| Themselves | genre | indie hip hop | 13 & God |
| Themselves | has part(s) | Doseone | Soft Skulls |

## Generic words reported but kept

One-word names written in lower case in at least 1% of the base's Wikipedia sentences, or all-caps short names. Kept: on T-REx they are Wikidata concepts that are real answers (occupation, position, genre).

| Name | Facts | Wikidata | Example fact |
|---|---|---|---|
| footballer | 22,242 | [Q7328517](https://www.wikidata.org/wiki/Q7328517) (English footballer; from Wikipedia article 'Richard Prokas') | India / sport / footballer |
| football | 19,661 | [Q7927464](https://www.wikidata.org/wiki/Q7927464) (College football rivalry game; from Wikipedia article 'Victory Bell (Cincinnati–Miami)') | United States / sport / football |
| politician | 11,475 | [Q4859203](https://www.wikidata.org/wiki/Q4859203) (American politician (born 1948); from Wikipedia article 'Barbara Osborn Kreamer') | politician / country / American |
| actor | 7,517 | no Wikidata match by label | Mohanlal / occupation / actor |
| defender | 7,256 | no Wikidata match by label | United States / sport / defender |
| midfielder | 6,055 | no Wikidata match by label | India / sport / midfielder |
| striker | 5,989 | no Wikidata match by label | United States / sport / striker |
| goalkeeper | 5,763 | no Wikidata match by label | goalkeeper / country of origin / English |
| actress | 5,670 | no Wikidata match by label | actress / country / French |
| composer | 5,667 | no Wikidata match by label | Manitoba / occupation / composer |
| village | 3,895 | no Wikidata match by label | village / country / US |
| comune | 3,853 | no Wikidata match by label | comune / country / Italy |
| river | 3,504 | no Wikidata match by label | river / country / United States |
| poet | 3,281 | no Wikidata match by label | Latin / subclass of / poet |
| journalist | 3,133 | no Wikidata match by label | journalist / place of birth / Iraq |
| soccer | 2,722 | no Wikidata match by label | soccer / country of origin / English |
| jazz | 2,331 | no Wikidata match by label | Columbia / genre / jazz |
| municipality | 2,240 | no Wikidata match by label | municipality / country / Germany |
| basketball | 2,174 | no Wikidata match by label | USA / sport / basketball |
| songwriter | 1,751 | no Wikidata match by label | songwriter / country / American |
| species | 1,328 | no Wikidata match by label | Buffalo / taxon rank / species |
| rock | 1,161 | no Wikidata match by label | RCA Records / genre / rock |
| international | 673 | no Wikidata match by label | Munich / instance of / international |
| OR | 62 | no Wikidata match by label | OR / country / US |
| IN | 61 | no Wikidata match by label | US / contains the administrative territorial entity / IN |
| UP | 59 | no Wikidata match by label | UP / shares border with / Chhattisgarh |
| CAN | 41 | no Wikidata match by label | CAN / contains the administrative territorial entity / Quebec |
| MI | 34 | no Wikidata match by label | MI / country / USA |
| AT | 33 | no Wikidata match by label | Slovenia / shares border with / AT |
| BE | 32 | no Wikidata match by label | Brussels / country / BE |
| DE | 25 | no Wikidata match by label | DE / located in the administrative territorial entity / USA |
| ON | 25 | no Wikidata match by label | Manitoba / shares border with / ON |
| census | 16 | no Wikidata match by label | Asian / instance of / census |
| AS | 13 | no Wikidata match by label | AS / country / Australia |
| TO | 12 | no Wikidata match by label | Vinovo / located in the administrative territorial entity / TO |
| Debut | 8 | no Wikidata match by label | Debut / genre / jazz |
| AND | 7 | no Wikidata match by label | AND / subclass of / OR |
| HOME | 6 | no Wikidata match by label | HOME / located in the administrative territorial entity / American |
| ICE | 5 | no Wikidata match by label | ICE / country / Germany |
| Winning | 5 | no Wikidata match by label | Winning / cast member / Paul Newman |
| NOW | 4 | no Wikidata match by label | NOW / headquarters location / Chicago |
| SET | 4 | no Wikidata match by label | SET / headquarters location / Bangkok |
| BEST | 3 | no Wikidata match by label | BEST / headquarters location / Bombay |
| SIDE | 3 | no Wikidata match by label | SIDE / country / Argentine Republic |
| IS | 3 | no Wikidata match by label | IS / participated in conflict / World War II |
| THE | 2 | no Wikidata match by label | THE / instance of / Operating System |
| TIME | 2 | [Q43297](https://www.wikidata.org/wiki/Q43297) (American news magazine and website; from Wikipedia article 'Time (magazine)') | TIME / headquarters location / NYC |

## The first, too-wide run (never used)

The first rule also dropped every generic word and every stopword-shaped name, all-caps included. It would have removed 118 entities and 130,033 base facts ({'generic': 129452, 'stopword': 504, 'number': 101}), plus 1,331 orphaned entities: facts 1,215,416 -> 1,085,383. Almost all of it hung on real answers. It was caught before any run used it; its files are kept as *_clean_v1_too_wide*.

| Name | Category | Facts |
|---|---|---|
| footballer | generic | 22,242 |
| football | generic | 19,661 |
| politician | generic | 11,475 |
| actor | generic | 7,517 |
| defender | generic | 7,256 |
| midfielder | generic | 6,055 |
| striker | generic | 5,989 |
| goalkeeper | generic | 5,763 |
| actress | generic | 5,670 |
| composer | generic | 5,667 |
| village | generic | 3,895 |
| comune | generic | 3,853 |
| river | generic | 3,504 |
| poet | generic | 3,281 |
| journalist | generic | 3,133 |
| soccer | generic | 2,722 |
| jazz | generic | 2,331 |
| municipality | generic | 2,240 |
| basketball | generic | 2,174 |
| songwriter | generic | 1,751 |
| species | generic | 1,328 |
| rock | generic | 1,161 |
| international | generic | 673 |
| OR | stopword | 62 |
| IN | stopword | 61 |
| UP | stopword | 59 |
| CAN | stopword | 41 |
| MI | generic | 34 |
| NO | stopword | 33 |
| AT | stopword | 33 |
| BE | stopword | 32 |
| Ain | stopword | 31 |
| DE | generic | 25 |
| ON | stopword | 25 |
| AM | stopword | 22 |
| Don | stopword | 21 |
| census | generic | 16 |
| AS | stopword | 13 |
| TO | stopword | 12 |
| SO | stopword | 11 |
