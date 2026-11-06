# The rules

What Juleep checks after the cleanup model replies, in the order it checks them. Each rule produces a reason that History shows under a held-back take, and a hint that is added to the prompt for the one retry.

Words are compared after lowercasing and stripping punctuation from word ends, so "Don't," and "don't" are the same word.

## 1. Format

The reply must be plain text. A reply that starts like JSON (`{`, `[`), a code fence (```` ``` ````) or a tag (`<`) is markup, not a sentence, and is rejected.
*Hint:* "Reply with the tidied sentence as plain text, never as JSON, a code block or tags."

## 2. Self-corrections

When the raw transcript contains a correction marker ("no", "no wait", "actually", "sorry", "I mean") followed by more words, the first real word after the marker is what the speaker meant and must appear in the reply. Small models like to keep the first version instead.
*Example:* "move the review to thursday no friday at three" must keep "friday".
*Hint:* "The speaker corrected themselves; keep 'friday', the version after the correction."

## 3. Negations

Count the negation words in the raw text and in the reply; they must match. Counted words: not, never, none, nothing, nobody, neither, nor, without, and every `n't` contraction; "cannot" and "can not" count as "not". Bare "no" is not counted, because in speech it is mostly a correction marker (rule 2) or filler.
*Example:* "meet me at 3pm not 4" → a reply of "Meet me at 4pm." is rejected.
*Hint:* "Your previous reply dropped the word 'not'. Keep it exactly as said."

## 4. Numbers

Every number in the raw text must appear in the reply, as a value. Digit runs count ("1,000" is 1000, "3pm" is 3), composed number words count ("twenty five" and "twenty-five" are 25, "two thousand twenty six" is 2026), in English and Lithuanian. Writing a number word as digits or the reverse is allowed; changing the value is not.
*Example:* "the quarterly number is forty two percent not forty" must keep 42 and 40.
*Hint:* "Your previous reply changed a number. Keep '42' exactly as said."

## 5. Protected tokens

Two kinds of token must appear in the reply exactly, case-sensitive, on a word boundary:

- words from the user's dictionary that were said (and they must come out spelled as the dictionary has them);
- anything in the raw text that looks like code: contains `_`, a `/`, a `.` or `-` between letters or digits, camelCase, ALLCAPS of two or more letters, or letters mixed with digits (`v3`, `utf8`), but not digit-first tokens like `3pm`.

*Example:* "rename loadTakes to fetchTakes in src/api.ts" must keep `loadTakes`, `fetchTakes` and `src/api.ts`.
*Hint:* "Your previous reply changed 'loadTakes'. Keep it exactly as said."

## 6. Rewrite limit

A word-level diff between the raw text and the reply is computed in code. If more than 60% of the raw words were changed, the reply is a rewrite (an answer to the sentence, an invention or a translation), not a tidy-up, and is rejected.
*Hint:* "Tidy the sentence; do not rewrite, answer or translate it."

## What happens next

A reply that passes is typed. A reply that fails gets one retry with the hint appended to the prompt. If the retry fails too, the raw transcript is typed instead (with the user's dictionary spellings applied), and History shows the take with the reason, for example "Typed as said. Cleanup would have dropped 'not'."

## Known gaps

- Dates and ordinals are not treated as numbers ("the tenth" is a word).
- Negation counting is per word, not per clause: a reply that moves a "not" to a different clause passes.
- Polish and German number words are not yet in the list, so in those languages only digits are protected by rule 4; rule 6 still limits rewrites.
