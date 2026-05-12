/* eslint-disable react-refresh/only-export-components */

import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

/* ============================================
   NEXA Button Variants
   Modern, clean button styles with subtle interactions
   ============================================ */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 relative overflow-hidden",
  {
    variants: {
      variant: {
        // Primary - Solid indigo, main action with enhanced feedback
        default: 'bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-md active:scale-[0.95] active:shadow-sm shadow-sm transition-all duration-150',

        // Destructive - For dangerous actions
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:shadow-md active:scale-[0.95] active:shadow-sm shadow-sm',

        // Outline - Secondary actions, bordered with better hover
        outline: 'border border-border bg-transparent hover:bg-secondary/70 hover:border-primary/50 active:scale-[0.95] active:bg-secondary',

        // Secondary - Subtle gray background
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80 hover:shadow-sm active:scale-[0.95]',

        // Ghost - Minimal, no background
        ghost: 'hover:bg-secondary/60 active:scale-[0.95] active:bg-secondary/80',

        // Link - Text only, for inline actions
        link: 'text-primary underline-offset-4 hover:underline hover:text-primary/80',

        // Success - Green with check icon style
        success: 'bg-emerald-500 text-white hover:bg-emerald-600 hover:shadow-md active:scale-[0.95] active:shadow-sm shadow-sm',

        // Soft - Very subtle, for tertiary actions
        soft: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 hover:shadow-sm active:scale-[0.95] dark:bg-emerald-900/30 dark:text-emerald-300 dark:hover:bg-emerald-900/50',
      },
      size: {
        default: 'h-10 rounded-lg px-4 py-2 has-[>svg]:px-3',
        sm: 'h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5 text-sm',
        lg: 'h-12 rounded-lg px-6 has-[>svg]:px-4 text-base',
        icon: 'size-10 rounded-lg',
        'icon-sm': 'size-8 rounded-md',
        'icon-lg': 'size-12 rounded-lg',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

interface ButtonProps extends React.ComponentProps<'button'>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, onClick, children, ...props }, ref) => {
    const [ripples, setRipples] = React.useState<{ x: number; y: number; id: number }[]>([]);
    const buttonRef = React.useRef<HTMLButtonElement>(null);

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      const button = buttonRef.current;
      if (!button) return;

      const rect = button.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const id = Date.now();

      setRipples(prev => [...prev, { x, y, id }]);

      setTimeout(() => {
        setRipples(prev => prev.filter(r => r.id !== id));
      }, 600);

      onClick?.(e);
    };

    const mergedRef = (node: HTMLButtonElement | null) => {
      buttonRef.current = node;
      if (typeof ref === 'function') {
        ref(node);
      } else if (ref) {
        ref.current = node;
      }
    };

    if (asChild) {
      return (
        <Slot
          ref={mergedRef}
          onClick={handleClick}
          className={cn(buttonVariants({ variant, size, className }))}
          {...props}
        >
          {children}
        </Slot>
      );
    }

    return (
      <button
        ref={mergedRef}
        className={cn(buttonVariants({ variant, size, className }))}
        onClick={handleClick}
        {...props}
      >
        {children}
        {ripples.map(ripple => (
          <span
            key={ripple.id}
            className="ripple-effect"
            style={{
              left: ripple.x,
              top: ripple.y,
            }}
          />
        ))}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button, buttonVariants };