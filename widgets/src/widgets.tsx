// The Yggdrasil suite's shared widgets (Hel H-002). Styles: hel-widgets.css.
// Each component is small and controlled: the app owns the state and passes
// the value and an onChange handler.

import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  CloudUpload,
  Info,
  Loader2,
  X,
  XCircle,
} from 'lucide-react';
import { renderInline } from './inline';

/** Severity of an alert or message. */
export type Level = 'info' | 'success' | 'warning' | 'error';

/** A message for an alert list. */
export interface Message {
  level: Level;
  text: string;
}

const textContent = (children: ReactNode): ReactNode =>
  typeof children === 'string' ? renderInline(children) : children;

/** A section heading. */
export function Header({ children }: { children: ReactNode }) {
  return <h2 className="hel-header">{children}</h2>;
}

/** A sub-section heading. */
export function Subheader({ children }: { children: ReactNode }) {
  return <h3 className="hel-subheader">{children}</h3>;
}

/** Small, muted explanatory text (inline markup allowed). */
export function Caption({ children }: { children: ReactNode }) {
  return <div className="hel-caption">{textContent(children)}</div>;
}

/** A horizontal rule. */
export function Divider() {
  return <hr className="hel-divider" />;
}

const ALERT_ICONS: Record<Level, ReactNode> = {
  info: <Info size={16} />,
  success: <CheckCircle2 size={16} />,
  warning: <AlertTriangle size={16} />,
  error: <XCircle size={16} />,
};

/** A coloured message box; errors are announced to screen readers. */
export function Alert({ level, children }: { level: Level; children: ReactNode }) {
  return (
    <div className={`hel-alert hel-alert-${level}`} role={level === 'error' ? 'alert' : 'status'}>
      <span className="hel-alert-icon">{ALERT_ICONS[level]}</span>
      <div>{textContent(children)}</div>
    </div>
  );
}

/** A list of alerts. */
export function Messages({ messages }: { messages: Message[] }) {
  return (
    <>
      {messages.map((m, i) => (
        <Alert key={i} level={m.level}>
          {m.text}
        </Alert>
      ))}
    </>
  );
}

/** A spinning indicator with a label. */
export function Spinner({ text }: { text: string }) {
  return (
    <div className="hel-spinner" role="status">
      <Loader2 size={16} className="spin" />
      <span>{text}</span>
    </div>
  );
}

/** A question-mark icon showing help text on hover. */
export function Help({ text }: { text: string }) {
  return (
    <span className="hel-help" title={text} aria-label={text}>
      <CircleHelp size={14} />
    </span>
  );
}

function Label({ text, htmlFor, help }: { text: string; htmlFor?: string; help?: string }) {
  return (
    <label className="hel-label" htmlFor={htmlFor}>
      {text}
      {help && <Help text={help} />}
    </label>
  );
}

/** A labelled value, large. */
export function Metric({ label, value, help }: { label: string; value: ReactNode; help?: string }) {
  return (
    <div className="hel-metric">
      <div className="hel-metric-label">
        {label}
        {help && <Help text={help} />}
      </div>
      <div className="hel-metric-value">{value}</div>
    </div>
  );
}

