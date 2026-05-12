import { useEffect } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  handler: () => void;
  description?: string;
}

const DEFAULT_PREVENT = ['b', 'k', '?', '/', 'Escape'];

export function useGlobalKeyboard(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't fire when typing in inputs/textareas
      const tag = (e.target as HTMLElement)?.tagName;
      const isEditable = (e.target as HTMLElement)?.isContentEditable;
      if ((tag === 'INPUT' || tag === 'TEXTAREA' || isEditable) && !e.ctrlKey && !e.metaKey) {
        return;
      }

      for (const shortcut of shortcuts) {
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase() ||
          e.code?.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = !!shortcut.ctrlKey === (e.ctrlKey || e.metaKey); // treat ctrl==meta
        const shiftMatch = !!shortcut.shiftKey === e.shiftKey;
        const altMatch = !!shortcut.altKey === e.altKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          if (DEFAULT_PREVENT.includes(shortcut.key.toLowerCase()) || shortcut.ctrlKey || shortcut.metaKey) {
            e.preventDefault();
          }
          shortcut.handler();
          break;
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [shortcuts]);
}
