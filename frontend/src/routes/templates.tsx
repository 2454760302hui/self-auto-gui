import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect, useCallback } from 'react';
import {
  listTaskTemplates,
  createTaskTemplate,
  updateTaskTemplate,
  deleteTaskTemplate,
  type TaskTemplate,
} from '../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Plus, Edit, Trash2, Loader2, FileText, Search } from 'lucide-react';
import { useTranslation } from '../lib/i18n-context';

export const Route = createFileRoute('/templates')({
  component: TemplatesComponent,
});

function TemplatesComponent() {
  const t = useTranslation();
  const [templates, setTemplates] = useState<TaskTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Dialog state
  const [showDialog, setShowDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<TaskTemplate | null>(null);
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formMessage, setFormMessage] = useState('');
  const [formCategory, setFormCategory] = useState('general');
  const [saving, setSaving] = useState(false);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTaskTemplates(selectedCategory || undefined);
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const categories = Array.from(new Set(templates.map(t => t.category)));

  const filteredTemplates = templates.filter(t => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.name.toLowerCase().includes(q) ||
      t.message.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q)
    );
  });

  const handleCreate = () => {
    setEditingTemplate(null);
    setFormName('');
    setFormDescription('');
    setFormMessage('');
    setFormCategory('general');
    setShowDialog(true);
  };

  const handleEdit = (template: TaskTemplate) => {
    if (template.is_builtin) return;
    setEditingTemplate(template);
    setFormName(template.name);
    setFormDescription(template.description);
    setFormMessage(template.message);
    setFormCategory(template.category);
    setShowDialog(true);
  };

  const handleSave = async () => {
    if (!formName.trim() || !formMessage.trim()) return;
    setSaving(true);
    try {
      if (editingTemplate) {
        await updateTaskTemplate(editingTemplate.id, {
          name: formName,
          description: formDescription,
          message: formMessage,
          category: formCategory,
        });
      } else {
        await createTaskTemplate({
          name: formName,
          description: formDescription,
          message: formMessage,
          category: formCategory,
        });
      }
      setShowDialog(false);
      loadTemplates();
    } catch (err) {
      console.error('Failed to save template:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTaskTemplate(id);
      loadTemplates();
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            <span className="xnext-gradient-text">{t.navigation?.templates || '任务模板'}</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            创建和管理常用任务模板，快速执行重复操作
          </p>
        </div>
        <Button onClick={handleCreate} className="bg-gradient-to-r from-indigo-500 to-cyan-500 text-white hover:opacity-90">
          <Plus className="w-4 h-4" />
          新建模板
        </Button>
      </div>

      {/* Search & Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            placeholder="搜索模板..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-1.5">
          <Button
            variant={selectedCategory === null ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            全部
          </Button>
          {categories.map(cat => (
            <Button
              key={cat}
              variant={selectedCategory === cat ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </Button>
          ))}
        </div>
      </div>

      {/* Templates Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filteredTemplates.length === 0 ? (
        <div className="text-center py-20">
          <FileText className="w-12 h-12 text-zinc-300 dark:text-zinc-700 mx-auto mb-3" />
          <p className="text-zinc-500 dark:text-zinc-400">暂无模板</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredTemplates.map(template => (
            <Card
              key={template.id}
              className="group xnext-card hover:border-indigo-500/30 dark:hover:border-indigo-400/30 transition-all hover:shadow-lg"
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base flex items-center gap-2">
                      {template.name}
                      {template.is_builtin && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 dark:text-indigo-400 font-normal">
                          内置
                        </span>
                      )}
                    </CardTitle>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                      {template.category} · {template.description || '无描述'}
                    </p>
                  </div>
                  {!template.is_builtin && (
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => handleEdit(template)}
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => handleDelete(template.id)}
                      >
                        <Trash2 className="w-3.5 h-3.5 text-red-500" />
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg bg-muted/50 p-3">
                  <code className="text-sm text-foreground/80 whitespace-pre-wrap">
                    {template.message}
                  </code>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingTemplate ? '编辑模板' : '新建模板'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>模板名称</Label>
              <Input
                value={formName}
                onChange={e => setFormName(e.target.value)}
                placeholder="例如：打开微信"
              />
            </div>
            <div className="space-y-2">
              <Label>描述</Label>
              <Input
                value={formDescription}
                onChange={e => setFormDescription(e.target.value)}
                placeholder="模板用途说明"
              />
            </div>
            <div className="space-y-2">
              <Label>执行指令</Label>
              <Textarea
                value={formMessage}
                onChange={e => setFormMessage(e.target.value)}
                placeholder="发送给设备的指令内容"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>分类</Label>
              <Input
                value={formCategory}
                onChange={e => setFormCategory(e.target.value)}
                placeholder="例如：应用、工具、系统"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              取消
            </Button>
            <Button
              variant="default"
              onClick={handleSave}
              disabled={saving || !formName.trim() || !formMessage.trim()}
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {editingTemplate ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
