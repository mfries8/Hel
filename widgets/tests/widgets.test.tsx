import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  Alert,
  Button,
  Caption,
  Checkbox,
  DataTable,
  Dialog,
  Divider,
  Expander,
  FileDrop,
  Header,
  Messages,
  Metric,
  NumberInput,
  Progress,
  Radio,
  Select,
  Slider,
  Spinner,
  StatusPill,
  Subheader,
  Tabs,
  TextInput,
  Toasts,
  renderInline,
} from '../src';

afterEach(cleanup);

describe('text', () => {
  it('renders inline markup', () => {
    render(<Caption>{'**bold**, _italic_, `code` and [a link](https://example.org)'}</Caption>);
    expect(screen.getByText('bold').tagName).toBe('STRONG');
    expect(screen.getByText('italic').tagName).toBe('EM');
    expect(screen.getByText('code').tagName).toBe('CODE');
    expect(screen.getByRole('link', { name: 'a link' })).toHaveProperty('href', 'https://example.org/');
  });

  it('leaves snake_case words alone', () => {
    const { container } = render(<div>{renderInline('analysis_mode and full_parameter_refinement')}</div>);
    expect(container.querySelector('em')).toBeNull();
  });

  it('renders headings, divider, metric, spinner and pill', () => {
    render(
      <>
        <Header>Run</Header>
        <Subheader>Inputs</Subheader>
        <Divider />
        <Metric label="Radar mass" value="9,980 kg" help="Sum over valid blips" />
        <Spinner text="Fitting" />
        <StatusPill tone="success">completed</StatusPill>
      </>,
    );
    expect(screen.getByRole('heading', { level: 2, name: 'Run' })).toBeTruthy();
    expect(screen.getByRole('heading', { level: 3, name: 'Inputs' })).toBeTruthy();
    expect(screen.getByText('9,980 kg')).toBeTruthy();
    expect(screen.getByLabelText('Sum over valid blips')).toBeTruthy();
    expect(screen.getByText('Fitting')).toBeTruthy();
    expect(screen.getByText('completed').className).toContain('hel-pill-success');
  });
});

describe('alerts', () => {
  it('announces errors and lists messages', () => {
    render(
      <>
        <Alert level="error">Failed</Alert>
        <Messages messages={[{ level: 'warning', text: 'Check winds' }, { level: 'info', text: 'Note' }]} />
      </>,
    );
    expect(screen.getByRole('alert').textContent).toContain('Failed');
    expect(screen.getAllByRole('status')).toHaveLength(2);
  });
});

describe('inputs', () => {
  it('reports radio, select, text, checkbox and slider changes', () => {
    const changes = vi.fn();
    render(
      <>
        <Radio label="Mode" options={['simple', 'full']} value="simple" onChange={changes} horizontal />
        <Select
          label="Wind source"
          options={[
            { value: 'era5', label: 'ERA5' },
            { value: 'raob', label: 'Rawinsonde' },
          ]}
          value="era5"
          onChange={changes}
        />
        <TextInput label="Fall folder" value="" onChange={changes} />
        <Checkbox label="Offline" checked={false} onChange={changes} />
        <Slider label="Multiple" min={1} max={5} value={1} onChange={changes} format={(v) => `${v}x`} />
      </>,
    );
    fireEvent.click(screen.getByLabelText('full'));
    fireEvent.change(screen.getByLabelText('Wind source'), { target: { value: 'raob' } });
    fireEvent.change(screen.getByLabelText('Fall folder'), { target: { value: 'C:/falls/PF' } });
    fireEvent.click(screen.getByLabelText('Offline'));
    fireEvent.change(screen.getByLabelText('Multiple'), { target: { value: '3' } });
    expect(changes.mock.calls).toEqual([['full'], ['raob'], ['C:/falls/PF'], [true], [3]]);
    expect(screen.getByText('5x')).toBeTruthy();
  });

  it('keeps a number being typed and reports it', () => {
    function Harness({ onValue }: { onValue: (v: number | null) => void }) {
      const [value, setValue] = useState<number | null>(3400);
      return (
        <NumberInput
          label="Density"
          unit="kg/m³"
          min={1000}
          max={8000}
          value={value}
          onChange={(v) => {
            setValue(v);
            onValue(v);
          }}
        />
      );
    }
    const seen = vi.fn();
    render(<Harness onValue={seen} />);
    const input = screen.getByLabelText('Density (kg/m³)') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '-' } });
    expect(input.value).toBe('-');
    expect(screen.getByText('Enter a number.')).toBeTruthy();
    fireEvent.change(input, { target: { value: '9000' } });
    expect(screen.getByText('Allowed range: 1000 to 8000 kg/m³.')).toBeTruthy();
    fireEvent.change(input, { target: { value: '3500.0' } });
    expect(input.value).toBe('3500.0');
    expect(seen.mock.calls).toEqual([[null], [9000], [3500]]);
  });

  it('accepts a dropped file of an allowed type only', () => {
    const changes = vi.fn();
    render(<FileDrop label="Radar export" accept={['.json']} file={null} onChange={changes} />);
    const input = screen.getByTestId('hel-file-input');
    fireEvent.change(input, { target: { files: [new File(['x'], 'notes.txt')] } });
    fireEvent.change(input, { target: { files: [new File(['{}'], 'RADAR_KDTX.json')] } });
    expect(changes).toHaveBeenCalledTimes(1);
    expect((changes.mock.calls[0][0] as File).name).toBe('RADAR_KDTX.json');
    expect(screen.getByText('JSON')).toBeTruthy();
  });

  it('shows the chosen file and removes it', () => {
    const changes = vi.fn();
    render(<FileDrop label="Radar export" file={new File(['12345'], 'radar.json')} onChange={changes} />);
    expect(screen.getByText('radar.json')).toBeTruthy();
    expect(screen.getByText('5B')).toBeTruthy();
    fireEvent.click(screen.getByLabelText('Remove file'));
    expect(changes).toHaveBeenCalledWith(null);
  });
});

