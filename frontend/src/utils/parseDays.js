export function parseDays(text, totalDays) {
  const splitRegex = /(?=^(?:#{1,3}\s*|\*{0,2})Day\s+\d+\b)/gim;
  const parts = text.split(splitRegex).filter(p => p.trim());

  const days = [];
  const seen = new Set();

  for (const part of parts) {
    const match = part.match(/^(?:#{1,3}\s*|\*{0,2})Day\s+(\d+)\b/im);
    if (match) {
      const dayNumber = parseInt(match[1], 10);
      if (dayNumber >= 1 && dayNumber <= totalDays && !seen.has(dayNumber)) {
        seen.add(dayNumber);
        days.push({ dayNumber, content: part.trim(), loading: false, comment: "" });
      }
    }
  }

  days.sort((a, b) => a.dayNumber - b.dayNumber);

  if (days.length === 0 && text.trim()) {
    return [{ dayNumber: 1, content: text.trim(), loading: true, comment: "" }];
  }

  return days;
}