import { useState } from 'react';
import {
  Box, Typography, TextField, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, Chip, LinearProgress,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { api } from '../api/client';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await api.post('/knowledge/search', { query, limit: 20 });
      setResults(data);
    } catch (e) {
      setResults({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Semantic Search</Typography>
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          fullWidth size="small" placeholder="Search knowledge base..."
          value={query} onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <Button variant="contained" startIcon={<SearchIcon />} onClick={handleSearch} disabled={loading}>
          Search
        </Button>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {results?.error && (
        <Typography color="error">{results.error}</Typography>
      )}

      {results?.results && (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {results.results.length} results ({results.total_embeddings} items indexed)
          </Typography>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Score</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>ID</TableCell>
                  <TableCell>Info</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {results.results.map((r, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <Chip label={r.similarity.toFixed(3)} size="small"
                        color={r.similarity > 0.7 ? 'success' : r.similarity > 0.4 ? 'warning' : 'default'} />
                    </TableCell>
                    <TableCell><Chip label={r.source_type} size="small" variant="outlined" /></TableCell>
                    <TableCell>{r.source_id}</TableCell>
                    <TableCell>{r.metadata?.title || r.metadata?.summary || '-'}</TableCell>
                  </TableRow>
                ))}
                {results.results.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} align="center">No results found</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Box>
  );
}
