# Why the full T-REx base halved accuracy

Test 04 run-02, GOAt pass, repeat 0 (17 right of 100), compared with the empty-start graph (test 05 arm A, repeat 0, 35 right).
Script: `why_accuracy_halved.py <dir with goat0/scored.jsonl, goat0/task.json> <arm A repeat_0/scored.jsonl>`; the 10 questions with
every fact are in `ten_failed_questions.json`. A fact is from T-REx when its source is `chunk -1`.

## What reached Haiku

| | T-REx facts | Document facts | Characters, T-REx : documents |
|---|---|---|---|
| 83 wrong questions, mean of the 50 slots | 33.3 | 15.7 | about 6 : 1 |
| 17 right questions | 34.5 | 15.5 | |

T-REx facts are whole Wikipedia sentences (about 400 characters each), document facts are one short line. 449 of the 4,074
slots on wrong questions were the same T-REx sentence repeated (one sentence backs several triples).

## The guess, checked

The guess: FactConsolidation edits facts on purpose, so real-world T-REx facts contradict the documents and crowd them out.
Mostly right, but crowding out is the main effect. Direct contradiction is the smaller one.

- **Crowding out (7 of 10):** T-REx takes two thirds of the slots, so the edited, newest document fact on the chain is dropped.
  Then Haiku has only the older document fact or nothing. Its answer then falls back on the real world.
- **A T-REx fact contradicts the gold (2 of 10):** q4, the T-REx sentence on the Valmiki Ramayana says Sanskrit, and Haiku
  answers Sanskrit (gold English). q21, the full document chain is there (Gustav Vigeland, Finland, Asia), but T-REx sentences
  about Finnish regions are around it, and Haiku answers Europe.
- **Real-world prior, no T-REx fact involved (1 of 10):** q49, both document facts are there (A. A. Milne born in London, serial 232;
  born in Lüftelberg, serial 9990). Haiku picks London, the real one and the older one.

Over all 83 wrong answers: the wrong answer appears only in a T-REx fact for 9, in a document fact for 11, and in neither for 63
(refusals like "the pool does not say", or answers from Haiku's own knowledge).

## The 10 questions (wrong on T-REx, right on the empty-start graph)

| q | Question (short) | Gold | Answer on T-REx | T-REx / doc facts | Gold in pool | What went wrong |
|---|---|---|---|---|---|---|
| 3 | origin of the broadcaster of Your Hit Parade | Paris | New York City | 16 / 34 | yes | NBC's edited headquarters fact dropped; real-world answer |
| 4 | language Valmiki wrote in | English | Sanskrit | 49 / 1 | yes | T-REx sentence says Sanskrit: contradiction |
| 12 | head office of the broadcaster of Adventures in Paradise | Knoxville | California | 44 / 6 | no | only ABC's older headquarters fact left |
| 14 | continent of Fernando Lugo's citizenship | Oceania | (United Kingdom, no continent) | 47 / 3 | no | the United Kingdom continent fact dropped |
| 21 | continent of Gustav Vigeland's citizenship | Asia | Europe | 44 / 6 | yes | chain present, T-REx Finland sentences around it: contradiction |
| 29 | place of death of the author of Carmilla | New York City | Dublin | 47 / 3 | no | the edited author's (Joseph Stein) death fact dropped; the older Le Fanu fact used |
| 37 | founder of Gabriel Narutowicz's religion | Gérard Blitz | refused | 3 / 47 | no | the founder fact dropped (47 Catholic Church facts filled the slots) |
| 49 | birthplace of the creator of Indiana Jones | Lüftelberg | London | 26 / 24 | yes | both versions present; Haiku picked the real, older one |
| 50 | head of the company that makes the Chevrolet Chevelle | David Potts | refused | 43 / 7 | no | the producer fact dropped |
| 59 | birthplace of the Illinois Attorney General | Higashiyamanashi District, Yamanashi | Chicago, Illinois | 49 / 1 | no | the whole chain dropped; real-world answer |

19 questions are wrong on T-REx but right on the empty-start graph (repeat 0): 3, 4, 12, 14, 21, 29, 37, 49, 50, 59, 60, 66, 70, 81,
83, 85, 86, 95, 97. The table shows the first 10.
