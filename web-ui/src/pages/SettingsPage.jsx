import { useCallback, useState } from 'react';
import {
  Box, Typography, Button, IconButton, Switch, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, MenuItem, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper, Chip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import usePolling from '../hooks/usePolling';
import { api } from '../api/client';

const PROVIDERS = ['github', 'gitlab', 'bitbucket'];

const EMPTY_FORM = { name: '', url: '', provider: 'github', default_branch: 'main' };

export default function SettingsPage() {
  const { data: repos, refresh } = usePolling(
    useCallback(() => api.get('/repositories'), []),
    10000,
  );

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const openAdd = () => {
    setEditId(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (repo) => {
    setEditId(repo.id);
    setForm({ name: repo.name, url: repo.url, provider: repo.provider, default_branch: repo.default_branch });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (editId) {
      await api.put(`/repositories/${editId}`, form);
    } else {
      await api.post('/repositories', form);
    }
    setDialogOpen(false);
    refresh();
  };

  const handleDelete = async (id) => {
    await api.delete(`/repositories/${id}`);
    setDeleteConfirm(null);
    refresh();
  };

  const handleToggleActive = async (repo) => {
    await api.put(`/repositories/${repo.id}`, { is_active: !repo.is_active });
    refresh();
  };

  const setField = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Settings</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openAdd}>
          Add Repository
        </Button>
      </Box>

      <Typography variant="h6" gutterBottom>Repositories</Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>URL</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Branch</TableCell>
              <TableCell>Active</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(repos || []).map((repo) => (
              <TableRow key={repo.id}>
                <TableCell>{repo.name}</TableCell>
                <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{repo.url}</TableCell>
                <TableCell><Chip label={repo.provider} size="small" /></TableCell>
                <TableCell>{repo.default_branch}</TableCell>
                <TableCell>
                  <Switch checked={repo.is_active} onChange={() => handleToggleActive(repo)} size="small" />
                </TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => openEdit(repo)}><EditIcon fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => setDeleteConfirm(repo.id)}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
            {repos && repos.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ color: 'text.secondary', py: 4 }}>
                  No repositories configured. Click "Add Repository" to get started.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editId ? 'Edit Repository' : 'Add Repository'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '16px !important' }}>
          <TextField label="Name" value={form.name} onChange={setField('name')} required fullWidth />
          <TextField label="URL" value={form.url} onChange={setField('url')} required fullWidth />
          <TextField label="Provider" value={form.provider} onChange={setField('provider')} select fullWidth>
            {PROVIDERS.map((p) => <MenuItem key={p} value={p}>{p}</MenuItem>)}
          </TextField>
          <TextField label="Default Branch" value={form.default_branch} onChange={setField('default_branch')} fullWidth />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={!form.name || !form.url}>Save</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Delete Repository</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this repository?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => handleDelete(deleteConfirm)}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
