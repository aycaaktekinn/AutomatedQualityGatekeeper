// Same bands as backend/app/scoring.py (FR-07).
const BANDS: [number, string][] = [[90, 'A'], [75, 'B'], [60, 'C'], [40, 'D'], [0, 'E']]

export function gradeFor(score: number | null): string | null {
  if (score === null) return null
  return BANDS.find(([threshold]) => score >= threshold)?.[1] ?? 'E'
}

export function gradeClass(grade: string | null): string {
  return grade ? `g-${grade.toLowerCase()}` : 'g-none'
}
