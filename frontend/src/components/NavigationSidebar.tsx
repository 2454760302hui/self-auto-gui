import React from 'react';
import { Link, useMatchRoute } from '@tanstack/react-router';
import {
  ListChecks,
  History,
  Clock,
  Terminal,
  LayoutTemplate,
  Smartphone,
  Radio,
  Cpu,
  type LucideIcon,
} from 'lucide-react';
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip';
import { useTranslation } from '../lib/i18n-context';
import { XNextLogo } from './XNextLogo';

interface NavigationItem {
  id: string;
  icon: LucideIcon;
  label: string;
  path: string;
  badge?: string;
}

interface NavigationSidebarProps {
  className?: string;
}

export function NavigationSidebar({ className }: NavigationSidebarProps) {
  const t = useTranslation();
  const matchRoute = useMatchRoute();

  const mainItems: NavigationItem[] = [
    // chat item removed
  ];

  const automationItems: NavigationItem[] = [
    {
      id: 'record',
      icon: Radio,
      label: '录制',
      path: '/record',
      badge: 'NEW',
    },
    {
      id: 'automation',
      icon: Cpu,
      label: '自动化',
      path: '/automation',
      badge: 'NEW',
    },
  ];

  const toolItems: NavigationItem[] = [
    {
      id: 'templates',
      icon: LayoutTemplate,
      label: t.navigation?.templates || '模板',
      path: '/templates',
    },
    {
      id: 'workflows',
      icon: ListChecks,
      label: t.navigation?.workflows || '工作流',
      path: '/workflows',
    },
  ];

  const supportItems: NavigationItem[] = [
    {
      id: 'history',
      icon: History,
      label: t.navigation?.history || '历史',
      path: '/history',
    },
    {
      id: 'scheduled-tasks',
      icon: Clock,
      label: t.navigation?.scheduledTasks || '定时',
      path: '/scheduled-tasks',
    },
    {
      id: 'logs',
      icon: Terminal,
      label: t.navigation?.logs || '日志',
      path: '/logs',
    },
  ];

  return (
    <nav
      className={`
        fixed top-0 left-0 right-0 z-50 h-16
        bg-white/80 dark:bg-[#0a0e1a]/80 backdrop-blur-xl
        border-b border-border
        flex items-center px-5
        ${className || ''}
      `}
    >
      {/* Logo */}
      <div className="pr-6 mr-6 border-r border-border">
        <XNextLogo size="default" />
      </div>

      {/* Main navigation */}
      <div className="flex items-center gap-1">
        {mainItems.map(item => {
          const Icon = item.icon;
          const isActive = matchRoute({ to: item.path });

          return (
            <Link
              key={item.id}
              to={item.path}
              className={`
                relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                transition-all duration-200
                ${isActive
                  ? 'text-primary dark:text-indigo-400 bg-primary/8 dark:bg-indigo-500/10'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                }
              `}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
              {isActive && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500" />
              )}
            </Link>
          );
        })}
      </div>

      <div className="w-px h-6 bg-border mx-4" />

      {/* Automation navigation - highlighted section */}
      <div className="flex items-center gap-1">
        {automationItems.map(item => {
          const Icon = item.icon;
          const isActive = matchRoute({ to: item.path });

          return (
            <Link
              key={item.id}
              to={item.path}
              className={`
                relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                transition-all duration-200
                ${isActive
                  ? 'text-primary dark:text-indigo-400 bg-primary/8 dark:bg-indigo-500/10'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                }
              `}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
              {item.badge && (
                <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold bg-gradient-to-r from-indigo-500 to-cyan-500 text-white rounded-full">
                  {item.badge}
                </span>
              )}
              {isActive && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500" />
              )}
            </Link>
          );
        })}
      </div>

      <div className="w-px h-6 bg-border mx-4" />

      {/* Tool navigation */}
      <div className="flex items-center gap-1">
        {toolItems.map(item => {
          const Icon = item.icon;
          const isActive = matchRoute({ to: item.path });

          return (
            <Link
              key={item.id}
              to={item.path}
              className={`
                relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                transition-all duration-200
                ${isActive
                  ? 'text-primary dark:text-indigo-400 bg-primary/8 dark:bg-indigo-500/10'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                }
              `}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
              {isActive && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500" />
              )}
            </Link>
          );
        })}
      </div>

      {/* Right side - support items */}
      <div className="flex items-center gap-1 ml-auto">
        {supportItems.map(item => {
          const Icon = item.icon;
          const isActive = matchRoute({ to: item.path });

          return (
            <Tooltip key={item.id}>
              <TooltipTrigger asChild>
                <Link
                  to={item.path}
                  className={`
                    relative w-9 h-9 flex items-center justify-center rounded-lg
                    transition-all duration-200
                    ${isActive
                      ? 'text-primary dark:text-indigo-400 bg-primary/8 dark:bg-indigo-500/10'
                      : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500" />
                  )}
                </Link>
              </TooltipTrigger>
              <TooltipContent side="bottom" sideOffset={8}>
                {item.label}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </nav>
  );
}
