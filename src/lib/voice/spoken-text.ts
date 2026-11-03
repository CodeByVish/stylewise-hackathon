/** Keep complete decision-bearing sentences; never cut an ownership condition mid-sentence. */
export function briefSpokenReply(text: string) {
  const sentences = text.replace(/\r/g, "").replace(/\n+/g, " ")
    .split(/(?<=[.!?])\s+(?=[A-Z"'“])/)
    .map(sentence => sentence.trim())
    .filter(sentence => sentence && !/^All offers are simulated\.?$/i.test(sentence));
  if (sentences.length <= 3 && text.split(/\s+/).length <= 65) return sentences.join(" ");

  // A confirmation question changes the next turn. Keep the outcome that gives it
  // meaning, then ask exactly that question. This avoids a long answer that asks
  // for confirmation and a budget at the same time.
  const confirmationIndex = sentences.findIndex(sentence =>
    /\b(?:need|needs) (?:to )?(?:confirm|check)|\bneeds? (?:review|checking|confirm)|\bstill have\b/i.test(sentence),
  );
  if (confirmationIndex >= 0) {
    const outcome = sentences.slice(0, confirmationIndex).find(sentence =>
      /\b(?:all set|work beautifully|works? together|already have|no shopping)\b/i.test(sentence),
    );
    const confirmation = sentences[confirmationIndex];
    const followUp = sentences.slice(confirmationIndex + 1).find(sentence => /\?/.test(sentence));
    return [outcome, confirmation, followUp]
      .filter((sentence, index, list): sentence is string => Boolean(sentence) && list.indexOf(sentence) === index)
      .join(" ");
  }
  const ranked = sentences.map((sentence, index) => {
    let score = 10;
    if (/^I went through your closet|^It (?:works with|creates)|^I picked it over/i.test(sentence)) score = 0;
    if (/\bSGD\s*\d|\b(?:buy|pick|recommend|already have everything|no shopping)\b/i.test(sentence)) score = 60;
    if (/\b(?:can't|cannot|couldn't|isn't verified|not verified|needs? (?:review|checking|confirm)|unless|if you still|if you do|might not|may not)\b/i.test(sentence)) score = 90;
    if (/\?/.test(sentence)) score = 100;
    if (/^Got it:/i.test(sentence)) score = 5;
    return {sentence, index, score};
  }).sort((a, b) => b.score - a.score || a.index - b.index);
  const selected: typeof ranked = [];
  let words = 0;
  for (const candidate of ranked) {
    const count = candidate.sentence.split(/\s+/).length;
    // Safety/clarifying sentences may exceed the soft limit; keep their full condition.
    if (selected.length < 3 && (words + count <= 65 || candidate.score >= 90 || !selected.length)) {
      selected.push(candidate); words += count;
    }
  }
  return selected.sort((a, b) => a.index - b.index).map(item => item.sentence).join(" ");
}

/** Fit replies are full of symbols a voice reads badly: say them as words. */
function speakFitTerms(text: string) {
  return text
    .replace(/±\s*(\d+(?:\.\d+)?)/g, "plus or minus $1")
    .replace(/(^|[\s(])\+(\d)/g, "$1plus $2")
    .replace(/(^|[\s(])[-−](\d)/g, "$1minus $2")
    .replace(/(\d)\s*cm\b/g, "$1 centimetres")
    .replace(/(\d)\s*in\b(?!\s+\w+ing)/g, "$1 inches")
    .replace(/\b(XS|S|M|L|XL)\s*\/\s*(?=(XS|S|M|L|XL)\b)/g, "$1, ")
    .replace(/\b([23])XL\b/g, "$1 X L").replace(/\bXXL\b/g, "double X L").replace(/\bXL\b/g, "X L").replace(/\bXS\b/g, "X S");
}

/** Sentence-sized pieces (never cut mid-sentence), so the voice keeps its rhythm and pauses. */
export function speechPieces(text: string, max = 220) {
  // a sentence ends at . ! ? followed by a space or the end, so decimals like "2.5" stay whole
  const sentences = text.match(/.+?(?:[.!?]+["')]*(?=\s|$)|$)/g) || [text];
  const pieces: string[] = [];
  for (const raw of sentences) {
    const sentence = raw.trim();
    if (!sentence) continue;
    const last = pieces[pieces.length - 1];
    if (last && last.length + sentence.length + 1 <= max) pieces[pieces.length - 1] = `${last} ${sentence}`;
    else if (sentence.length <= max) pieces.push(sentence);
    else pieces.push(...(sentence.match(new RegExp(`.{1,${max}}(?:,\\s|\\s|$)`, "g")) || [sentence]).map(part => part.trim()));
  }
  return pieces.length ? pieces : [text];
}

/** Plain speech punctuation, avoiding report labels and awkward stacked pauses. */
export function normalizeSpokenText(text: string) {
  return speakFitTerms(text)
    .replace(/\[\[[\s\S]*?\]\]/g, "")
    .replace(/\*\*|__|`/g, "")
    .replace(/(?:^|\n)\s*[-*•]\s+/g, "")
    .replace(/[“”]/g, '"').replace(/[‘’]/g, "'")
    .replace(/\bNEEDS_REVIEW\b/g, "needs your confirmation")
    .replace(/\bINFEASIBLE\b/g, "does not meet your requirements")
    .replace(/\bFEASIBLE\b/g, "meets your requirements")
    .replace(/\s+[+＆]\s+/g, " with ")
    .replace(/[;]+/g, ". ")
    .replace(/\s*[—–]\s*/g, ", ")
    .replace(/[:()]/g, ", ")
    .replace(/\.{2,}/g, ".")
    .replace(/,\s*[,\.]/g, ".")
    .replace(/\s+([,.!?])/g, "$1")
    .replace(/\s+/g, " ").trim();
}
