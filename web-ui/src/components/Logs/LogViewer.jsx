import { useEffect, useRef, useState } from 'react';
import { Box, Paper, Typography, Switch, FormControlLabel, TextField } from '@mui/material';

const LEVEL_COLORS = {
  INFO: '#333',
  ERROR: '#d32f2f',
  LLM: '#1565c0',
  GATE: '#f57c00',
};

function LogLine({ entry }) {
  const color = LEVEL_COLORS[entry.level] || '#333';
  return (
    <Box sx={{ fontFamily: 'monospace', fontSize: 13, py: 0.2, color, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
      <span style={{ opacity: 0.5 }}>{entry.timestamp?.slice(11, 23)}</span>
      {' '}
      <span style={{ fontWeight: 600 }}>[{entry.level}]</span>
      {' '}
      {entry.message}
    </Box>
  );
}

export default function LogViewer({ logs }) {
  const bottomRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, autoScroll]);

  const filtered = filter
    ? logs.filter((l) => l.message?.toLowerCase().includes(filter.toLowerCase()) || l.level === filter.toUpperCase())
    : logs;

  return (
    <Paper variant="outlined" sx={{ p: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle2">Logs ({logs.length} lines)</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <TextField size="small" placeholder="Filter..." value={filter} onChange={(e) => setFilter(e.target.value)} sx={{ width: 150 }} />
          <FormControlLabel control={<Switch checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} size="small" />} label="Auto-scroll" />
        </Box>
      </Box>
      <Box sx={{ maxHeight: 400, overflow: 'auto', bgcolor: '#fafafa', p: 1, borderRadius: 1 }}>
        {filtered.length === 0 && <Typography color="text.secondary" sx={{ fontStyle: 'italic' }}>No logs yet</Typography>}
        {filtered.map((entry, i) => <LogLine key={i} entry={entry} />)}
        <div ref={bottomRef} />
      </Box>
    </Paper>
  );
}
