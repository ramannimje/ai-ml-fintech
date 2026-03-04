import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import type { AIChatMessage } from '../../store/chat-store';

function parseInlineMarkdown(text: string): Array<{ kind: 'text' | 'bold' | 'code'; value: string }> {
  const tokens: Array<{ kind: 'text' | 'bold' | 'code'; value: string }> = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  for (const match of text.matchAll(regex)) {
    const full = match[0];
    const start = match.index ?? 0;
    if (start > last) {
      tokens.push({ kind: 'text', value: text.slice(last, start) });
    }
    if (full.startsWith('**')) {
      tokens.push({ kind: 'bold', value: full.slice(2, -2) });
    } else {
      tokens.push({ kind: 'code', value: full.slice(1, -1) });
    }
    last = start + full.length;
  }
  if (last < text.length) {
    tokens.push({ kind: 'text', value: text.slice(last) });
  }
  return tokens;
}

function renderMarkdown(content: string): React.ReactNode {
  const nodes: React.ReactNode[] = [];
  const codeRegex = /```(\w+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let key = 0;
  for (const match of content.matchAll(codeRegex)) {
    const full = match[0];
    const lang = match[1] || 'text';
    const code = match[2] || '';
    const index = match.index ?? 0;
    if (index > lastIndex) {
      nodes.push(
        <div key={`txt-${key++}`} className="space-y-2">
          {renderPlainBlock(content.slice(lastIndex, index), key)}
        </div>,
      );
    }
    nodes.push(
      <pre key={`code-${key++}`} className="overflow-x-auto rounded-xl border p-3 text-xs" style={{ borderColor: 'var(--border-strong)', background: 'color-mix(in srgb, var(--surface-2) 92%, black 8%)' }}>
        <code data-lang={lang}>{code}</code>
      </pre>,
    );
    lastIndex = index + full.length;
  }
  if (lastIndex < content.length) {
    nodes.push(
      <div key={`tail-${key++}`} className="space-y-2">
        {renderPlainBlock(content.slice(lastIndex), key)}
      </div>,
    );
  }
  return nodes;
}

function renderPlainBlock(text: string, keySeed: number): React.ReactNode {
  const lines = text.split('\n');
  const items = lines.filter((line) => line.trim().startsWith('- '));
  const hasList = items.length > 0;
  const paragraphLines = lines.filter((line) => !line.trim().startsWith('- '));
  return (
    <>
      {paragraphLines.map((line, idx) => (
        <p key={`p-${keySeed}-${idx}`} className="whitespace-pre-wrap leading-relaxed">
          {parseInlineMarkdown(line).map((part, j) => {
            if (part.kind === 'bold') return <strong key={`b-${j}`}>{part.value}</strong>;
            if (part.kind === 'code') return <code key={`c-${j}`} className="rounded bg-black/10 px-1 py-0.5 text-[0.85em]">{part.value}</code>;
            return <span key={`t-${j}`}>{part.value}</span>;
          })}
        </p>
      ))}
      {hasList ? (
        <ul className="list-disc space-y-1 pl-5">
          {items.map((line, idx) => (
            <li key={`li-${keySeed}-${idx}`}>{line.trim().slice(2)}</li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

export function ChatMessage({ message }: { message: AIChatMessage }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const rendered = useMemo(() => renderMarkdown(message.content), [message.content]);

  const onCopy = async () => {
    await navigator.clipboard.writeText(message.content).catch(() => undefined);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[88%] rounded-2xl border p-4 text-sm md:max-w-[78%] ${isUser ? 'ml-4' : 'mr-4'}`}
        style={{
          borderColor: isUser ? 'color-mix(in srgb, var(--gold) 40%, var(--border))' : 'var(--border)',
          background: isUser
            ? 'linear-gradient(160deg, color-mix(in srgb, var(--gold) 8%, var(--surface)), var(--surface))'
            : 'var(--surface)',
        }}
      >
        {rendered}
        {!isUser ? (
          <div className="mt-2 flex items-center justify-end">
            <button type="button" onClick={onCopy} className="btn-ghost !px-2 !py-1 !text-[10px] uppercase tracking-[0.12em]">
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        ) : null}
      </div>
    </motion.article>
  );
}

