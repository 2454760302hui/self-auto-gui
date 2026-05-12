import * as React from 'react';
import { Outlet, createRootRoute } from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';
import { RootLayout } from '../components/layout/RootLayout';
import { Toaster } from '../components/Toaster';

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  return (
    <RootLayout>
      <Outlet />
    </RootLayout>
  );
}
