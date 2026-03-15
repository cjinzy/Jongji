/**
 * Renders text with <mark> segments highlighted.
 * The backend returns highlight strings with <mark>...</mark> tags.
 * Parses safely to avoid XSS — only <mark> tags are rendered as elements.
 */
export function HighlightText({ html }: { html: string }) {
  const parts = html.split(/(<mark>.*?<\/mark>)/g)
  return (
    <span className="[&_mark]:bg-accent/20 [&_mark]:text-accent [&_mark]:rounded-[2px] [&_mark]:px-0.5">
      {parts.map((part, i) => {
        const match = part.match(/^<mark>(.*?)<\/mark>$/)
        if (match) {
          return <mark key={i}>{match[1]}</mark>
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}
