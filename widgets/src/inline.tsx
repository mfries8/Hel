import type { ReactNode } from 'react';

// A small inline-markup renderer for widget text: **bold**, _italic_,
// `code` and [links](url). Not a general Markdown renderer.

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|(?<![A-Za-z0-9])_[^_]+_(?![A-Za-z0-9]))/g;

/** Render a string's inline markup as React nodes. */
export function renderInline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const match of text.matchAll(INLINE)) {
    const token = match[0];
    const index = match.index ?? 0;
    if (index > last) out.push(text.slice(last, index));
    if (token.startsWith('**')) {
      out.push(<strong key={key++}>{renderInline(token.slice(2, -2))}</strong>);
    } else if (token.startsWith('`')) {
      out.push(<code key={key++}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith('[')) {
      const close = token.indexOf('](');
      out.push(
        <a key={key++} href={token.slice(close + 2, -1)} target="_blank" rel="noreferrer">
          {renderInline(token.slice(1, close))}
        </a>,
      );
    } else {
      out.push(<em key={key++}>{renderInline(token.slice(1, -1))}</em>);
    }
    last = index + token.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}