/** One choice among a few options, all visible. */
export function Radio({
  label,
  options,
  value,
  onChange,
  horizontal = false,
  hideLabel = false,
}: {
  label: string;
  options: { value: string; label: string }[] | string[];
  value: string;
  onChange: (v: string) => void;
  horizontal?: boolean;
  hideLabel?: boolean;
}) {
  const name = useId();
  const items = options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o));
  return (
    <div className="hel-widget" role="radiogroup" aria-label={label}>
      {!hideLabel && <div className="hel-label">{label}</div>}
      <div className={horizontal ? 'hel-radio hel-radio-horizontal' : 'hel-radio'}>
        {items.map((opt) => (
          <label key={opt.value} className="hel-radio-option">
            <input
              type="radio"
              name={name}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
            />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

/** An option of a Select. */
export interface SelectOption {
  value: string;
  label: string;
}

/** One choice from a drop-down list. */
export function Select({
  label,
  options,
  value,
  onChange,
  help,
}: {
  label: string;
  options: SelectOption[];
  value: string;
  onChange: (v: string) => void;
  help?: string;
}) {
  const id = useId();
  return (
    <div className="hel-widget">
      <Label text={label} htmlFor={id} help={help} />
      <select id={id} className="hel-input" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

/** A single line of text. */
export function TextInput({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
  help,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: 'text' | 'password' | 'date';
  help?: string;
}) {
  const id = useId();
  return (
    <div className="hel-widget">
      <Label text={label} htmlFor={id} help={help} />
      <input
        id={id}
        className="hel-input"
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

/**
 * A number, typed. While the text is not a number (empty, or a lone minus
 * sign) it is kept as typed and onChange receives null; a number outside
 * [min, max] is reported but not clamped.
 */
export function NumberInput({
  label,
  value,
  onChange,
  min,
  max,
  step,
  unit,
  help,
  placeholder,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  help?: string;
  placeholder?: string;
}) {
  const id = useId();
  const [text, setText] = useState(value === null ? '' : String(value));
  // Follow the app's value, but keep what is being typed when it already
  // means that value ("1.50" for 1.5) or is not a number yet ("-").
  useEffect(() => {
    setText((current) => {
      const typed = current.trim() === '' ? null : Number(current);
      if (value === null) return typed === null || Number.isNaN(typed) ? current : '';
      return typed === value ? current : String(value);
    });
  }, [value]);
  const parsed = text.trim() === '' ? null : Number(text);
  const invalid = parsed !== null && Number.isNaN(parsed);
  const outside = parsed !== null && !invalid && ((min !== undefined && parsed < min) || (max !== undefined && parsed > max));
  return (
    <div className="hel-widget">
      <Label text={unit ? `${label} (${unit})` : label} htmlFor={id} help={help} />
      <input
        id={id}
        className="hel-input"
        inputMode="decimal"
        value={text}
        placeholder={placeholder}
        aria-invalid={invalid || outside}
        onChange={(e) => {
          setText(e.target.value);
          const next = e.target.value.trim() === '' ? null : Number(e.target.value);
          onChange(next === null || Number.isNaN(next) ? null : next);
        }}
        step={step}
      />
      {(invalid || outside) && (
        <div className="hel-caption" role="status">
          {invalid
            ? 'Enter a number.'
            : `Allowed range: ${min ?? '…'} to ${max ?? '…'}${unit ? ` ${unit}` : ''}.`}
        </div>
      )}
    </div>
  );
}

/** A number on a range, dragged. */
export function Slider({
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
  format = (v) => String(v),
  help,
}: {
  label: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (v: number) => void;
  format?: (v: number) => string;
  help?: string;
}) {
  const id = useId();
  return (
    <div className="hel-widget">
      <Label text={label} htmlFor={id} help={help} />
      <div className="hel-slider-value">{format(value)}</div>
      <input
        id={id}
        className="hel-slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="hel-slider-bounds">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}

/** An on/off choice. */
export function Checkbox({
  label,
  checked,
  onChange,
  help,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  help?: string;
}) {
  return (
    <label className="hel-checkbox">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
      {help && <Help text={help} />}
    </label>
  );
}

/** A button: primary for the main action of a view, secondary otherwise. */
export function Button({
  children,
  onClick,
  kind = 'secondary',
  disabled = false,
  type = 'button',
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  kind?: 'primary' | 'secondary';
  disabled?: boolean;
  type?: 'button' | 'submit';
  title?: string;
}) {
  return (
    <button type={type} className={`hel-button ${kind}`} onClick={onClick} disabled={disabled} title={title}>
      {children}
    </button>
  );
}

function formatBytes(n: number): string {
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)}MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)}KB`;
  return `${n}B`;
}

/**
 * A drop zone with a "Browse files" button. Choosing a file calls onChange
 * at once; the chosen file shows as a removable chip. Files whose names do
 * not end in one of `accept` are ignored.
 */
export function FileDrop({
  label,
  accept,
  file,
  onChange,
  disabled = false,
}: {
  label: string;
  accept?: string[] | null;
  file: File | null;
  onChange: (f: File | null) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const typesText = accept?.length ? accept.map((a) => a.replace('.', '').toUpperCase()).join(', ') : '';

  const pick = (f: File | undefined | null) => {
    if (!f) return;
    if (accept?.length && !accept.some((ext) => f.name.toLowerCase().endsWith(ext))) return;
    onChange(f);
  };

  return (
    <div className="hel-widget">
      <div className="hel-label">{label}</div>
      <div
        className={`hel-dropzone${dragOver ? ' drag-over' : ''}`}
        data-testid="hel-dropzone"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (!disabled) pick(e.dataTransfer.files?.[0]);
        }}
      >
        <CloudUpload size={28} className="hel-dropzone-icon" />
        <div className="hel-dropzone-text">
          <div>Drag and drop file here</div>
          {typesText && <small>{typesText}</small>}
        </div>
        <Button onClick={() => inputRef.current?.click()} disabled={disabled}>
          Browse files
        </Button>
        <input
          ref={inputRef}
          type="file"
          hidden
          data-testid="hel-file-input"
          accept={accept?.join(',') ?? undefined}
          onChange={(e) => {
            pick(e.target.files?.[0]);
            e.target.value = '';
          }}
        />
      </div>
      {file && (
        <div className="hel-file-chip">
          <span className="hel-file-name">{file.name}</span>
          <small>{formatBytes(file.size)}</small>
          <button type="button" className="hel-icon-button" aria-label="Remove file" onClick={() => onChange(null)}>
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

/** A progress bar, value 0 to 1 (clamped). */
export function Progress({ value, label }: { value: number; label?: string }) {
  const fraction = Math.max(0, Math.min(1, value));
  return (
    <div
      className="hel-progress"
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(fraction * 100)}
    >
      <div className="hel-progress-bar" style={{ width: `${fraction * 100}%` }} />
    </div>
  );
}

/**
 * A modal with a title bar and a close button; Escape and a click outside
 * also close it. Rendered into <body>, so a blurred sidebar cannot trap it.
 */
export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return createPortal(
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="modal-box" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-title">
          <h3>{title}</h3>
          <button type="button" className="hel-icon-button" aria-label="Close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}

/** One toast notification. */
export interface ToastItem {
  id: number;
  text: string;
  icon: string;
}

/** Brief notifications in a corner. */
export function Toasts({ toasts }: { toasts: ToastItem[] }) {
  return (
    <div className="hel-toasts" role="status">
      {toasts.map((t) => (
        <div key={t.id} className="hel-toast">
          <span aria-hidden="true">{t.icon}</span>
          <span>{t.text}</span>
        </div>
      ))}
    </div>
  );
}

/** A table of text cells, scrolling sideways when wide. */
export function DataTable({ columns, rows }: { columns: string[]; rows: ReactNode[][] }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** One tab of a Tabs bar. */
export interface TabItem {
  id: string;
  label: string;
  disabled?: boolean;
  title?: string;
}

/** A row of tabs; the app shows the active tab's content. */
export function Tabs({
  tabs,
  active,
  onChange,
  label,
}: {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  label: string;
}) {
  return (
    <div className="hel-tabs" role="tablist" aria-label={label}>
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={t.id === active}
          className={`hel-tab${t.id === active ? ' active' : ''}`}
          disabled={t.disabled}
          title={t.title}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/** A collapsible section. */
export function Expander({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = useId();
  return (
    <section className="hel-expander">
      <button
        type="button"
        className="hel-expander-summary"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {title}
      </button>
      {open && (
        <div className="hel-expander-body" id={bodyId}>
          {children}
        </div>
      )}
    </section>
  );
}

/** Tone of a StatusPill. */
export type PillTone = 'neutral' | 'running' | 'success' | 'warning' | 'error';

/** A small rounded label for a state (e.g. a run's status). */
export function StatusPill({ tone, children }: { tone: PillTone; children: ReactNode }) {
  return <span className={`hel-pill hel-pill-${tone}`}>{children}</span>;
}