describe('buttons, progress, tables', () => {
  it('clicks, and not when disabled', () => {
    const click = vi.fn();
    render(
      <>
        <Button kind="primary" onClick={click}>
          Run
        </Button>
        <Button onClick={click} disabled>
          Stop
        </Button>
      </>,
    );
    fireEvent.click(screen.getByText('Run'));
    fireEvent.click(screen.getByText('Stop'));
    expect(click).toHaveBeenCalledTimes(1);
  });

  it('clamps progress', () => {
    render(<Progress value={1.7} label="Fit" />);
    expect(screen.getByRole('progressbar', { name: 'Fit' }).getAttribute('aria-valuenow')).toBe('100');
  });

  it('renders a table', () => {
    render(<DataTable columns={['Blip', 'Mass']} rows={[['KDTX_5_0', '18.8 g']]} />);
    expect(screen.getByRole('columnheader', { name: 'Mass' })).toBeTruthy();
    expect(screen.getByRole('cell', { name: '18.8 g' })).toBeTruthy();
  });
});

describe('tabs, expander, dialog, toasts', () => {
  it('switches tabs and skips disabled ones', () => {
    const change = vi.fn();
    render(
      <Tabs
        label="Results"
        active="map"
        onChange={change}
        tabs={[
          { id: 'map', label: 'Search Map' },
          { id: 'masses', label: 'Masses' },
          { id: 'plots', label: 'Plots', disabled: true },
        ]}
      />,
    );
    expect(screen.getByRole('tab', { name: 'Search Map' }).getAttribute('aria-selected')).toBe('true');
    fireEvent.click(screen.getByRole('tab', { name: 'Masses' }));
    fireEvent.click(screen.getByRole('tab', { name: 'Plots' }));
    expect(change.mock.calls).toEqual([['masses']]);
  });

  it('opens and closes an expander', () => {
    render(
      <Expander title="Search ranges">
        <span>ranges</span>
      </Expander>,
    );
    expect(screen.queryByText('ranges')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Search ranges' }));
    expect(screen.getByText('ranges')).toBeTruthy();
  });

  it('closes a dialog by button, Escape and backdrop', () => {
    const close = vi.fn();
    render(
      <Dialog title="Choose the anchor blip" onClose={close}>
        <p>question</p>
      </Dialog>,
    );
    expect(screen.getByRole('dialog', { name: 'Choose the anchor blip' })).toBeTruthy();
    fireEvent.mouseDown(screen.getByText('question'));
    expect(close).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText('Close'));
    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    fireEvent.mouseDown(document.querySelector('.modal-backdrop') as Element);
    expect(close).toHaveBeenCalledTimes(3);
  });

  it('shows toasts', () => {
    render(<Toasts toasts={[{ id: 1, text: 'Run completed', icon: '✓' }]} />);
    expect(screen.getByText('Run completed')).toBeTruthy();
  });
});
