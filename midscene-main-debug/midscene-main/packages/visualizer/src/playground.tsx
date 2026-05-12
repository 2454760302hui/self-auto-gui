import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import { globalThemeConfig } from './component/color';
import {
  Playground,
  extensionAgentForTabId,
} from './component/playground-component';
import { useChromeTabInfo } from './component/store';

function PlaygroundApp(): JSX.Element {
  const { tabId, windowId } = useChromeTabInfo();

  return (
    <ConfigProvider theme={globalThemeConfig()}>
      <Playground
        getAgent={() => extensionAgentForTabId(tabId, windowId)}
        showContextPreview={false}
      />
    </ConfigProvider>
  );
}

const root = document.getElementById('root');
if (root) {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <PlaygroundApp />
    </React.StrictMode>,
  );
}
